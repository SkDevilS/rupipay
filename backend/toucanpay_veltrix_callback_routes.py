"""
ToucanPay_Veltrix Webhook/Callback Routes

Toucan Payments DQR documentation specifies a POST callback containing:
upiTransRefNo, pspRefNo, txnId, custRefNo, amount, txnAuthDate,
payeeRespCode, approvalNumber, status, statusDesc, payerVPA, payeeVPA,
txnType, txnNote, payeeName, payerAccNo and payeeAccNo.
"""

from datetime import datetime
import json
import requests
from flask import Blueprint, request, jsonify

from config import Config
from database import get_db_connection


toucanpay_veltrix_callback_bp = Blueprint("toucanpay_veltrix_callback", __name__)


def _normalise_status(data):
    status = str(data.get("status") or "").strip().upper()
    response_code = str(data.get("payeeRespCode") or "").strip()

    if status in {"SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED"} or response_code == "00":
        return "SUCCESS"

    if status in {"FAILED", "FAILURE", "DECLINED", "REJECTED", "EXPIRED", "CANCELLED"}:
        return "FAILED"

    return "PENDING"


def _derive_invoice_number(psp_ref_no):
    """
    Toucan documents pspRefNo as terminalNumber + invoiceNumber.
    """
    if not psp_ref_no:
        return None

    psp_ref_no = str(psp_ref_no).strip()
    terminal = str(Config.TOUCANPAY_VELTRIX_TERMINAL_NUMBER or "").strip()

    if terminal and psp_ref_no.startswith(terminal):
        return psp_ref_no[len(terminal):]

    return None


