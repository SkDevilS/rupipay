"""
Check PayTouch Callback Data
Analyze what data PayTouch actually sends in callbacks
"""

from database import get_db_connection
import json

def check_paytouch_callbacks():
    """Check recent PayTouch callback data to see what fields are sent"""
    
    print("=" * 80)
    print("PayTouch Callback Data Analysis")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent PayTouch transactions with their callback logs
            print("\n1. Recent PayTouch Transactions")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.reference_id,
                    pt.status,
                    pt.utr,
                    pt.bank_ref_no,
                    pt.pg_txn_id,
                    pt.created_at
                FROM payout_transactions pt
                WHERE pt.pg_partner = 'PayTouch'
                ORDER BY pt.created_at DESC
                LIMIT 10
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("No PayTouch transactions found")
                return
            
            for txn in transactions:
                print(f"\nTransaction: {txn['txn_id']}")
                print(f"  Reference: {txn['reference_id']}")
                print(f"  Status: {txn['status']}")
                print(f"  UTR: {txn['utr']}")
                print(f"  Bank Ref: {txn['bank_ref_no']}")
                print(f"  PG TXN ID: {txn['pg_txn_id']}")
                print(f"  Created: {txn['created_at']}")
            
            # Check callback logs
            print("\n\n2. PayTouch Callback Logs")
            print("-" * 80)
            
            # First check if callback_logs table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_name = 'callback_logs'
            """)
            
            table_exists = cursor.fetchone()['count'] > 0
            
            if not table_exists:
                print("⚠️  callback_logs table does not exist")
                print("   Callbacks are not being logged to database")
                print("\n   To create the table, run:")
                print("""
                CREATE TABLE callback_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50),
                    txn_id VARCHAR(100),
                    callback_url TEXT,
                    request_data TEXT,
                    response_code INT,
                    response_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                
                # Check backend logs instead
                print("\n\n3. Check Backend Logs for Callback Data")
                print("-" * 80)
                print("Run this command on your server:")
                print("  grep -A 20 'PayTouch Payout Callback Received' /var/www/moneyone/logs/backend.log | tail -100")
                
            else:
                cursor.execute("""
                    SELECT 
                        cl.id,
                        cl.txn_id,
                        cl.request_data,
                        cl.response_code,
                        cl.created_at
                    FROM callback_logs cl
                    INNER JOIN payout_transactions pt ON cl.txn_id = pt.txn_id
                    WHERE pt.pg_partner = 'PayTouch'
                    ORDER BY cl.created_at DESC
                    LIMIT 5
                """)
                
                callbacks = cursor.fetchall()
                
                if not callbacks:
                    print("No PayTouch callback logs found")
                    print("\nPossible reasons:")
                    print("1. PayTouch hasn't sent any callbacks yet")
                    print("2. Callback URL is not configured correctly")
                    print("3. Callbacks are failing before being logged")
                else:
                    for cb in callbacks:
                        print(f"\nCallback #{cb['id']} - {cb['created_at']}")
                        print(f"  Transaction: {cb['txn_id']}")
                        print(f"  Response Code: {cb['response_code']}")
                        
                        if cb['request_data']:
                            try:
                                request_json = json.loads(cb['request_data'])
                                print(f"  Request Data:")
                                print(json.dumps(request_json, indent=4))
                                
                                # Analyze fields
                                print(f"\n  Available Fields: {list(request_json.keys())}")
                                
                                # Check for UTR-like fields
                                utr_fields = []
                                for key in request_json.keys():
                                    if any(term in key.lower() for term in ['utr', 'ref', 'bank', 'rrn', 'reference']):
                                        utr_fields.append(f"{key}: {request_json[key]}")
                                
                                if utr_fields:
                                    print(f"\n  Potential UTR Fields:")
                                    for field in utr_fields:
                                        print(f"    - {field}")
                                else:
                                    print(f"\n  ⚠️  No UTR-like fields found")
                                    
                            except json.JSONDecodeError:
                                print(f"  Request Data (raw): {cb['request_data'][:200]}")
            
            # Check backend application logs
            print("\n\n4. Backend Log Analysis")
            print("-" * 80)
            print("To see what PayTouch is actually sending, check backend logs:")
            print()
            print("On your server, run:")
            print("  tail -1000 /var/www/moneyone/logs/backend.log | grep -A 30 'PayTouch Payout Callback Received'")
            print()
            print("Look for lines like:")
            print("  'Callback Data: {...}'")
            print("  'UTR: ...'")
            print()
            print("This will show the exact JSON PayTouch sends")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    check_paytouch_callbacks()
