"""
VIYONAPAY Payin Callback Routes
Handles webhook notifications from VIYONAPAY for payment status updates
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA
import json
import base64
import os
from config import Config

viyonapay_callback_bp = Blueprint('viyonapay_callback', __name__, url_prefix='/api/callback/viyonapay')

def load_viyonapay_public_key(config_type='TRUAXIS'):
    """Load VIYONAPAY's public key for signature verification"""
    try:
        if config_type == 'BARRINGER':
            key_path = Config.VIYONAPAY_BARRINGER_SERVER_PUBLIC_KEY_PATH
        else:
            key_path = Config.VIYONAPAY_SERVER_PUBLIC_KEY_PATH
        
        with open(key_path, 'r') as f:
            key_data = f.read()
        return RSA.import_key(key_data)
    except Exception as e:
        print(f"❌ Failed to load VIYONAPAY {config_type} public key: {e}")
        return None

def load_client_secret_key(config_type='TRUAXIS'):
    """Load client secret key for decryption (16-byte hex key)"""
    try:
        # The secret key should be a 16-byte (128-bit) key in hex format (32 hex chars)
        # This is the same key used for webhook encryption/decryption
        if config_type == 'BARRINGER':
            secret_key_hex = Config.VIYONAPAY_BARRINGER_WEBHOOK_SECRET_KEY if hasattr(Config, 'VIYONAPAY_BARRINGER_WEBHOOK_SECRET_KEY') else Config.VIYONAPAY_WEBHOOK_SECRET_KEY
        else:
            secret_key_hex = Config.VIYONAPAY_WEBHOOK_SECRET_KEY
        
        if not secret_key_hex:
            print(f"❌ VIYONAPAY {config_type} WEBHOOK_SECRET_KEY not configured in .env")
            return None
        key_bytes = bytes.fromhex(secret_key_hex)
        if len(key_bytes) != 16:
            print(f"❌ Invalid webhook secret key length: {len(key_bytes)} bytes (expected 16)")
            return None
        return key_bytes
    except Exception as e:
        print(f"❌ Failed to load webhook secret key for {config_type}: {e}")
        return None

def verify_signature(payload_dict, signature_b64, config_type='TRUAXIS'):
    """
    Verify webhook signature using VIYONAPAY's public key
    
    Args:
        payload_dict: Webhook payload dictionary
        signature_b64: Base64-encoded signature from X-SIGNATURE header
        config_type: 'TRUAXIS' or 'BARRINGER'
    
    Returns:
        Boolean indicating if signature is valid
    """
    try:
        # Load public key for the specific configuration
        public_key = load_viyonapay_public_key(config_type)
        if not public_key:
            return False
        
        # Convert payload to canonical JSON
        json_data = json.dumps(payload_dict, separators=(',', ':'), sort_keys=True)
        
        # Create SHA-256 hash
        hash_obj = SHA256.new(json_data.encode('utf-8'))
        
        # Decode signature
        signature = base64.b64decode(signature_b64)
        
        # Verify signature
        pkcs1_15.new(public_key).verify(hash_obj, signature)
        
        return True
    except Exception as e:
        print(f"❌ Signature verification failed for {config_type}: {e}")
        return False

def decrypt_webhook_response(encrypted_b64, secret_key, aad_dict):
    """
    Decrypt webhook response using AES-128-GCM
    Based on Viyonapay's official decryption logic
    
    Args:
        encrypted_b64: Base64-encoded encrypted data
        secret_key: 16-byte secret key (bytes or hex string)
        aad_dict: Additional Authenticated Data (timestamp and request_id)
    
    Returns:
        Decrypted dictionary or None
    """
    try:
        # Convert key from hex string to bytes if needed
        if isinstance(secret_key, str):
            key16 = bytes.fromhex(secret_key)
        else:
            key16 = secret_key
        
        # Validate key length
        if not isinstance(key16, (bytes, bytearray)) or len(key16) != 16:
            print(f"❌ Invalid key: must be 16 bytes, got {len(key16) if isinstance(key16, (bytes, bytearray)) else 'invalid type'}")
            return None
        
        # Decode base64
        raw = base64.b64decode(encrypted_b64)
        
        # Extract components: nonce (12 bytes) + ciphertext (includes auth tag)
        nonce = raw[:12]
        ciphertext = raw[12:]  # Ciphertext includes the authentication tag
        
        # Convert AAD to canonical JSON (sorted keys, no spaces)
        # IMPORTANT: timestamp must be int, not string
        aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
        aad_bytes = aad_json.encode('utf-8')
        
        # Decrypt using AESGCM (handles tag automatically)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(key16)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        
        return json.loads(plaintext.decode('utf-8'))
    except Exception as e:
        print(f"❌ Webhook decryption error: {e}")
        import traceback
        traceback.print_exc()
        return None