@toucanpay_veltrix_callback_bp.route("/api/callback/toucanpay_veltrix", methods=["POST"])
def handle_toucanpay_veltrix_callback():
    try:
        data = request.get_json(silent=True)
        if not data:
            data = request.form.to_dict()

        if not data:
            return jsonify({"success": False, "message": "Empty callback payload"}), 400

        print(f"📥 ToucanPay_VELTRIX Callback Received: {json.dumps(data, default=str)}")

        psp_ref_no = str(data.get("pspRefNo") or "").strip()
        toucan_txn_id = str(data.get("txnId") or "").strip()
        upi_ref_no = str(data.get("upiTransRefNo") or "").strip()
        status = _normalise_status(data)

        invoice_number = _derive_invoice_number(psp_ref_no)
        if not invoice_number:
            return jsonify({
                "success": False,
                "message": "Invalid or missing pspRefNo; unable to derive invoiceNumber",
            }), 400

        callback_amount = data.get("amount")
        try:
            callback_amount = float(callback_amount) if callback_amount not in (None, "") else None
        except (TypeError, ValueError):
            callback_amount = None

        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Database connection failed"}), 500

        try:
            with conn.cursor() as cursor:
                # Before callback, pg_txn_id contains Toucan invoiceNumber.
                # After callback, it contains Toucan txnId. Support both so
                # duplicate callbacks remain idempotent.
                cursor.execute(
                    """
                    SELECT
                        id, merchant_id, txn_id, order_id, amount, net_amount,
                        charge_amount, callback_url, status, pg_partner,
                        pg_txn_id, payment_mode
                    FROM payin_transactions
                    WHERE pg_partner = 'ToucanPay_Veltrix'
                      AND (
                            pg_txn_id = %s
                            OR (%s <> '' AND pg_txn_id = %s)
                            OR order_id = %s
                          )
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (invoice_number, toucan_txn_id, toucan_txn_id, invoice_number),
                )
                txn = cursor.fetchone()

                if not txn:
                    print(
                        f"❌ ToucanPay_Veltrix Callback: transaction not found "
                        f"for invoice={invoice_number}, pspRefNo={psp_ref_no}"
                    )
                    return jsonify({"success": False, "message": "Transaction not found"}), 404

                txn_id = txn["txn_id"]
                merchant_id = txn["merchant_id"]
                current_status = str(txn.get("status") or "").upper()
                amount = float(txn["amount"])

                # Amount mismatch is treated as a bad callback rather than
                # silently crediting a different amount.
                if callback_amount is not None and abs(callback_amount - amount) > 0.01:
                    print(
                        f"❌ ToucanPay_Veltrix amount mismatch for {txn_id}: "
                        f"DB={amount}, callback={callback_amount}"
                    )
                    return jsonify({"success": False, "message": "Amount mismatch"}), 400

                if current_status in {"SUCCESS", "FAILED"}:
                    print(f"⚠️ ToucanPay_Veltrix transaction {txn_id} already final: {current_status}")
                    return jsonify({"success": True, "message": "Already processed"}), 200

                # Update transaction first.
                cursor.execute(
                    """
                    UPDATE payin_transactions
                    SET
                        status = %s,
                        bank_ref_no = %s,
                        pg_txn_id = %s,
                        payment_mode = 'UPI',
                        completed_at = CASE
                            WHEN %s IN ('SUCCESS', 'FAILED') THEN NOW()
                            ELSE completed_at
                        END,
                        updated_at = NOW()
                    WHERE txn_id = %s
                    """,
                    (
                        status,
                        upi_ref_no or data.get("approvalNumber") or None,
                        toucan_txn_id or invoice_number,
                        status,
                        txn_id,
                    ),
                )

                if status == "SUCCESS":
                    # Idempotency: do not credit wallet twice if Toucan retries callback.
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM merchant_wallet_transactions
                        WHERE reference_id = %s
                          AND txn_type = 'UNSETTLED_CREDIT'
                        """,
                        (txn_id,),
                    )
                    already_credited = cursor.fetchone()["count"] > 0

                    if not already_credited:
                        from wallet_service import wallet_service

                        merchant_wallet_result = wallet_service.credit_unsettled_wallet(
                            merchant_id=merchant_id,
                            amount=float(txn["net_amount"]),
                            description=f"PayIn received (ToucanPay_Veltrix) - {txn['order_id']}",
                            reference_id=txn_id,
                        )

                        if not merchant_wallet_result.get("success"):
                            print(
                                f"❌ ToucanPay_Veltrix merchant wallet credit failed: "
                                f"{merchant_wallet_result.get('message')}"
                            )

                        admin_wallet_result = wallet_service.credit_admin_unsettled_wallet(
                            admin_id="admin",
                            amount=float(txn["charge_amount"]),
                            description=f"PayIn charge (ToucanPay_Veltrix) - {txn['order_id']}",
                            reference_id=txn_id,
                        )

                        if not admin_wallet_result.get("success"):
                            print(
                                f"❌ ToucanPay_Veltrix admin wallet credit failed: "
                                f"{admin_wallet_result.get('message')}"
                            )
                    else:
                        print(f"⚠️ Wallet already credited for {txn_id}; skipping duplicate credit")

                conn.commit()

                # Forward normalized callback to merchant.
                callback_url = txn.get("callback_url")
                if callback_url:
                    callback_url = callback_url.strip() or None

                if not callback_url:
                    cursor.execute(
                        """
                        SELECT payin_callback_url
                        FROM merchant_callbacks
                        WHERE merchant_id = %s
                        """,
                        (merchant_id,),
                    )
                    fallback = cursor.fetchone()
                    if fallback and fallback.get("payin_callback_url"):
                        callback_url = fallback["payin_callback_url"].strip() or None

                if callback_url:
                    # Do not forward to an internal gateway callback endpoint.
                    if "/api/callback/toucanpay_veltrix" in callback_url:
                        print("⚠️ Skipping merchant callback: points to ToucanPay_Veltrix internal callback endpoint")
                    else:
                        merchant_callback_data = {
                            "txn_id": txn_id,
                            "order_id": txn["order_id"],
                            "status": status,
                            "amount": str(amount),
                            "net_amount": str(txn.get("net_amount", amount)),
                            "charge_amount": str(txn.get("charge_amount", "0")),
                            "utr": upi_ref_no or "",
                            "pg_txn_id": toucan_txn_id or invoice_number,
                            "payment_mode": "UPI",
                            "pg_partner": "ToucanPay_Veltrix",
                            "timestamp": datetime.now().isoformat(),
                        }

                        try:
                            callback_response = requests.post(
                                callback_url,
                                json=merchant_callback_data,
                                headers={"Content-Type": "application/json"},
                                timeout=10,
                            )

                            cursor.execute(
                                """
                                INSERT INTO callback_logs
                                (merchant_id, txn_id, callback_url, request_data,
                                 response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                """,
                                (
                                    merchant_id,
                                    txn_id,
                                    callback_url,
                                    json.dumps(merchant_callback_data),
                                    callback_response.status_code,
                                    callback_response.text[:1000],
                                ),
                            )
                            conn.commit()

                            print(
                                f"✅ ToucanPay_Veltrix merchant callback sent: "
                                f"{callback_response.status_code}"
                            )

                        except requests.exceptions.RequestException as exc:
                            print(f"❌ ToucanPay_Veltrix merchant callback failed: {exc}")

                            cursor.execute(
                                """
                                INSERT INTO callback_logs
                                (merchant_id, txn_id, callback_url, request_data,
                                 response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                                """,
                                (
                                    merchant_id,
                                    txn_id,
                                    callback_url,
                                    json.dumps(merchant_callback_data),
                                    0,
                                    str(exc)[:1000],
                                ),
                            )
                            conn.commit()

                return jsonify({"success": True}), 200

        finally:
            conn.close()

    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"❌ ToucanPay_Veltrix callback error: {exc}")
        return jsonify({"success": False, "message": "Internal server error"}), 500
