"""
ToucanPay_Veltrix DQR Payin Service

Implements the Toucan_Veltrix Payments DQR transaction API from the supplied
"Complete Title: DQR transaction-API Specifications" document.

Provider API:
    POST https://pay.toucanpay.in/api/pay/v1/process

Toucan callback is configured out-of-band with Toucan Payments:
    POST /api/callback/toucanpay_veltrix
"""

import hashlib
import os
import secrets
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests

from config import Config
from database import get_db_connection


class ToucanPayVeltrixService:
    def __init__(self):
        self.pg_partner_name = "ToucanPay_Veltrix"
        self.txn_prefix = "TOUCAN_"

        self.payin_url = Config.TOUCANPAY_VELTRIX_PAYIN_URL
        self.auth_token = Config.TOUCANPAY_VELTRIX_AUTH_TOKEN
        self.merchant_number = Config.TOUCANPAY_VELTRIX_MERCHANT_NUMBER
        self.terminal_number = Config.TOUCANPAY_VELTRIX_TERMINAL_NUMBER
        self.expiry_minutes = Config.TOUCANPAY_VELTRIX_EXPIRY_MINUTES

        print(f"🔑 {self.pg_partner_name} Service Initialized")
        print(f"  Payin URL: {self.payin_url}")
        print(f"  Merchant Number: {'SET' if self.merchant_number else 'NOT SET'}")
        print(f"  Terminal Number: {'SET' if self.terminal_number else 'NOT SET'}")
        print(f"  Auth Token: {'SET' if self.auth_token else 'NOT SET'}")

    @staticmethod
    def _sha512(value: str) -> str:
        """Toucan's documented hash logic: SHA-512 over UTF-8 bytes."""
        return hashlib.sha512(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _amount_string(raw_amount) -> str:
        """
        Preserve the merchant-supplied numeric representation where possible.
        The supplied Toucan example hashes the value '58' directly.
        """
        value = str(raw_amount).strip()
        if not value:
            raise ValueError("Amount is required")

        try:
            amount = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Invalid amount") from exc

        if amount <= 0:
            raise ValueError("Invalid amount")

        # For values such as 58.00, keep the supplied representation.
        # For Decimal/scientific input, normalize to a plain decimal string.
        if "e" in value.lower():
            value = format(amount, "f")

        return value

    @staticmethod
    def _generate_invoice_number() -> str:
        """
        Toucan requires a unique invoiceNumber with minimum 15 digits.
        13-digit millisecond timestamp + 2 random digits = 15 digits.
        """
        return f"{int(time.time() * 1000):013d}{secrets.randbelow(100):02d}"

    def calculate_charges(self, amount, scheme_id, service_type="PAYIN"):
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return None, None, None

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT charge_value, charge_type
                    FROM commercial_charges
                    WHERE scheme_id = %s
                      AND service_type = %s
                      AND %s BETWEEN min_amount AND max_amount
                    ORDER BY min_amount DESC
                    LIMIT 1
                    """,
                    (scheme_id, service_type, amount),
                )
                charge_config = cursor.fetchone()

                if not charge_config:
                    return 0.00, amount, "FIXED"

                charge_type = charge_config["charge_type"]
                charge_value = float(charge_config["charge_value"])
                charge_amount = (
                    (amount * charge_value) / 100
                    if charge_type == "PERCENTAGE"
                    else charge_value
                )

                return round(charge_amount, 2), round(amount - charge_amount, 2), charge_type

        except Exception as exc:
            print(f"❌ ToucanPay_Veltrix charge calculation error: {exc}")
            return None, None, None
        finally:
            if conn:
                conn.close()

    def create_payin_order(self, merchant_id, order_data):
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                return {"success": False, "message": "Database connection failed"}

            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT merchant_id, full_name, email, scheme_id, is_active
                    FROM merchants
                    WHERE merchant_id = %s
                    """,
                    (merchant_id,),
                )
                merchant = cursor.fetchone()

                if not merchant or not merchant["is_active"]:
                    return {"success": False, "message": "Merchant inactive/not found"}

                raw_amount = order_data.get("amount")
                try:
                    amount_string = self._amount_string(raw_amount)
                    amount = float(Decimal(amount_string))
                except (ValueError, InvalidOperation):
                    return {"success": False, "message": "Invalid amount"}

                if amount <= 0:
                    return {"success": False, "message": "Invalid amount"}

                if not self.auth_token:
                    return {"success": False, "message": "ToucanPay_Veltrix auth token is not configured"}
                if not self.merchant_number:
                    return {"success": False, "message": "ToucanPay_Veltrix merchant number is not configured"}
                if not self.terminal_number:
                    return {"success": False, "message": "ToucanPay_Veltrix terminal number is not configured"}

                charge_amount, net_amount, charge_type = self.calculate_charges(
                    amount, merchant["scheme_id"]
                )
                if charge_amount is None:
                    return {"success": False, "message": "Charge calculation failed"}

                original_order_id = str(order_data.get("orderid", "")).strip()
                if not original_order_id:
                    return {"success": False, "message": "orderid is required"}

                # Toucan requires a minimum 15-digit invoiceNumber.
                # We keep the platform's original order_id in our DB and use
                # the generated invoice as the temporary pg_txn_id until callback.
                invoice_number = self._generate_invoice_number()
                txn_id = (
                    f"{self.txn_prefix}{merchant_id}_{original_order_id}_"
                    f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )

                # Toucan's supplied sample proves SHA-512("58") equals the
                # documented hashAmount for a transaction value of 58.
                hash_amount = self._sha512(amount_string)

                payload = {
                    "messageID": "/api/pay/v1/process",
                    "requestType": "CREATE",
                    "object": {
                        "transactionamount": {
                            "code": "INR",
                            "value": amount,
                        },
                        "tranAmtInMerchantCurrency": {
                            "code": "INR",
                            "value": amount,
                        },
                        "invoiceNumber": invoice_number,
                        "merchantNumber": self.merchant_number,
                        "messageType": "VPA_PUSH",
                        "expiryTime": str(self.expiry_minutes),
                        "paymentMethod": "UPI",
                        "terminalNumber": self.terminal_number,
                        "transactionCurrency": "INR",
                        "hashAmount": hash_amount,
                    },
                }

                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                print(
                    f"📤 ToucanPay_Veltrix CREATE: merchant={merchant_id}, "
                    f"order={original_order_id}, invoice={invoice_number}, amount={amount_string}"
                )

                response = requests.post(
                    self.payin_url,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )

                try:
                    result = response.json()
                except ValueError:
                    return {
                        "success": False,
                        "message": f"Invalid JSON response from ToucanPay_Veltrix: {response.text[:1000]}",
                    }

                if response.status_code not in (200, 201):
                    return {
                        "success": False,
                        "message": f"ToucanPay_Veltrix API error ({response.status_code})",
                        "details": result,
                    }

                if not result.get("success", False):
                    return {
                        "success": False,
                        "message": result.get("message")
                        or result.get("errorMessage")
                        or "ToucanPay_Veltrix rejected the transaction",
                        "details": result,
                    }

                obj = result.get("object") or {}

                # Toucan returns qrResponse as the UPI intent/QR string.
                qr_string = obj.get("qrResponse") or ""
                rrn = obj.get("rrn") or invoice_number
                provider_status = str(obj.get("status") or "").upper()
                provider_status_code = str(obj.get("statusCode") or "")

                if not qr_string:
                    return {
                        "success": False,
                        "message": "ToucanPay_Veltrix did not return qrResponse",
                        "details": result,
                    }

                # Keep original merchant order_id in our DB.
                # pg_txn_id initially stores the Toucan invoice number so the
                # callback can locate the transaction through pspRefNo.
                cursor.execute(
                    """
                    INSERT INTO payin_transactions (
                        txn_id, merchant_id, order_id, amount, charge_amount,
                        charge_type, net_amount, payee_name, payee_email,
                        payee_mobile, product_info, status, pg_partner,
                        pg_txn_id, callback_url, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, NOW()
                    )
                    """,
                    (
                        txn_id,
                        merchant_id,
                        original_order_id,
                        amount,
                        charge_amount,
                        charge_type,
                        net_amount,
                        order_data.get("payee_fname") or merchant["full_name"] or "Customer",
                        order_data.get("payee_email") or merchant["email"] or "test@gmail.com",
                        order_data.get("payee_mobile") or "9999999999",
                        order_data.get("productinfo", "Payment"),
                        "INITIATED",
                        self.pg_partner_name,
                        invoice_number,
                        order_data.get("callbackurl"),
                    ),
                )
                conn.commit()

                return {
                    "success": True,
                    "txn_id": txn_id,
                    "order_id": original_order_id,
                    "merchant_order_id": original_order_id,
                    "amount": amount,
                    "charge_amount": charge_amount,
                    "net_amount": net_amount,
                    "qr_string": qr_string,
                    "qr_code_url": qr_string,
                    "upi_link": qr_string,
                    "intent_url": qr_string,
                    "payment_link": qr_string,
                    "pg_txn_id": invoice_number,
                    "pg_partner": self.pg_partner_name,
                    "provider_rrn": rrn,
                    "provider_status": provider_status,
                    "provider_status_code": provider_status_code,
                    "expires_in": int(self.expiry_minutes),
                }

        except requests.exceptions.RequestException as exc:
            if conn:
                conn.rollback()
            print(f"❌ ToucanPay_Veltrix API request error: {exc}")
            return {"success": False, "message": f"ToucanPay_Veltrix API request failed: {exc}"}
        except Exception as exc:
            if conn:
                conn.rollback()
            import traceback
            traceback.print_exc()
            print(f"❌ ToucanPay_Veltrix order generation error: {exc}")
            return {"success": False, "message": str(exc)}
        finally:
            if conn:
                conn.close()


toucanpay_veltrix_service = ToucanPayVeltrixService()