def encrypt_webhook_acknowledgment(data_dict, secret_key, aad_dict):
    """
    Encrypt webhook acknowledgment response using AES-GCM
    
    Args:
        data_dict: Dictionary to encrypt
        secret_key: 16-byte secret key
        aad_dict: Additional Authenticated Data
    
    Returns:
        Base64-encoded encrypted data
    """
    try:
        from Crypto.Random import get_random_bytes
        
        # Convert data to JSON
        json_data = json.dumps(data_dict)
        
        # Convert AAD to canonical JSON
        aad_json = json.dumps(aad_dict, separators=(',', ':'), sort_keys=True)
        aad_bytes = aad_json.encode('utf-8')
        
        # Generate random 12-byte nonce
        nonce = get_random_bytes(12)
        
        # Create AES-GCM cipher
        cipher = AES.new(secret_key, AES.MODE_GCM, nonce=nonce)
        cipher.update(aad_bytes)
        
        # Encrypt data
        ciphertext, tag = cipher.encrypt_and_digest(json_data.encode('utf-8'))
        
        # Combine: nonce + ciphertext + tag
        encrypted_data = nonce + ciphertext + tag
        
        return base64.b64encode(encrypted_data).decode('utf-8')
    except Exception as e:
        print(f"❌ Webhook encryption error: {e}")
        return None

