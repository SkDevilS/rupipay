"""
Check RMS_JSS transaction callback URL
"""
import sys
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from database import get_db_connection

def check_callback_url():
    """Check callback URL for recent RMS_JSS transaction"""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get most recent RMS_JSS transaction
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    callback_url,
                    created_at,
                    status
                FROM payin_transactions
                WHERE pg_partner = 'RMS_JSS'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("No RMS_JSS transactions found")
                return
            
            print(f"\n{'='*80}")
            print(f"Recent RMS_JSS Transactions")
            print(f"{'='*80}\n")
            
            for txn in transactions:
                print(f"Transaction ID: {txn['txn_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Merchant ID: {txn['merchant_id']}")
                print(f"Callback URL: {txn['callback_url'] if txn['callback_url'] else 'NOT SET'}")
                print(f"Status: {txn['status']}")
                print(f"Created: {txn['created_at']}")
                print(f"-" * 80)
            
            # Check merchant_callbacks table
            print(f"\n{'='*80}")
            print(f"Checking merchant_callbacks table")
            print(f"{'='*80}\n")
            
            for txn in transactions:
                cursor.execute("""
                    SELECT payin_callback_url
                    FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (txn['merchant_id'],))
                
                merchant_callback = cursor.fetchone()
                
                print(f"Merchant ID: {txn['merchant_id']}")
                if merchant_callback:
                    print(f"  Payin Callback URL: {merchant_callback['payin_callback_url'] if merchant_callback.get('payin_callback_url') else 'NOT SET'}")
                else:
                    print(f"  No entry in merchant_callbacks table")
                print()
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_callback_url()
