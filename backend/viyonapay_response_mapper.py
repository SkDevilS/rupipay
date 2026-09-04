#!/usr/bin/env python3
"""
ViyonaPay Response Field Mapper
This script analyzes the callback response and generates the exact mapping code
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def load_client_secret_key():
    """Load ViyonaPay client secret key"""
    secret_key = os.getenv('VIYONAPAY_CLIENT_SECRET')
    if not secret_key:
        print("⚠️  VIYONAPAY_CLIENT_SECRET not found in environment")
        return None
    return secret_key

def decrypt_webhook(encrypted_b64, secret_key, aad_dict):
    """Decrypt ViyonaPay webhook response"""
    try:
        encrypted_data = base64.b64decode(encrypted_b64)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        key_bytes = bytes.fromhex(secret_key)
        aesgcm = AESGCM(key_bytes)
        aad_json = json.dumps(aad_dict, separators=(',', ':'))
        aad_bytes = aad_json.encode('utf-8')
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        decrypted_text = decrypted_bytes.decode('utf-8')
        return json.loads(decrypted_text)
    except Exception as e:
        print(f"❌ Decryption failed: {e}")
        return None

def generate_mapping_code(response_data):
    """Generate Python code for field mapping"""
    
    print("\n" + "="*80)
    print("  GENERATED MAPPING CODE")
    print("="*80)
    
    # Common field name variations
    field_mappings = {
        'order_id': ['orderId', 'order_id', 'merchantOrderId', 'merchant_order_id', 'orderReference'],
        'pg_txn_id': ['transactionId', 'transaction_id', 'paymentId', 'payment_id', 'txnId', 'viyonaPayTxnId'],
        'bank_ref_no': ['bankRefNo', 'bank_ref_no', 'rrn', 'RRN', 'bankReference', 'bank_reference'],
        'utr': ['utr', 'UTR', 'referenceNumber', 'reference_number', 'bankUTR', 'utrNumber'],
        'status': ['status', 'paymentStatus', 'payment_status', 'transactionStatus', 'transaction_status'],
        'amount': ['amount', 'transactionAmount', 'transaction_amount', 'paymentAmount', 'payment_amount'],
        'payment_mode': ['paymentMode', 'payment_mode', 'paymentMethod', 'payment_method', 'mode']
    }
    
    found_mappings = {}
    
    # Search for fields in response
    for our_field, possible_names in field_mappings.items():
        for name in possible_names:
            if name in response_data:
                found_mappings[our_field] = name
                break
    
    print("\n# Add this to your viyonapay_callback_routes.py in the callback handler:\n")
    print("# After decrypting the webhook response:\n")
    print("decrypted_data = decrypt_webhook_response(encrypted_data, secret_key, aad)")
    print("if decrypted_data:")
    print("    # Extract fields from ViyonaPay response")
    
    if found_mappings:
        for our_field, viyona_field in found_mappings.items():
            print(f"    {our_field} = decrypted_data.get('{viyona_field}')")
    else:
        print("    # Manual mapping required - fields not auto-detected")
        print("    # Check the response structure below")
    
    print("\n    # Update transaction in database")
    print("    cursor.execute('''")
    print("        UPDATE payin_transactions")
    print("        SET ")
    
    if found_mappings:
        updates = []
        if 'status' in found_mappings:
            updates.append("status = %s")
        if 'pg_txn_id' in found_mappings:
            updates.append("pg_txn_id = %s")
        if 'bank_ref_no' in found_mappings:
            updates.append("bank_ref_no = %s")
        if 'utr' in found_mappings:
            updates.append("utr = %s")
        if 'payment_mode' in found_mappings:
            updates.append("payment_mode = %s")
        
        print("            " + ",\n            ".join(updates) + ",")
        print("            updated_at = NOW()")
        print("        WHERE txn_id = %s")
        print("    ''', (")
        
        params = []
        if 'status' in found_mappings:
            params.append("status")
        if 'pg_txn_id' in found_mappings:
            params.append("pg_txn_id")
        if 'bank_ref_no' in found_mappings:
            params.append("bank_ref_no")
        if 'utr' in found_mappings:
            params.append("utr")
        if 'payment_mode' in found_mappings:
            params.append("payment_mode")
        params.append("txn_id")
        
        print("        " + ", ".join(params))
        print("    ))")
    else:
        print("            status = %s,")
        print("            pg_txn_id = %s,")
        print("            bank_ref_no = %s,")
        print("            utr = %s,")
        print("            updated_at = NOW()")
        print("        WHERE txn_id = %s")
        print("    ''', (status, pg_txn_id, bank_ref_no, utr, txn_id))")
    
    print("\n" + "="*80)
    print("  FIELD MAPPING SUMMARY")
    print("="*80)
    
    if found_mappings:
        print("\n✅ Auto-detected field mappings:\n")
        for our_field, viyona_field in found_mappings.items():
            print(f"  {our_field:20} ← {viyona_field}")
    else:
        print("\n⚠️  No fields auto-detected. Manual mapping required.")
    
    print("\n" + "="*80)
    print("  ALL AVAILABLE FIELDS IN RESPONSE")
    print("="*80)
    print("\nYou can map any of these fields:\n")
    
    for key, value in response_data.items():
        value_str = str(value)[:50]
        print(f"  • {key:30} = {value_str}")

def analyze_callback():
    """Analyze the most recent ViyonaPay callback and generate mapping"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        secret_key = load_client_secret_key()
        
        with conn.cursor() as cursor:
            print("\n" + "="*80)
            print("  ANALYZING VIYONAPAY CALLBACK RESPONSE")
            print("="*80)
            
            # Get the most recent callback
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    request_data,
                    created_at
                FROM callback_logs
                WHERE request_data LIKE '%encryptedData%'
                   OR request_data LIKE '%VIYONAPAY%'
                   OR request_data LIKE '%viyonapay%'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            callback = cursor.fetchone()
            
            if not callback:
                print("\n❌ No ViyonaPay callbacks found")
                print("\nPlease complete a transaction first, then run this script again.")
                return
            
            print(f"\n✅ Found callback from: {callback['created_at']}")
            print(f"   Callback ID: {callback['id']}")
            print(f"   Merchant ID: {callback['merchant_id']}")
            
            try:
                request_data = json.loads(callback['request_data'])
                
                # Check if encrypted
                if 'encryptedData' in request_data and 'aad' in request_data:
                    print("\n📦 Encrypted webhook detected")
                    
                    if not secret_key:
                        print("❌ Cannot decrypt - VIYONAPAY_CLIENT_SECRET not set")
                        print("\nRaw encrypted data:")
                        print(json.dumps(request_data, indent=2))
                        return
                    
                    print("🔓 Decrypting...")
                    
                    decrypted = decrypt_webhook(
                        request_data['encryptedData'],
                        secret_key,
                        request_data['aad']
                    )
                    
                    if decrypted:
                        print("✅ Decryption successful!\n")
                        print("="*80)
                        print("  DECRYPTED RESPONSE DATA")
                        print("="*80)
                        print(json.dumps(decrypted, indent=2))
                        
                        # Generate mapping code
                        generate_mapping_code(decrypted)
                    else:
                        print("❌ Decryption failed")
                else:
                    print("\n📄 Plain (non-encrypted) callback data")
                    print(json.dumps(request_data, indent=2))
                    
                    # Generate mapping code for plain data
                    generate_mapping_code(request_data)
                    
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                print(callback['request_data'])
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  ViyonaPay Response Field Mapper")
    print("  Automatic field mapping code generator")
    print("="*80)
    analyze_callback()
    print("\n" + "="*80)
    print("\nNext steps:")
    print("1. Copy the generated mapping code above")
    print("2. Update backend/viyonapay_callback_routes.py")
    print("3. Deploy the changes")
    print("="*80 + "\n")
