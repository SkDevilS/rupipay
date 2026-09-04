"""
Bridgmoney Coco Payout Service
Handles integration with Bridgmoney Coco Payout API using HMAC SHA256 v2 authentication.
Prefix for transactions: BM_CO_TXN_
"""

import os
import time
import uuid
import json
import hmac
import hashlib
import requests
from urllib.parse import urlparse
from datetime import datetime
from config import Config
from database_pooled import get_db_connection


class BridgmoneyCocoService:
    def __init__(self):
        self.base_url = Config.BRIDGMONEY_COCO_BASE_URL.rstrip('/')
        self.api_key = Config.BRIDGMONEY_COCO_API_KEY
        self.api_secret = Config.BRIDGMONEY_COCO_API_SECRET
        self.beneficiary_id = Config.BRIDGMONEY_COCO_BENEFICIARY_ID
        
        # Parse host for v2 canonical string
        parsed_url = urlparse(self.base_url)
        self.host = (parsed_url.netloc or parsed_url.path).lower()

    def _hmac_sha256(self, canonical_string):
        """Generate HMAC SHA256 hex signature over canonical string"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            canonical_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def get_signed_headers_v2(self, method, path_and_query, body_str="", idempotency_key=None):
        """
        Generate HMAC v2 headers as per Bridgmoney Coco API documentation:
        Canonical string: METHOD | HOST | PATH_AND_QUERY | API_KEY | TIMESTAMP | NONCE | SHA256_HEX(BODY)
        """
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        body_hash = hashlib.sha256(body_str.encode('utf-8')).hexdigest()
        
        canonical = "|".join([
            method.upper(),
            self.host,
            path_and_query,
            self.api_key,
            timestamp,
            nonce,
            body_hash
        ])
        
        signature = self._hmac_sha256(canonical)
        
        headers = {
            "x-bridg-sig-version": "2",
            "x-api-key": self.api_key,
            "x-timestamp": timestamp,
            "x-nonce": nonce,
            "x-signature": signature,
            "Content-Type": "application/json"
        }
        
        if idempotency_key:
            headers["Idempotency-Key"] = str(idempotency_key)
            
        return headers

    def generate_txn_id(self, merchant_id, reference_id):
        """Generate unique transaction ID with BM_CO_TXN prefix"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"BM_CO_TXN_{merchant_id}_{reference_id}_{timestamp}"

    def calculate_charges(self, amount, scheme_id, service_type='PAYOUT'):
        """Calculate payout charges based on scheme"""
        try:
            conn = get_db_connection()
            if not conn:
                print("Charge calculation error: Database connection failed")
                return {
                    'charge_amount': 0.00,
                    'charge_type': 'FIXED',
                    'net_amount': round(float(amount), 2)
                }

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
                    charge_amount = 0.0
                    if charge['charge_type'] == 'PERCENTAGE':
                        charge_amount = (float(amount) * float(charge['charge_value'])) / 100
                    else:
                        charge_amount = float(charge['charge_value'])

                    net_amount = float(amount) + charge_amount

                    conn.close()
                    return {
                        'charge_amount': round(charge_amount, 2),
                        'charge_type': charge['charge_type'],
                        'net_amount': round(net_amount, 2)
                    }
                else:
                    print(f"No charge configuration found for scheme_id={scheme_id}, service_type={service_type}, amount={amount}")
                    conn.close()
                    return {
                        'charge_amount': 0.00,
                        'charge_type': 'FIXED',
                        'net_amount': round(float(amount), 2)
                    }

        except Exception as e:
            print(f"Charge calculation error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'charge_amount': 0.00,
                'charge_type': 'FIXED',
                'net_amount': round(float(amount), 2)
            }

    def add_beneficiary(self, name, phone_number, account_number=None, ifsc=None, vpa=None, email=None):
        """
        Add a beneficiary by providing name, phone number, and payment details.
        Only active beneficiaries can receive payouts.
        Returns newly created beneficiaryId (201) or existing deduplicated beneficiaryId (409).
        Bank beneficiaries dedupe on accountNumber + ifsc; UPI beneficiaries dedupe on vpa.
        """
        try:
            name_str = str(name).strip()[:100] if name else "Beneficiary"
            phone_str = str(phone_number).strip() if phone_number else "9999999999"
            
            payload = {
                "name": name_str,
                "phoneNumber": phone_str
            }
            if email and str(email).strip():
                payload["email"] = str(email).strip()

            if vpa and str(vpa).strip():
                # UPI target
                payload["vpa"] = str(vpa).strip()
            elif account_number and ifsc:
                # Bank target
                payload["accountNumber"] = str(account_number).strip()
                payload["ifsc"] = str(ifsc).strip().upper()
            else:
                return {
                    'success': False,
                    'message': 'Must provide either (accountNumber + ifsc) or vpa'
                }

            body_str = json.dumps(payload, separators=(',', ':'))
            path_and_query = "/v1/beneficiaries"
            headers = self.get_signed_headers_v2("POST", path_and_query, body_str)
            url = f"{self.base_url}{path_and_query}"

            print("=" * 80)
            print(f"CALLING BRIDGMONEY_COCO ADD BENEFICIARY: {url}")
            print(f"Payload: {body_str}")
            print("=" * 80)

            response = requests.post(
                url,
                headers=headers,
                data=body_str,
                timeout=30
            )

            print(f"Bridgmoney_Coco Add Beneficiary Response: {response.status_code} - {response.text}")

            try:
                res_json = response.json()
            except Exception:
                res_json = {}

            if response.status_code in [200, 201]:
                data_obj = res_json.get('data', {}) if isinstance(res_json.get('data'), dict) else {}
                beneficiary_id = data_obj.get('beneficiaryId', '')
                beneficiary_code = data_obj.get('beneficiaryCode', '')
                return {
                    'success': True,
                    'beneficiary_id': beneficiary_id,
                    'beneficiaryId': beneficiary_id,
                    'beneficiary_code': beneficiary_code,
                    'beneficiaryCode': beneficiary_code,
                    'existing': False,
                    'status_code': response.status_code,
                    'message': res_json.get('message', 'Beneficiary created successfully'),
                    'data': data_obj
                }
            elif response.status_code == 409:
                # Beneficiary already exists under the same business - return existing beneficiaryId
                data_obj = res_json.get('data', {}) if isinstance(res_json.get('data'), dict) else {}
                beneficiary_id = data_obj.get('beneficiaryId', '')
                return {
                    'success': True,
                    'beneficiary_id': beneficiary_id,
                    'beneficiaryId': beneficiary_id,
                    'existing': True,
                    'status_code': 409,
                    'message': res_json.get('message', 'Beneficiary already exists'),
                    'data': data_obj
                }
            else:
                error_msg = res_json.get('message') or f"Beneficiary API error: HTTP {response.status_code} - {response.text}"
                return {
                    'success': False,
                    'message': error_msg,
                    'status_code': response.status_code,
                    'data': res_json.get('data')
                }
        except Exception as e:
            print(f"Bridgmoney_Coco add beneficiary error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f"Exception adding beneficiary: {str(e)}"}

    def list_beneficiaries(self, page=1, limit=50, status=None):
        """
        List beneficiaries for the tenant.
        GET /v1/beneficiaries
        """
        try:
            params = []
            if page:
                params.append(f"page={page}")
            if limit:
                params.append(f"limit={limit}")
            if status:
                params.append(f"status={status}")
            
            query_str = f"?{'&'.join(params)}" if params else ""
            path_and_query = f"/v1/beneficiaries{query_str}"
            headers = self.get_signed_headers_v2("GET", path_and_query, "")
            url = f"{self.base_url}{path_and_query}"

            print(f"CALLING BRIDGMONEY_COCO LIST BENEFICIARIES: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            print(f"Bridgmoney_Coco List Beneficiaries Response: {response.status_code} - {response.text[:200]}")

            try:
                res_json = response.json()
            except Exception:
                res_json = {}

            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'data': res_json.get('data', []),
                    'meta': res_json.get('meta'),
                    'message': res_json.get('message', 'Beneficiaries listed successfully')
                }
            else:
                error_msg = res_json.get('message') or f"HTTP {response.status_code}"
                return {'success': False, 'message': error_msg, 'status_code': response.status_code}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_beneficiary(self, beneficiary_id):
        """
        Get details of a specific beneficiary by ID.
        GET /v1/beneficiaries/{beneficiaryId}
        """
        try:
            path_and_query = f"/v1/beneficiaries/{beneficiary_id}"
            headers = self.get_signed_headers_v2("GET", path_and_query, "")
            url = f"{self.base_url}{path_and_query}"

            response = requests.get(url, headers=headers, timeout=30)
            try:
                res_json = response.json()
            except Exception:
                res_json = {}

            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'data': res_json.get('data', {}),
                    'message': res_json.get('message', 'Beneficiary retrieved successfully')
                }
            else:
                error_msg = res_json.get('message') or f"HTTP {response.status_code}"
                return {'success': False, 'message': error_msg, 'status_code': response.status_code}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def update_beneficiary(self, beneficiary_id, name=None, phone_number=None, email=None, status=None):
        """
        Update an existing beneficiary.
        PATCH /v1/beneficiaries/{beneficiaryId}
        """
        try:
            payload = {}
            if name:
                payload["name"] = str(name).strip()[:100]
            if phone_number:
                payload["phoneNumber"] = str(phone_number).strip()
            if email is not None:
                payload["email"] = str(email).strip()
            if status:
                payload["status"] = str(status).strip()

            body_str = json.dumps(payload, separators=(',', ':')) if payload else ""
            path_and_query = f"/v1/beneficiaries/{beneficiary_id}"
            headers = self.get_signed_headers_v2("PATCH", path_and_query, body_str)
            url = f"{self.base_url}{path_and_query}"

            response = requests.patch(url, headers=headers, data=body_str, timeout=30)
            try:
                res_json = response.json()
            except Exception:
                res_json = {}

            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'data': res_json.get('data', {}),
                    'message': res_json.get('message', 'Beneficiary updated successfully')
                }
            else:
                error_msg = res_json.get('message') or f"HTTP {response.status_code}"
                return {'success': False, 'message': error_msg, 'status_code': response.status_code}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def archive_beneficiary(self, beneficiary_id):
        """
        Archive (deactivate) a beneficiary.
        Only active beneficiaries can receive payouts.
        Tries DELETE /v1/beneficiaries/{beneficiaryId} or fallback to PATCH status='ARCHIVED'.
        """
        try:
            path_and_query = f"/v1/beneficiaries/{beneficiary_id}"
            headers = self.get_signed_headers_v2("DELETE", path_and_query, "")
            url = f"{self.base_url}{path_and_query}"

            response = requests.delete(url, headers=headers, timeout=30)
            try:
                res_json = response.json()
            except Exception:
                res_json = {}

            if response.status_code in [200, 201, 204]:
                return {
                    'success': True,
                    'data': res_json.get('data', {}),
                    'message': res_json.get('message', 'Beneficiary archived successfully')
                }
            elif response.status_code in [404, 405]:
                # Fallback to PATCH status='ARCHIVED'
                return self.update_beneficiary(beneficiary_id, status="ARCHIVED")
            else:
                error_msg = res_json.get('message') or f"HTTP {response.status_code}"
                return {'success': False, 'message': error_msg, 'status_code': response.status_code}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def reactivate_beneficiary(self, beneficiary_id):
        """
        Reactivate an archived beneficiary.
        POST /v1/beneficiaries/{beneficiaryId}/reactivate or fallback to PATCH status='ACTIVE'.
        """
        try:
            path_and_query = f"/v1/beneficiaries/{beneficiary_id}/reactivate"
            headers = self.get_signed_headers_v2("POST", path_and_query, "")
            url = f"{self.base_url}{path_and_query}"

            response = requests.post(url, headers=headers, timeout=30)
            try:
                res_json = response.json()
            except Exception:
                res_json = {}

            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'data': res_json.get('data', {}),
                    'message': res_json.get('message', 'Beneficiary reactivated successfully')
                }
            elif response.status_code in [404, 405]:
                # Fallback to PATCH status='ACTIVE'
                return self.update_beneficiary(beneficiary_id, status="ACTIVE")
            else:
                error_msg = res_json.get('message') or f"HTTP {response.status_code}"
                return {'success': False, 'message': error_msg, 'status_code': response.status_code}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_or_create_beneficiary_for_payout(self, payout_data):
        """
        Helper method that adds or dedupes a beneficiary before payout initiation.
        Returns beneficiaryId to be used in POST /v1/payouts.
        """
        try:
            existing_id = payout_data.get('beneficiary_id') or payout_data.get('beneficiaryId')
            # If an explicit valid beneficiaryId is already provided, use it
            if existing_id and str(existing_id).strip() != str(self.beneficiary_id).strip():
                print(f"Using explicitly provided beneficiaryId: {existing_id}")
                return str(existing_id).strip()

            name = payout_data.get('bene_name') or payout_data.get('account_holder_name') or "Merchant Beneficiary"
            phone_number = payout_data.get('bene_mobile') or payout_data.get('phoneNumber') or payout_data.get('mobile') or "9876543210"
            email = payout_data.get('bene_email') or payout_data.get('email') or ""

            mode = str(payout_data.get('payment_mode', '')).upper()
            vpa = payout_data.get('vpa') or payout_data.get('bene_vpa') or payout_data.get('upi_id')
            account_number = payout_data.get('bene_account') or payout_data.get('account_number') or payout_data.get('account_no')
            ifsc = payout_data.get('bene_ifsc') or payout_data.get('ifsc_code') or payout_data.get('ifsc')

            if mode == 'UPI' or (vpa and not (account_number and ifsc)):
                result = self.add_beneficiary(
                    name=name,
                    phone_number=phone_number,
                    vpa=vpa,
                    email=email
                )
            else:
                result = self.add_beneficiary(
                    name=name,
                    phone_number=phone_number,
                    account_number=account_number,
                    ifsc=ifsc,
                    email=email
                )

            if result and result.get('success') and result.get('beneficiary_id'):
                beneficiary_id = result.get('beneficiary_id')
                print(f"Successfully obtained beneficiaryId for payout: {beneficiary_id} (existing={result.get('existing', False)})")
                return str(beneficiary_id)
            else:
                print(f"Warning: add_beneficiary did not return beneficiaryId ({result.get('message')}). Using fallback.")
                return str(existing_id or self.beneficiary_id)
        except Exception as e:
            print(f"Error in get_or_create_beneficiary_for_payout: {e}")
            return str(payout_data.get('beneficiary_id') or payout_data.get('beneficiaryId') or self.beneficiary_id)

    def initiate_payout(self, merchant_id, payout_data, admin_id=None):
        """
        Initiate a payout using Bridgmoney Coco API
        
        Args:
            merchant_id: Merchant ID (None for admin personal payout)
            payout_data: Dict containing amount, bene_name, bene_account, bene_ifsc, reference_id, etc.
            admin_id: Admin ID if admin personal payout
        """
        try:
            is_admin_payout = merchant_id is None and admin_id is not None
            print(f"Initiating Bridgmoney_Coco Payout - Merchant: {merchant_id}, Admin: {admin_id}, Ref: {payout_data.get('reference_id')}")

            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database connection failed'}

            try:
                with conn.cursor() as cursor:
                    # Validate balance for merchant payouts
                    if not is_admin_payout:
                        cursor.execute("""
                            SELECT scheme_id, is_active FROM merchants WHERE merchant_id = %s
                        """, (merchant_id,))
                        merchant = cursor.fetchone()

                        scheme_id = merchant['scheme_id'] if merchant and merchant.get('scheme_id') else None
                        charges = self.calculate_charges(payout_data['amount'], scheme_id, 'PAYOUT')
                        if not charges:
                            charges = {
                                'charge_amount': 0.00,
                                'charge_type': 'FIXED',
                                'net_amount': float(payout_data['amount'])
                            }

                        cursor.execute("""
                            SELECT txn_id FROM payout_transactions
                            WHERE reference_id = %s AND pg_partner = 'Bridgmoney_Coco'
                        """, (payout_data['reference_id'],))
                        
                        if not cursor.fetchone():
                            total_deduction = float(payout_data['amount']) + float(charges['charge_amount'])
                            cursor.execute("""
                                SELECT COALESCE(settled_balance, 0) as available_balance
                                FROM merchant_wallet
                                WHERE merchant_id = %s
                            """, (merchant_id,))
                            wallet_result = cursor.fetchone()
                            available_balance = float(wallet_result['available_balance']) if wallet_result else 0.00
                            
                            if total_deduction > available_balance:
                                return {
                                    'success': False,
                                    'message': f'Insufficient balance in wallet, remaining balance: ₹{available_balance:.2f}'
                                }
                    else:
                        charges = {
                            'charge_amount': 0.0,
                            'charge_type': 'FLAT',
                            'net_amount': float(payout_data['amount']),
                            'total_deduction': float(payout_data['amount'])
                        }

                    # Check if transaction already exists (e.g. created by caller)
                    cursor.execute("""
                        SELECT txn_id FROM payout_transactions
                        WHERE reference_id = %s AND pg_partner = 'Bridgmoney_Coco'
                    """, (payout_data['reference_id'],))
                    existing_txn = cursor.fetchone()

                    if existing_txn:
                        txn_id = existing_txn['txn_id']
                        print(f"Using existing transaction: {txn_id}")
                    else:
                        identifier = admin_id if is_admin_payout else merchant_id
                        txn_id = self.generate_txn_id(identifier, payout_data['reference_id'])

                        cursor.execute("""
                            INSERT INTO payout_transactions (
                                txn_id, merchant_id, admin_id, reference_id, amount, charge_amount,
                                charge_type, net_amount, bene_name, bene_email, bene_mobile,
                                bene_bank, ifsc_code, account_no, payment_type, purpose,
                                status, pg_partner, callback_url, remarks
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'INITIATED', 'Bridgmoney_Coco', %s, %s)
                        """, (
                            txn_id, merchant_id, admin_id, payout_data['reference_id'],
                            payout_data['amount'], charges['charge_amount'],
                            charges['charge_type'], charges['net_amount'],
                            payout_data['bene_name'],
                            payout_data.get('bene_email', ''),
                            payout_data.get('bene_mobile', ''),
                            payout_data.get('bank_name', ''),
                            payout_data['bene_ifsc'],
                            payout_data['bene_account'],
                            payout_data.get('payment_mode', 'IMPS'),
                            payout_data.get('narration', 'Payment'),
                            payout_data.get('callback_url', ''),
                            payout_data.get('remarks', '')
                        ))
                        conn.commit()
                        print(f"Created new transaction: {txn_id}")

                    # Determine rail / transactionType (I, N, R, U, S)
                    mode = str(payout_data.get('payment_mode', 'IMPS')).upper()
                    mode_map = {
                        'IMPS': 'I', 'NEFT': 'N', 'RTGS': 'R', 'UPI': 'U', 'SELF': 'S',
                        'I': 'I', 'N': 'N', 'R': 'R', 'U': 'U', 'S': 'S'
                    }
                    transaction_type = mode_map.get(mode, 'I')

                    # Beneficiary ID resolution: add/dedupe beneficiary first to get beneficiaryId for payout
                    beneficiary_id = self.get_or_create_beneficiary_for_payout(payout_data)

                    # Prepare Bridgmoney Coco API request payload
                    payload = {
                        "beneficiaryId": str(beneficiary_id),
                        "amount": f"{float(payout_data['amount']):.2f}",
                        "transactionType": transaction_type,
                        "merchantReferenceId": str(payout_data['reference_id'])[:128]
                    }

                    body_str = json.dumps(payload, separators=(',', ':'))
                    path_and_query = "/v1/payouts"
                    headers = self.get_signed_headers_v2(
                        method="POST",
                        path_and_query=path_and_query,
                        body_str=body_str,
                        idempotency_key=str(payout_data['reference_id'])
                    )

                    url = f"{self.base_url}{path_and_query}"
                    print(f"=" * 80)
                    print(f"CALLING BRIDGMONEY_COCO API: {url}")
                    print(f"Payload: {body_str}")
                    print(f"=" * 80)

                    response = requests.post(
                        url,
                        headers=headers,
                        data=body_str,
                        timeout=30
                    )

                    print(f"Bridgmoney_Coco API Response: {response.status_code} - {response.text}")

                    if response.status_code not in [200, 201]:
                        error_msg = f"Bridgmoney_Coco API error: HTTP {response.status_code} - {response.text}"
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (error_msg, txn_id))
                        conn.commit()
                        return {'success': False, 'message': error_msg}

                    try:
                        res_json = response.json()
                    except json.JSONDecodeError as e:
                        error_msg = f"Bridgmoney_Coco API returned invalid JSON: {str(e)}"
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (error_msg, txn_id))
                        conn.commit()
                        return {'success': False, 'message': error_msg}

                    # Check response status
                    top_status = str(res_json.get('status', '')).upper()
                    if top_status in ['ERR', 'ERROR', 'FAILED']:
                        error_msg = res_json.get('message', 'Gateway returned error status')
                        cursor.execute("""
                            UPDATE payout_transactions
                            SET status = 'FAILED', error_message = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (error_msg, txn_id))
                        conn.commit()
                        return {'success': False, 'message': error_msg}

                    data_obj = res_json.get('data', {}) if isinstance(res_json.get('data'), dict) else res_json
                    payout_txn_id = (
                        data_obj.get('payoutTransactionId') or
                        data_obj.get('transactionId') or
                        data_obj.get('id') or
                        ''
                    )
                    raw_status = data_obj.get('status', 3)

                    # Map Bridgmoney Coco status (3 -> QUEUED, 11 -> SUCCESS, 12 -> FAILED)
                    status_map = {
                        3: 'QUEUED', '3': 'QUEUED',
                        11: 'SUCCESS', '11': 'SUCCESS',
                        12: 'FAILED', '12': 'FAILED',
                        'SUCCESS': 'SUCCESS', 'SUCCESSFUL': 'SUCCESS',
                        'PENDING': 'QUEUED', 'INITIATED': 'QUEUED', 'QUEUED': 'QUEUED',
                        'FAILED': 'FAILED'
                    }
                    mapped_status = status_map.get(raw_status, 'QUEUED')
                    if isinstance(raw_status, str):
                        mapped_status = status_map.get(raw_status.upper(), 'QUEUED')

                    print(f"Bridgmoney_Coco Extracted TxnID: {payout_txn_id}, Status: {raw_status} -> {mapped_status}")

                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (mapped_status, payout_txn_id, txn_id))
                    conn.commit()

                    return {
                        'success': True,
                        'message': 'Payout initiated successfully',
                        'txn_id': txn_id,
                        'reference_id': payout_data['reference_id'],
                        'bridgmoney_coco_txn_id': payout_txn_id,
                        'status': mapped_status,
                        'amount': payout_data['amount'],
                        'charge_amount': charges['charge_amount']
                    }

            finally:
                conn.close()

        except Exception as e:
            print(f"Bridgmoney_Coco payout error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Internal error: {str(e)}'}

    def check_payout_status(self, transaction_id=None, external_ref=None):
        """
        Check payout status from Bridgmoney Coco
        
        Args:
            transaction_id: Bridgmoney Coco transaction ID / payoutTransactionId
            external_ref: System reference ID (merchantReferenceId)
        """
        try:
            print(f"Checking Bridgmoney_Coco payout status - transaction_id: {transaction_id}, external_ref: {external_ref}")
            
            if transaction_id:
                path_and_query = f"/v1/payouts/{transaction_id}"
            elif external_ref:
                path_and_query = f"/v1/payouts?merchantReferenceId={external_ref}"
            else:
                return {'success': False, 'message': 'Missing transaction_id or external_ref'}
                
            headers = self.get_signed_headers_v2("GET", path_and_query, "")
            url = f"{self.base_url}{path_and_query}"
            
            response = requests.get(url, headers=headers, timeout=30)
            print(f"Bridgmoney_Coco Status Response: {response.status_code} - {response.text}")
            
            if response.status_code not in [200, 201]:
                return {'success': False, 'message': f'Status check failed: {response.text}'}
                
            res_json = response.json()
            data_obj = res_json.get('data', {}) if isinstance(res_json.get('data'), dict) else res_json
            
            raw_status = data_obj.get('status', 3)
            utr = (
                data_obj.get('utr') or
                data_obj.get('transactionReference') or
                data_obj.get('utr_no') or
                ''
            )
            
            status_map = {
                3: 'QUEUED', '3': 'QUEUED',
                11: 'SUCCESS', '11': 'SUCCESS',
                12: 'FAILED', '12': 'FAILED',
                'SUCCESS': 'SUCCESS', 'SUCCESSFUL': 'SUCCESS',
                'PENDING': 'QUEUED', 'INITIATED': 'QUEUED', 'QUEUED': 'QUEUED',
                'FAILED': 'FAILED'
            }
            mapped_status = status_map.get(raw_status, 'QUEUED')
            if isinstance(raw_status, str):
                mapped_status = status_map.get(raw_status.upper(), 'QUEUED')
                
            return {
                'success': True,
                'status': mapped_status,
                'transaction_id': data_obj.get('payoutTransactionId') or data_obj.get('transactionId') or transaction_id,
                'external_ref': data_obj.get('merchantReferenceId') or external_ref,
                'utr': utr,
                'amount': data_obj.get('amount'),
                'message': res_json.get('message', 'Status retrieved successfully')
            }
            
        except Exception as e:
            print(f"Bridgmoney_Coco status check error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Status check error: {str(e)}'}


# Global service instance
bridgmoney_coco_service = BridgmoneyCocoService()
