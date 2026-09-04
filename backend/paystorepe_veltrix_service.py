"""
PayStorePe_Veltrix Payout Service Integration
Handles payout transactions through PayStorePe for Veltrix.

PayStorePe API:
POST /api/payout/v1/payout-initiate

Expected gateway response:
{
    "status": "ACCEPTED",
    "txn_id": "...",
    "amount": 5000.00,
    "service_charge": 10.00,
    "gst_amount": 1.80,
    "deduct_amount": 5011.80,
    "wallet_balance": 95000.00,
    "message": "Request accepted successfully"
}

Gateway error response:
{
    "status": "FAILED",
    "message": "Insufficient wallet balance"
}
"""

import requests
import json
from datetime import datetime
from database import get_db_connection
from config import Config


class PayStorePeVeltrixService:
    def __init__(self):
        self.base_url = Config.PAYSTOREPE_VELTRIX_BASE_URL.rstrip('/')
        self.client_id = Config.PAYSTOREPE_VELTRIX_CLIENT_ID
        self.client_secret = Config.PAYSTOREPE_VELTRIX_CLIENT_SECRET
        self.callback_url = getattr(
            Config,
            'PAYSTOREPE_VELTRIX_CALLBACK_URL',
            ''
        )

    def get_headers(self):
        """Headers required by PayStorePe."""
        return {
            'Client-Id': self.client_id,
            'Client-Secret': self.client_secret,
            'Content-Type': 'application/json'
        }

    def generate_txn_id(self, merchant_id, reference_id):
        """Generate an internal transaction ID."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        merchant_part = str(merchant_id or 'ADMIN').replace(' ', '_')
        reference_part = str(reference_id or 'REF').replace(' ', '_')
        return f"PSPE_VE_TXN_{merchant_part}_{reference_part}_{timestamp}"

    def calculate_charges(self, amount, scheme_id, service_type='PAYOUT'):
        """
        Calculate the merchant-side payout charge from the portal's
        commercial charge configuration.

        PayStorePe's service_charge/gst_amount are gateway-side values
        returned after initiation and are kept separately from the
        portal's commercial charge.
        """
        try:
            conn = get_db_connection()
            if not conn:
                print("PayStorePe_Veltrix charge calculation: DB connection failed")
                return None

            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT charge_value, charge_type
                    FROM commercial_charges
                    WHERE scheme_id = %s
                      AND service_type = %s
                      AND %s BETWEEN min_amount AND max_amount
                    LIMIT 1
                """, (scheme_id, service_type, amount))

                charge = cursor.fetchone()

                if charge:
                    charge_amount = 0.00

                    if charge['charge_type'] == 'PERCENTAGE':
                        charge_amount = (
                            float(amount) * float(charge['charge_value'])
                        ) / 100
                    else:
                        charge_amount = float(charge['charge_value'])

                    net_amount = float(amount) + charge_amount

                    conn.close()
                    return {
                        'charge_amount': round(charge_amount, 2),
                        'charge_type': charge['charge_type'],
                        'net_amount': round(net_amount, 2)
                    }

                conn.close()
                return {
                    'charge_amount': 0.00,
                    'charge_type': 'FIXED',
                    'net_amount': round(float(amount), 2)
                }

        except Exception as e:
            print(f"PayStorePe_Veltrix charge calculation error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def initiate_payout(self, merchant_id, payout_data, admin_id=None):
        """
        Initiate a payout through PayStorePe.

        payout_data expected keys:
            reference_id
            amount
            bene_name
            bene_account
            bene_ifsc
            payment_mode
            bank_name
            bene_mobile
            bene_email
            callback_url
            remarks
        """
        conn = None

        try:
            conn = get_db_connection()
            if not conn:
                return {
                    'success': False,
                    'message': 'Database connection failed'
                }

            with conn.cursor() as cursor:

                # Admin payout handling follows the existing payout service pattern.
                is_admin_payout = (
                    admin_id is not None or
                    (merchant_id and str(merchant_id).startswith('ADMIN_'))
                )

                if is_admin_payout:
                    if admin_id is None and merchant_id:
                        admin_id = str(merchant_id).replace('ADMIN_', '', 1)
                    merchant_id = None

                    charges = {
                        'charge_amount': 0.00,
                        'charge_type': 'FIXED',
                        'net_amount': float(payout_data['amount'])
                    }
                else:
                    cursor.execute("""
                        SELECT scheme_id, is_active
                        FROM merchants
                        WHERE merchant_id = %s
                    """, (merchant_id,))
                    merchant = cursor.fetchone()

                    if not merchant:
                        return {
                            'success': False,
                            'message': 'Merchant not found'
                        }

                    if not merchant['is_active']:
                        return {
                            'success': False,
                            'message': 'Merchant account is inactive'
                        }

                    if not merchant['scheme_id']:
                        return {
                            'success': False,
                            'message': 'Merchant scheme not found'
                        }

                    charges = self.calculate_charges(
                        float(payout_data['amount']),
                        merchant['scheme_id'],
                        'PAYOUT'
                    )

                    if not charges:
                        return {
                            'success': False,
                            'message': 'Unable to calculate charges'
                        }

                    # Validate wallet balance before creating a new transaction.
                    cursor.execute("""
                        SELECT COALESCE(settled_balance, 0) AS available_balance
                        FROM merchant_wallet
                        WHERE merchant_id = %s
                    """, (merchant_id,))
                    wallet_result = cursor.fetchone()

                    available_balance = (
                        float(wallet_result['available_balance'])
                        if wallet_result else 0.00
                    )

                    total_deduction = (
                        float(payout_data['amount']) +
                        float(charges['charge_amount'])
                    )

                    if total_deduction > available_balance:
                        return {
                            'success': False,
                            'message': (
                                f'Insufficient balance in wallet, '
                                f'remaining balance: ₹{available_balance:.2f}'
                            )
                        }

                reference_id = payout_data['reference_id']

                # Reuse an existing transaction if payout_routes.py already
                # created one for this reference.
                cursor.execute("""
                    SELECT txn_id
                    FROM payout_transactions
                    WHERE reference_id = %s
                      AND UPPER(pg_partner) = 'PAYSTOREPE_VELTRIX'
                    LIMIT 1
                """, (reference_id,))
                existing_txn = cursor.fetchone()

                if existing_txn:
                    txn_id = existing_txn['txn_id']
                    print(f"Using existing PayStorePe transaction: {txn_id}")
                else:
                    identifier = admin_id if is_admin_payout else merchant_id
                    txn_id = self.generate_txn_id(identifier, reference_id)

                    cursor.execute("""
                        INSERT INTO payout_transactions (
                            txn_id,
                            merchant_id,
                            admin_id,
                            reference_id,
                            amount,
                            charge_amount,
                            charge_type,
                            net_amount,
                            bene_name,
                            bene_email,
                            bene_mobile,
                            bene_bank,
                            ifsc_code,
                            account_no,
                            payment_type,
                            purpose,
                            status,
                            pg_partner,
                            callback_url,
                            remarks
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        txn_id,
                        merchant_id,
                        admin_id,
                        reference_id,
                        float(payout_data['amount']),
                        charges['charge_amount'],
                        charges['charge_type'],
                        charges['net_amount'],
                        payout_data['bene_name'],
                        payout_data.get('bene_email', ''),
                        payout_data.get('bene_mobile', ''),
                        payout_data.get('bank_name', ''),
                        payout_data['bene_ifsc'],
                        payout_data['bene_account'],
                        payout_data.get('payment_mode', 'IMPS'),
                        payout_data.get('narration', 'Payout'),
                        'INITIATED',
                        'PayStorePe_Veltrix',
                        payout_data.get('callback_url') or self.callback_url,
                        payout_data.get('remarks', '')
                    ))

                    conn.commit()
                    print(f"Created PayStorePe transaction: {txn_id}")

                # PayStorePe's client_id is the portal reference/order ID.
                client_id = reference_id

                from flask import request
                try:
                    webhook_url = f"{request.host_url.rstrip('/')}/api/callback/paystorepe_veltrix/payout".replace("http://", "https://")
                except RuntimeError:
                    webhook_url = self.callback_url


                payload = {
                    'client_id': client_id,
                    'mobile_number': payout_data.get('bene_mobile', ''),
                    'email': payout_data.get('bene_email', ''),
                    'beneficiary_name': payout_data['bene_name'],
                    'account_number': payout_data['bene_account'],
                    'ifsc_code': payout_data['bene_ifsc'],
                    'bank_name': payout_data.get('bank_name', ''),
                    'amount': float(payout_data['amount']),
                    'txn_mode': payout_data.get('payment_mode', 'IMPS'),
                    'webhook_url': webhook_url
                }

                url = f"{self.base_url}/api/payout/v1/payout-initiate"

                print("=" * 80)
                print("CALLING PAYSTOREPE_VELTRIX PAYOUT API")
                print("=" * 80)
                print(f"URL: {url}")
                print(
                    "Payload: "
                    + json.dumps(
                        {**payload, 'webhook_url': webhook_url},
                        indent=2
                    )
                )

                response = requests.post(
                    url,
                    headers=self.get_headers(),
                    json=payload,
                    timeout=30
                )

                print("PayStorePe_Veltrix Response:")
                print(f"HTTP Status: {response.status_code}")
                print(f"Raw Response: {response.text}")
                print("=" * 80)

                try:
                    response_data = response.json()
                except ValueError:
                    error_msg = (
                        f'PayStorePe_Veltrix returned invalid JSON: '
                        f'{response.text[:500]}'
                    )

                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = 'FAILED',
                            error_message = %s,
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (error_msg, txn_id))
                    conn.commit()

                    return {
                        'success': False,
                        'message': error_msg
                    }

                gateway_status = str(
                    response_data.get('status', 'FAILED')
                ).upper()

                gateway_txn_id = response_data.get('txn_id')

                # PayStorePe returns FAILED in the JSON body for business/API
                # failures such as insufficient gateway wallet balance.
                if response.status_code not in [200, 201] or gateway_status == 'FAILED':
                    error_msg = response_data.get(
                        'message',
                        f'PayStorePe_Veltrix API error: HTTP {response.status_code}'
                    )

                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = 'FAILED',
                            pg_txn_id = %s,
                            error_message = %s,
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (gateway_txn_id, error_msg, txn_id))
                    conn.commit()

                    return {
                        'success': False,
                        'message': error_msg,
                        'txn_id': txn_id,
                        'reference_id': reference_id,
                        'paystorepe_txn_id': gateway_txn_id,
                        'status': 'FAILED'
                    }

                # ACCEPTED means the payout request was accepted by the
                # gateway. Final status comes through the webhook.
                if gateway_status == 'ACCEPTED':
                    mapped_status = 'QUEUED'
                elif gateway_status in ['PENDING', 'PROCESSING', 'INITIATED', 'QUEUED']:
                    mapped_status = 'QUEUED'
                else:
                    mapped_status = 'QUEUED'

                cursor.execute("""
                    UPDATE payout_transactions
                    SET status = %s,
                        pg_txn_id = %s,
                        updated_at = NOW()
                    WHERE txn_id = %s
                """, (mapped_status, gateway_txn_id, txn_id))
                conn.commit()

                return {
                    'success': True,
                    'message': response_data.get(
                        'message',
                        'Payout initiated successfully'
                    ),
                    'txn_id': txn_id,
                    'reference_id': reference_id,
                    'paystorepe_txn_id': gateway_txn_id,
                    'status': mapped_status,
                    'gateway_status': gateway_status,
                    'amount': response_data.get(
                        'amount',
                        payout_data['amount']
                    ),
                    'service_charge': response_data.get('service_charge', 0),
                    'gst_amount': response_data.get('gst_amount', 0),
                    'deduct_amount': response_data.get(
                        'deduct_amount',
                        payout_data['amount']
                    ),
                    'wallet_balance': response_data.get('wallet_balance')
                }

        except requests.Timeout:
            error_msg = 'PayStorePe_Veltrix payout API request timed out'

            if conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET
                                status = 'INPROCESS',
                                error_message = %s,
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (
                            error_msg,
                            locals().get('txn_id')
                        ))
                        conn.commit()
                except Exception:
                    pass

            return {
                'success': True,
                'message': (
                    'PayStorePe request timed out. '
                    'Transaction is awaiting webhook confirmation.'
                ),
                'txn_id': locals().get('txn_id'),
                'reference_id': locals().get('reference_id'),
                'status': 'INPROCESS',
                'gateway_status': 'UNKNOWN',
                'reconciliation_required': True
            }

        except requests.RequestException as e:
            error_msg = f'PayStorePe_Veltrix API connection error: {str(e)}'

            if conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED',
                                error_message = %s,
                                updated_at = NOW()
                            WHERE txn_id = %s
                        """, (error_msg, locals().get('txn_id')))
                        conn.commit()
                except Exception:
                    pass

            return {
                'success': False,
                'message': error_msg
            }

        except Exception as e:
            print(f"PayStorePe_Veltrix payout error: {e}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'message': f'Internal error: {str(e)}'
            }

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


# Global instance
paystorepe_veltrix_service = PayStorePeVeltrixService()

# Explicit module exports for reliable Flask/Gunicorn imports.
__all__ = ["paystorepe_veltrix_service", "PayStorePeVeltrixService"]
