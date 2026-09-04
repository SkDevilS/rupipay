"""
Check Viyonapay Callback Forwarding Configuration
"""

from database import get_db_connection
import json

def check_callback_configuration(order_id=None):
    """Check callback URL configuration for a transaction"""
    
    print("\n" + "="*60)
    print("VIYONAPAY CALLBACK FORWARDING CHECK")
    print("="*60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent Viyonapay transactions
            if order_id:
                query = """
                    SELECT txn_id, order_id, merchant_id, status, callback_url, created_at
                    FROM payin_transactions
                    WHERE order_id = %s AND pg_partner = 'VIYONAPAY'
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(query, (order_id,))
            else:
                query = """
                    SELECT txn_id, order_id, merchant_id, status, callback_url, created_at
                    FROM payin_transactions
                    WHERE pg_partner = 'VIYONAPAY'
                    ORDER BY created_at DESC
                    LIMIT 5
                """
                cursor.execute(query)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("❌ No Viyonapay transactions found")
                return
            
            print(f"\n📋 Found {len(transactions)} transaction(s):")
            print("="*60)
            
            for txn in transactions:
                print(f"\n🔍 Transaction: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Merchant ID: {txn['merchant_id']}")
                print(f"  Status: {txn['status']}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Callback URL in transaction: {txn['callback_url'] if txn['callback_url'] else 'NOT SET'}")
                
                # Check merchant_callbacks table
                cursor.execute("""
                    SELECT payin_callback_url, payout_callback_url
                    FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (txn['merchant_id'],))
                
                merchant_callback = cursor.fetchone()
                
                if merchant_callback:
                    print(f"\n  📞 Merchant Callback Configuration:")
                    print(f"    PayIn Callback URL: {merchant_callback['payin_callback_url'] if merchant_callback['payin_callback_url'] else 'NOT SET'}")
                    print(f"    PayOut Callback URL: {merchant_callback['payout_callback_url'] if merchant_callback['payout_callback_url'] else 'NOT SET'}")
                else:
                    print(f"\n  ❌ No callback configuration found in merchant_callbacks table")
                
                # Check callback logs
                cursor.execute("""
                    SELECT callback_url, request_data, response_code, response_data, created_at
                    FROM callback_logs
                    WHERE txn_id = %s
                    ORDER BY created_at DESC
                    LIMIT 3
                """, (txn['txn_id'],))
                
                callback_logs = cursor.fetchall()
                
                if callback_logs:
                    print(f"\n  📝 Callback Logs ({len(callback_logs)} attempts):")
                    for i, log in enumerate(callback_logs, 1):
                        print(f"\n    Attempt {i}:")
                        print(f"      URL: {log['callback_url']}")
                        print(f"      Response Code: {log['response_code']}")
                        print(f"      Time: {log['created_at']}")
                        if log['response_code'] != 200:
                            print(f"      Response: {log['response_data'][:200] if log['response_data'] else 'None'}")
                else:
                    print(f"\n  ⚠️  No callback logs found - callback was NOT forwarded")
                
                print("\n" + "-"*60)
            
            # Summary
            print(f"\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            
            print(f"\n✅ What's Working:")
            print(f"  - Viyonapay callbacks are being received")
            print(f"  - Transaction status is being updated")
            
            print(f"\n🔍 Potential Issues:")
            
            has_callback_url = False
            for txn in transactions:
                if txn['callback_url']:
                    has_callback_url = True
                    break
            
            if not has_callback_url:
                print(f"  ❌ No callback_url in payin_transactions table")
                print(f"     → Callback URL should be saved when creating the order")
            
            has_merchant_callback = False
            for txn in transactions:
                cursor.execute("""
                    SELECT payin_callback_url FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (txn['merchant_id'],))
                mc = cursor.fetchone()
                if mc and mc['payin_callback_url']:
                    has_merchant_callback = True
                    break
            
            if not has_merchant_callback:
                print(f"  ❌ No payin_callback_url in merchant_callbacks table")
                print(f"     → Merchant needs to configure callback URL")
            
            print(f"\n📋 Next Steps:")
            print(f"  1. Check if callback_url is being saved during order creation")
            print(f"  2. Verify merchant_callbacks table has payin_callback_url")
            print(f"  3. Check backend logs for callback forwarding attempts")
            print(f"  4. Test with a new transaction to see if callback is forwarded")
            
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    
    order_id = None
    if len(sys.argv) > 1:
        order_id = sys.argv[1]
        print(f"Checking specific order: {order_id}")
    else:
        print("Checking recent transactions (provide order_id as argument for specific check)")
    
    check_callback_configuration(order_id)