@viyonapay_callback_bp.route('/payin', methods=['POST'])
def viyonapay_payin_callback():
    """
    VIYONAPAY Payin Webhook Handler
    
    Receives payment status updates from VIYONAPAY
    Payload is sent as plain JSON, but response must be encrypted
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 VIYONAPAY Payin Callback Received")
        print(f"{'='*60}")
        
        # Log raw request for debugging
        print(f"\n📋 Raw Request Info:")
        print(f"  Method: {request.method}")
        print(f"  URL: {request.url}")
        print(f"  Remote Address: {request.remote_addr}")
        print(f"  Content-Type: {request.headers.get('Content-Type', 'None')}")
        print(f"  Content-Length: {request.headers.get('Content-Length', 'None')}")
        
        # Get headers
        signature = request.headers.get('X-SIGNATURE')
        timestamp_header = request.headers.get('X-TIMESTAMP')
        request_id_header = request.headers.get('X-Request-Id')
        api_key = request.headers.get('X-API-KEY')
        
        print(f"📋 Headers:")
        print(f"  X-SIGNATURE: {signature[:20] if signature else 'None'}...")
        print(f"  X-TIMESTAMP: {timestamp_header}")
        print(f"  X-Request-Id: {request_id_header}")
        print(f"  X-API-KEY: {api_key[:10] if api_key else 'None'}...")
        
        # Get webhook payload - support both JSON and form-data
        content_type = request.headers.get('Content-Type', '')
        print(f"  Content-Type: {content_type}")
        
        webhook_data = None
        
        # Try JSON first
        if 'application/json' in content_type or request.is_json:
            webhook_data = request.get_json(silent=True)
            if webhook_data:
                print(f"✓ Received JSON payload")
        
        # Try form data if JSON failed
        if not webhook_data and request.form:
            webhook_data = request.form.to_dict()
            print(f"✓ Received form-data payload")
        
        # Try raw data as fallback
        if not webhook_data and request.data:
            try:
                import json as json_lib
                webhook_data = json_lib.loads(request.data.decode('utf-8'))
                print(f"✓ Received raw JSON payload")
            except:
                pass
        
        if not webhook_data:
            print(f"❌ No webhook data received")
            print(f"  Content-Type: {content_type}")
            print(f"  Request data: {request.data[:200] if request.data else 'None'}")
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        print(f"\n📦 Webhook Payload (Encrypted):")
        print(json.dumps(webhook_data, indent=2))
        
        # Verify signature BEFORE decryption (signature is on the encrypted payload)
        # Try both configurations since we don't know which one was used yet
        config_type = None
        if signature:
            print(f"\n🔐 Verifying signature on encrypted payload...")
            print(f"  Signature (base64): {signature[:50]}...")
            
            # Try Truaxis first
            print(f"  Trying TRUAXIS configuration...")
            signature_valid = verify_signature(webhook_data, signature, 'TRUAXIS')
            
            if signature_valid:
                config_type = 'TRUAXIS'
                print(f"✓ Signature verified successfully with TRUAXIS")
            else:
                # Try Barringer
                print(f"  Trying BARRINGER configuration...")
                signature_valid = verify_signature(webhook_data, signature, 'BARRINGER')
                
                if signature_valid:
                    config_type = 'BARRINGER'
                    print(f"✓ Signature verified successfully with BARRINGER")
                else:
                    print(f"❌ Signature verification failed for both configurations")
                    
                    # Log details for debugging
                    print(f"\n🔍 Signature Debug Info:")
                    json_canonical = json.dumps(webhook_data, separators=(',', ':'), sort_keys=True)
                    print(f"  Payload (canonical JSON): {json_canonical[:200]}...")
                    
                    from Crypto.Hash import SHA256
                    hash_obj = SHA256.new(json_canonical.encode('utf-8'))
                    print(f"  SHA256 hash: {hash_obj.hexdigest()}")
                    
                    return jsonify({'success': False, 'message': 'Invalid signature'}), 401
        else:
            print(f"⚠ No signature provided in X-SIGNATURE header")
            # Default to TRUAXIS if no signature
            config_type = 'TRUAXIS'
        
        print(f"\n📋 Using configuration: {config_type}")
        
        # Check if payload contains encrypted_data
        encrypted_data = webhook_data.get('encrypted_data')
        if encrypted_data and timestamp_header and request_id_header:
            print(f"\n🔓 Decrypting webhook payload using {config_type} configuration...")
            
            # Load secret key for the detected configuration
            secret_key = load_client_secret_key(config_type)
            if not secret_key:
                print(f"❌ Failed to load webhook secret key for {config_type}")
                return jsonify({'success': False, 'message': 'Configuration error'}), 500
            
            # Prepare AAD
            aad = {
                'timestamp': int(timestamp_header),
                'request_id': request_id_header
            }
            
            # Decrypt
            decrypted_data = decrypt_webhook_response(encrypted_data, secret_key, aad)
            
            if not decrypted_data:
                print(f"❌ Failed to decrypt webhook payload")
                return jsonify({'success': False, 'message': 'Decryption failed'}), 400
            
            print(f"✅ Decryption successful!")
            print(f"\n📦 Decrypted Payload:")
            print(json.dumps(decrypted_data, indent=2))
            
            # Extract responseBody (actual payment data)
            response_body = decrypted_data.get('responseBody', {})
            if not response_body:
                print(f"❌ No responseBody in decrypted data")
                return jsonify({'success': False, 'message': 'Invalid payload structure'}), 400
            
            # Use decrypted data as webhook_data
            webhook_data = response_body
            print(f"\n📦 Extracted Payment Data:")
            print(json.dumps(webhook_data, indent=2))
        else:
            print(f"\n📦 Plain Webhook Payload:")
            print(json.dumps(webhook_data, indent=2))
        
        # Extract payment details
        payment_status = webhook_data.get('paymentStatus')
        transaction_id = webhook_data.get('transactionId')
        payment_mode = webhook_data.get('paymentMode')
        card_type = webhook_data.get('cardType', '')
        card_masked = webhook_data.get('cardMasked', '')
        order_id = webhook_data.get('orderId')
        customer_name = webhook_data.get('customerName')
        customer_email = webhook_data.get('customerEmail')
        customer_phone = webhook_data.get('customerPhoneNumber')
        amount = webhook_data.get('amount')
        bank_ref_id = webhook_data.get('bankRefId', '')
        
        print(f"\n💳 Payment Details:")
        print(f"  Status: {payment_status}")
        print(f"  Transaction ID: {transaction_id}")
        print(f"  Order ID: {order_id}")
        print(f"  Amount: ₹{amount}")
        print(f"  Payment Mode: {payment_mode}")
        print(f"  Bank Ref: {bank_ref_id}")
        
        # Map VIYONAPAY status to our status
        if payment_status == 'SUCCESS':
            status = 'SUCCESS'
        elif payment_status == 'FAILED':
            status = 'FAILED'
        elif payment_status == 'PENDING':
            status = 'PENDING'
        else:
            status = 'INITIATED'
        
        # Update transaction in database
        conn = get_db_connection()
        if not conn:
            print(f"❌ Database connection failed")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Find transaction by order_id - check both VIYONAPAY and VIYONAPAY_BARRINGER
                cursor.execute("""
                    SELECT txn_id, merchant_id, status, net_amount, charge_amount, pg_partner
                    FROM payin_transactions
                    WHERE order_id = %s AND pg_partner IN ('VIYONAPAY', 'VIYONAPAY_BARRINGER')
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"❌ Transaction not found for order_id: {order_id}")
                    return jsonify({'success': False, 'message': 'Transaction not found'}), 404
                
                print(f"\n✓ Transaction found: {txn['txn_id']}")
                print(f"  Current status: {txn['status']}")
                print(f"  New status: {status}")
                
                # Check for duplicate callback (idempotency)
                if txn['status'] == status and status in ['SUCCESS', 'FAILED']:
                    print(f"⚠ Duplicate callback - transaction already {status}")
                    
                    # Still send success response
                    secret_key = load_client_secret_key(config_type)
                    if secret_key and timestamp_header and request_id_header:
                        aad = {
                            'timestamp': int(timestamp_header),
                            'request_id': request_id_header
                        }
                        
                        response_data = {
                            'response_status': 1,
                            'message': 'Callback already processed'
                        }
                        
                        encrypted_response = encrypt_webhook_acknowledgment(response_data, secret_key, aad)
                        
                        if encrypted_response:
                            return jsonify({
                                'response_status': 1,
                                'encrypted_data': encrypted_response
                            }), 200
                    
                    return jsonify({'success': True, 'message': 'Already processed'}), 200
                
                # Update transaction status
                if status == 'SUCCESS':
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, pg_txn_id = %s, bank_ref_no = %s,
                            payment_mode = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, transaction_id, bank_ref_id, payment_mode, txn['txn_id']))
                    
                    # Check if wallet already credited (idempotency)
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                    """, (txn['txn_id'],))
                    
                    wallet_already_credited = cursor.fetchone()['count'] > 0
                    
                    if not wallet_already_credited:
                        # Credit merchant unsettled wallet
                        from wallet_service import wallet_service as wallet_svc
                        
                        wallet_result = wallet_svc.credit_unsettled_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=float(txn['net_amount']),
                            description=f"PayIn received (VIYONAPAY) - {order_id}",
                            reference_id=txn['txn_id']
                        )
                        
                        if wallet_result['success']:
                            print(f"✓ Merchant wallet credited: ₹{txn['net_amount']}")
                        else:
                            print(f"✗ Failed to credit merchant wallet: {wallet_result.get('message')}")
                        
                        # Credit admin unsettled wallet
                        admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                            admin_id='admin',
                            amount=float(txn['charge_amount']),
                            description=f"PayIn charge (VIYONAPAY) - {order_id}",
                            reference_id=txn['txn_id']
                        )
                        
                        if admin_wallet_result['success']:
                            print(f"✓ Admin wallet credited: ₹{txn['charge_amount']}")
                        else:
                            print(f"✗ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                    else:
                        print(f"⚠ Wallet already credited - skipping")
                    
                elif status == 'FAILED':
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, pg_txn_id = %s, bank_ref_no = %s,
                            payment_mode = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, transaction_id, bank_ref_id, payment_mode, txn['txn_id']))
                else:
                    # PENDING or other status
                    cursor.execute("""
                        UPDATE payin_transactions
                        SET status = %s, pg_txn_id = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (status, transaction_id, txn['txn_id']))
                
                conn.commit()
                
                print(f"✅ Transaction updated successfully")
                
                # Forward callback to merchant if configured
                print(f"\n{'='*60}")
                print(f"MERCHANT CALLBACK FORWARDING - VIYONAPAY")
                print(f"{'='*60}")
                
                try:
                    # Get callback URL from transaction
                    cursor.execute("""
                        SELECT callback_url FROM payin_transactions
                        WHERE txn_id = %s
                    """, (txn['txn_id'],))
                    
                    txn_callback = cursor.fetchone()
                    callback_url = None
                    
                    if txn_callback and txn_callback.get('callback_url'):
                        callback_url = txn_callback['callback_url'].strip()
                        if not callback_url:
                            callback_url = None
                    
                    print(f"Step 1: Transaction callback_url: {callback_url if callback_url else 'NOT SET'}")
                    
                    # If no callback URL in transaction, check merchant_callbacks table
                    if not callback_url:
                        print(f"Step 2: Checking merchant_callbacks table")
                        cursor.execute("""
                            SELECT payin_callback_url FROM merchant_callbacks
                            WHERE merchant_id = %s
                        """, (txn['merchant_id'],))
                        
                        merchant_callback = cursor.fetchone()
                        if merchant_callback and merchant_callback.get('payin_callback_url'):
                            callback_url = merchant_callback['payin_callback_url'].strip()
                            if not callback_url:
                                callback_url = None
                        
                        print(f"Step 2: Merchant payin_callback_url: {callback_url if callback_url else 'NOT SET'}")
                    
                    if callback_url:
                        # Prepare callback payload for merchant
                        merchant_callback_data = {
                            'txn_id': txn['txn_id'],
                            'order_id': order_id,
                            'status': status,
                            'amount': float(amount) if amount else 0.0,
                            'utr': bank_ref_id or '',
                            'pg_txn_id': transaction_id or '',
                            'payment_mode': payment_mode or 'UPI',
                            'pg_partner': 'VIYONAPAY',
                            'timestamp': webhook_data.get('timestamp', '')
                        }
                        
                        print(f"Forwarding VIYONAPAY callback to merchant: {callback_url}")
                        print(f"Callback data: {json.dumps(merchant_callback_data, indent=2)}")
                        
                        try:
                            import requests
                            
                            callback_response = requests.post(
                                callback_url,
                                json=merchant_callback_data,
                                headers={'Content-Type': 'application/json'},
                                timeout=10
                            )
                            
                            print(f"Merchant callback response: {callback_response.status_code}")
                            
                            # Log callback attempt
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                callback_url,
                                json.dumps(merchant_callback_data),
                                callback_response.status_code,
                                callback_response.text[:1000]
                            ))
                            conn.commit()
                            
                            print(f"✓ Merchant callback sent successfully")
                            
                        except Exception as e:
                            print(f"ERROR: Failed to send merchant callback: {e}")
                            
                            # Log failed callback attempt
                            cursor.execute("""
                                INSERT INTO callback_logs 
                                (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """, (
                                txn['merchant_id'],
                                txn['txn_id'],
                                callback_url,
                                json.dumps(merchant_callback_data),
                                0,
                                str(e)[:1000]
                            ))
                            conn.commit()
                    else:
                        print("No merchant callback URL configured")
                        
                except Exception as e:
                    print(f"ERROR in merchant callback forwarding: {e}")
                    import traceback
                    traceback.print_exc()
                
                print(f"{'='*60}\n")
                
                # Prepare encrypted response
                secret_key = load_client_secret_key(config_type)
                
                if secret_key and timestamp_header and request_id_header:
                    # Prepare AAD for response encryption
                    aad = {
                        'timestamp': int(timestamp_header),
                        'request_id': request_id_header
                    }
                    
                    # Prepare response data
                    response_data = {
                        'response_status': 1,
                        'message': 'Callback processed successfully'
                    }
                    
                    # Encrypt response
                    encrypted_response = encrypt_webhook_acknowledgment(response_data, secret_key, aad)
                    
                    if encrypted_response:
                        return jsonify({
                            'response_status': 1,
                            'encrypted_data': encrypted_response
                        }), 200
                
                # Fallback: plain response
                return jsonify({
                    'success': True,
                    'message': 'Callback processed successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Callback processing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
