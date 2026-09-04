#!/usr/bin/env python3
"""
Get merchant credentials for testing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def get_merchant_credentials(merchant_id="9000000001"):
    """Get merchant credentials for API testing"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT merchant_id, full_name, email, api_key, module_secret, 
                       aes_key, aes_iv, is_active
                FROM merchants
                WHERE merchant_id = %s
            """, (merchant_id,))
            
            merchant = cursor.fetchone()
            
            if merchant:
                print(f"✅ Merchant Found: {merchant['merchant_id']}")
                print(f"   Name: {merchant['full_name']}")
                print(f"   Email: {merchant['email']}")
                print(f"   API Key: {merchant['api_key']}")
                print(f"   Module Secret: {merchant['module_secret']}")
                print(f"   AES Key: {merchant['aes_key']}")
                print(f"   AES IV: {merchant['aes_iv']}")
                print(f"   Active: {merchant['is_active']}")
                return merchant
            else:
                print(f"❌ Merchant {merchant_id} not found")
                return None
                
    finally:
        conn.close()

if __name__ == "__main__":
    merchant_id = sys.argv[1] if len(sys.argv) > 1 else "9000000001"
    get_merchant_credentials(merchant_id)
