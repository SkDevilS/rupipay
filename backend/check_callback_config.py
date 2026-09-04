"""
Diagnostic script to check callback configuration for transactions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_callback_config(order_id=None, merchant_id=None):
    """Check callback configuration for a transaction or merchant"""
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            if order_id:
                print("=" * 80)
                print(f"Checking callback config for Order ID: {order_id}")
                print("=" * 80)
                
                # Get transaction details
                cursor.execute("""
                    SELECT 
                        txn_id, 
                        order_id, 
                        merchant_id, 
                        status, 
                        callback_url,
                        pg_partner,
                        amount,
                        created_at
                    FROM payin_transactions
                    WHERE order_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print("ERROR: Transaction not found")
                    return
                
                print("\nTransaction Details:")
                print(f"  TXN ID: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Merchant ID: {txn['merchant_id']}")
                print(f"  Status: {txn['status']}")
                print(f"  PG Partner: {txn['pg_partner']}")
                print(f"  Amount: {txn['amount']}")
                print(f"  Created: {txn['created_at']}")
                print(f"\n  Callback URL in Transaction: '{txn['callback_url']}'")
                print(f"  Is NULL: {txn['callback_url'] is None}")
                print(f"  Is Empty String: {txn['callback_url'] == ''}")
                print(f"  Length: {len(txn['callback_url']) if txn['callback_url'] else 0}")
                
                merchant_id = txn['merchant_id']
            
            if merchant_id:
                print("\n" + "=" * 80)
                print(f"Checking merchant_callbacks table for Merchant ID: {merchant_id}")
                print("=" * 80)
                
                cursor.execute("""
                    SELECT 
                        callback_url,
                        is_active,
                        created_at,
                        updated_at
                    FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                merchant_callback = cursor.fetchone()
                
                if merchant_callback:
                    print("\nMerchant Callbacks Table:")
                    print(f"  Callback URL: '{merchant_callback['callback_url']}'")
                    print(f"  Is Active: {merchant_callback['is_active']}")
                    print(f"  Is NULL: {merchant_callback['callback_url'] is None}")
                    print(f"  Is Empty String: {merchant_callback['callback_url'] == ''}")
                    print(f"  Created: {merchant_callback['created_at']}")
                    print(f"  Updated: {merchant_callback['updated_at']}")
                else:
                    print("\n  No entry in merchant_callbacks table")
                
                # Check recent transactions for this merchant
                print("\n" + "=" * 80)
                print(f"Recent transactions for Merchant ID: {merchant_id}")
                print("=" * 80)
                
                cursor.execute("""
                    SELECT 
                        txn_id,
                        order_id,
                        status,
                        callback_url,
                        created_at
                    FROM payin_transactions
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (merchant_id,))
                
                transactions = cursor.fetchall()
                
                if transactions:
                    print(f"\nFound {len(transactions)} recent transactions:")
                    for i, t in enumerate(transactions, 1):
                        print(f"\n  {i}. Order ID: {t['order_id']}")
                        print(f"     Status: {t['status']}")
                        print(f"     Callback URL: '{t['callback_url']}'")
                        print(f"     Created: {t['created_at']}")
                else:
                    print("\n  No transactions found")
                
                # Check callback logs
                print("\n" + "=" * 80)
                print(f"Recent callback logs for Merchant ID: {merchant_id}")
                print("=" * 80)
                
                cursor.execute("""
                    SELECT 
                        txn_id,
                        callback_url,
                        response_code,
                        LEFT(response_data, 100) as response_preview,
                        created_at
                    FROM callback_logs
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (merchant_id,))
                
                logs = cursor.fetchall()
                
                if logs:
                    print(f"\nFound {len(logs)} recent callback logs:")
                    for i, log in enumerate(logs, 1):
                        print(f"\n  {i}. TXN ID: {log['txn_id']}")
                        print(f"     Callback URL: {log['callback_url']}")
                        print(f"     Response Code: {log['response_code']}")
                        print(f"     Response Preview: {log['response_preview']}")
                        print(f"     Created: {log['created_at']}")
                else:
                    print("\n  No callback logs found")
            
            print("\n" + "=" * 80)
            print("Diagnostic Summary:")
            print("=" * 80)
            
            if order_id:
                txn_url = txn['callback_url']
                if txn_url and txn_url.strip():
                    print(f"✓ Transaction has callback URL: {txn_url}")
                else:
                    print("✗ Transaction has NO callback URL (NULL or empty)")
            
            if merchant_id and merchant_callback:
                merch_url = merchant_callback['callback_url']
                if merch_url and merch_url.strip() and merchant_callback['is_active']:
                    print(f"✓ Merchant has active callback URL: {merch_url}")
                elif merch_url and merch_url.strip():
                    print(f"⚠ Merchant has callback URL but is_active=FALSE: {merch_url}")
                else:
                    print("✗ Merchant has NO callback URL in merchant_callbacks table")
            elif merchant_id:
                print("✗ Merchant has NO entry in merchant_callbacks table")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check callback configuration')
    parser.add_argument('--order-id', help='Order ID to check')
    parser.add_argument('--merchant-id', help='Merchant ID to check')
    
    args = parser.parse_args()
    
    if not args.order_id and not args.merchant_id:
        print("ERROR: Either --order-id or --merchant-id must be provided")
        parser.print_help()
        sys.exit(1)
    
    check_callback_config(order_id=args.order_id, merchant_id=args.merchant_id)
