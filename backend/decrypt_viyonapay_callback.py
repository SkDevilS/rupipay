#!/usr/bin/env python3
"""
Decrypt and display ViyonaPay webhook callback response
This script decrypts the encrypted webhook data to show the actual response structure
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

def load_client_secret_key():
    """Load ViyonaPay client secret key"""
    secret_key = os.getenv('VIYONAPAY_CLIENT_SECRET')
    if not secret_key:
        raise ValueError("VIYONAPAY_CLIENT_SECRET not found in environment")
    return secret_key

def decrypt_webhook_response(encrypted_b64, secret_key, aad_dict):
    """
    Decrypt ViyonaPay webhook response
    
    Args:
        encrypted_b64: Base64 encoded encrypted data
        secret_key: Client secret key (hex string)
        aad_dict: Additional authenticated data dictionary
    
    Returns:
        Decrypted JSON data
    """
    try:
        # Decode base64
        encrypted_data = base64.b64decode(encrypted_b64)
        
        # Extract nonce (first 12 bytes) and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # Convert hex secret key to bytes
        key_bytes = bytes.fromhex(secret_key)
        
        # Create AESGCM cipher
        aesgcm = AESGCM(key_bytes)
        
        # Prepare AAD
        aad_json = json.dumps(aad_dict, separators=(',', ':'))
        aad_bytes = aad_json.encode('utf-8')
        
        # Decrypt
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        decrypted_text = decrypted_bytes.decode('utf-8')
        
        # Parse JSON
        return json.loads(decrypted_text)
        
    except Exception as e:
        print(f"❌ Decryption error: {e}")
        import traceback
        traceback.print_exc()
        return None

def decrypt_and_display_callback():
    """Decrypt and display the most recent ViyonaPay callback"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        # Load secret key
        try:
            secret_key = load_client_secret_key()
            print("✅ Loaded ViyonaPay client secret key")
        except Exception as e:
            print(f"❌ Failed to load secret key: {e}")
            secret_key = None
        
        with conn.cursor() as cursor:
            print("\n" + "="*80)
            print("  SEARCHING FOR ENCRYPTED WEBHOOK DATA")
            print("="*80)
            
            # Look for encrypted webhook callbacks
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE (request_data LIKE '%encryptedData%' 
                   OR request_data LIKE '%signature%')
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            callbacks = cursor.fetchall()
            
            if not callbacks:
                print("\n❌ No encrypted webhook callbacks found")
                print("\nTrying to find any ViyonaPay related callbacks...")
                
                cursor.execute("""
                    SELECT 
                        id,
                        merchant_id,
                        request_data,
                        response_code,
                        created_at
                    FROM callback_logs
                    WHERE request_data LIKE '%VIYONAPAY%'
                       OR request_data LIKE '%viyonapay%'
                    ORDER BY created_at DESC
                    LIMIT 3
                """)
                
                callbacks = cursor.fetchall()
            
            if not callbacks:
                print("❌ No ViyonaPay callbacks found at all")
                return
            
            print(f"\n✅ Found {len(callbacks)} callback(s)\n")
            
            for idx, callback in enumerate(callbacks, 1):
                print(f"\n{'='*80}")
                print(f"  CALLBACK #{idx}")
                print(f"{'='*80}")
                print(f"Callback ID: {callback['id']}")
                print(f"Merchant ID: {callback['merchant_id']}")
                print(f"Response Code: {callback.get('response_code', 'N/A')}")
                print(f"Created: {callback['created_at']}")
                
                print("\n" + "-"*80)
                print("  RAW REQUEST DATA")
                print("-"*80)
                
                try:
                    request_data = json.loads(callback['request_data'])
                    print(json.dumps(request_data, indent=2))
                    
                    # Check if it's encrypted
                    if 'encryptedData' in request_data and 'aad' in request_data:
                        print("\n" + "-"*80)
                        print("  ENCRYPTED WEBHOOK DETECTED - ATTEMPTING DECRYPTION")
                        print("-"*80)
                        
                        if secret_key:
                            encrypted_data = request_data['encryptedData']
                            aad = request_data['aad']
                            
                            print(f"\nEncrypted Data Length: {len(encrypted_data)} chars")
                            print(f"AAD: {json.dumps(aad, indent=2)}")
                            
                            # Decrypt
                            decrypted = decrypt_webhook_response(encrypted_data, secret_key, aad)
                            
                            if decrypted:
                                print("\n" + "="*80)
                                print("  ✅ DECRYPTED RESPONSE DATA")
                                print("="*80)
                                print(json.dumps(decrypted, indent=2))
                                
                                # Show field mapping
                                print("\n" + "="*80)
                                print("  FIELD MAPPING FOR THIS RESPONSE")
                                print("="*80)
                                
                                print("\nAvailable fields in decrypted response:")
                                for key in decrypted.keys():
                                    value = decrypted[key]
                                    print(f"  • {key}: {value} (type: {type(value).__name__})")
                                
                                # Suggest mapping
                                print("\n" + "-"*80)
                                print("  SUGGESTED FIELD MAPPING")
                                print("-"*80)
                                print("""
# Map these ViyonaPay fields to our database:

txn_id (ours)        → Keep our original transaction ID
order_id             → {order_id_field}
pg_txn_id            → {payment_id_field}
bank_ref_no          → {bank_ref_field}
utr                  → {utr_field}
status               → {status_field}
amount               → {amount_field}
payment_mode         → {payment_method_field}

Replace {field_name} with actual field names from the decrypted response above.
                                """)
                            else:
                                print("\n❌ Failed to decrypt webhook data")
                        else:
                            print("\n⚠️  Cannot decrypt - secret key not available")
                    else:
                        print("\n✓ This appears to be plain (non-encrypted) callback data")
                        
                except json.JSONDecodeError:
                    print(callback['request_data'])
                    print("\n⚠️  Not valid JSON")
                except Exception as e:
                    print(f"\n❌ Error processing callback: {e}")
                    import traceback
                    traceback.print_exc()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  ViyonaPay Webhook Decryption Tool")
    print("  Decrypt and display callback response for mapping")
    print("="*80)
    decrypt_and_display_callback()
    print("\n" + "="*80)
