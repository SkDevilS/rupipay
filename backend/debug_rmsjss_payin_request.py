"""
Debug script to check what data merchant is sending in RMS_JSS payin request
Run this to see the actual field names in the last RMS_JSS transaction
"""

from database import get_db_connection
import json

def check_last_rmsjss_request():
    """Check the last RMS_JSS payin request to see what was sent"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            # Get the most recent RMS_JSS transaction
            cursor.execute("""
                SELECT txn_id, order_id, merchant_id, callback_url, created_at
                FROM payin_transactions
                WHERE pg_partner = 'RMS_JSS'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            txn = cursor.fetchone()
            
            if not txn:
                print("❌ No RMS_JSS transactions found")
                return
            
            print("=" * 80)
            print("LAST RMS_JSS PAYIN TRANSACTION")
            print("=" * 80)
            print(f"Transaction ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Merchant ID: {txn['merchant_id']}")
            print(f"Callback URL in DB: {txn['callback_url'] if txn['callback_url'] else 'NOT SET'}")
            print(f"Created: {txn['created_at']}")
            print()
            
            # Check if there are any logs that might show the original request
            print("=" * 80)
            print("INSTRUCTIONS TO DEBUG")
            print("=" * 80)
            print("1. The merchant sends encrypted data to /api/payin/order/create")
            print("2. The data is decrypted and passed as 'order_data' to rmsjss_service")
            print("3. We added DEBUG logging in rmsjss_service.py to print the full order_data")
            print("4. Ask the merchant to make a NEW payin request")
            print("5. Check the backend logs with:")
            print("   sudo journalctl -u backend -f | grep -A 50 'DEBUG: Full order_data'")
            print()
            print("This will show you ALL the fields the merchant is sending, including:")
            print("  - callback_url")
            print("  - callbackurl")
            print("  - callbackUrl")
            print("  - webhook_url")
            print("  - etc.")
            print()
            print("Once you see the actual field name, the code will extract it correctly.")
            print("=" * 80)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    check_last_rmsjss_request()
