"""
Complete PayTouch UTR Fix
1. Check what PayTouch sends in callbacks
2. Check database for missing UTRs
3. Fetch UTR from PayTouch API for transactions that don't have it
4. Update database
"""

from database import get_db_connection
from paytouch_service import paytouch_service
import json

def fix_paytouch_utr():
    """Complete fix for PayTouch UTR issues"""
    
    print("=" * 80)
    print("PayTouch UTR Complete Fix")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Step 1: Find PayTouch transactions without UTR
            print("\n1. Finding PayTouch Transactions Without UTR")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    pg_txn_id,
                    status,
                    utr,
                    bank_ref_no,
                    created_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                  AND status = 'SUCCESS'
                  AND (utr IS NULL OR utr = '')
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            missing_utr_txns = cursor.fetchall()
            
            if not missing_utr_txns:
                print("✅ All SUCCESS PayTouch transactions have UTR")
            else:
                print(f"Found {len(missing_utr_txns)} SUCCESS transactions without UTR:")
                for txn in missing_utr_txns:
                    print(f"  - {txn['txn_id']} ({txn['reference_id']}) - Created: {txn['created_at']}")
            
            # Step 2: Check what fields PayTouch actually returns
            print("\n\n2. Testing PayTouch API Response")
            print("-" * 80)
            
            if missing_utr_txns:
                test_txn = missing_utr_txns[0]
                print(f"Testing with transaction: {test_txn['txn_id']}")
                print(f"  Reference ID: {test_txn['reference_id']}")
                print(f"  PG TXN ID: {test_txn['pg_txn_id']}")
                
                # Call PayTouch API
                result = paytouch_service.check_payout_status(
                    transaction_id=test_txn['pg_txn_id'],
                    external_ref=test_txn['reference_id']
                )
                
                print(f"\nPayTouch API Response:")
                print(json.dumps(result, indent=2))
                
                if result.get('success'):
                    print(f"\n✓ API call successful")
                    print(f"  Status: {result.get('status')}")
                    print(f"  UTR: {result.get('utr')}")
                    
                    if not result.get('utr'):
                        print(f"\n⚠️  UTR is NULL in PayTouch response!")
                        print(f"  This means PayTouch is not providing UTR")
                        print(f"  Possible reasons:")
                        print(f"    1. PayTouch doesn't provide UTR in their API")
                        print(f"    2. UTR is in a different field (check raw response above)")
                        print(f"    3. UTR is only available in callbacks, not status API")
                else:
                    print(f"\n✗ API call failed: {result.get('message')}")
            
            # Step 3: Fix transactions by fetching UTR from PayTouch
            print("\n\n3. Fetching and Updating UTR for Transactions")
            print("-" * 80)
            
            if missing_utr_txns:
                print(f"Attempting to fetch UTR for {len(missing_utr_txns)} transactions...")
                
                updated_count = 0
                failed_count = 0
                no_utr_count = 0
                
                for txn in missing_utr_txns:
                    print(f"\nProcessing {txn['txn_id']}...")
                    
                    # Fetch status from PayTouch
                    result = paytouch_service.check_payout_status(
                        transaction_id=txn['pg_txn_id'],
                        external_ref=txn['reference_id']
                    )
                    
                    if result.get('success'):
                        utr = result.get('utr')
                        
                        if utr:
                            # Update database
                            cursor.execute("""
                                UPDATE payout_transactions
                                SET utr = %s, updated_at = NOW()
                                WHERE txn_id = %s
                            """, (utr, txn['txn_id']))
                            
                            conn.commit()
                            updated_count += 1
                            print(f"  ✅ Updated UTR: {utr}")
                        else:
                            no_utr_count += 1
                            print(f"  ⚠️  PayTouch didn't return UTR")
                    else:
                        failed_count += 1
                        print(f"  ✗ Failed to fetch status: {result.get('message')}")
                
                print(f"\n" + "=" * 80)
                print(f"Update Summary:")
                print(f"  Updated: {updated_count}")
                print(f"  No UTR from PayTouch: {no_utr_count}")
                print(f"  Failed: {failed_count}")
                print("=" * 80)
            
            # Step 4: Check callback logs to see what PayTouch sends
            print("\n\n4. Analyzing PayTouch Callback Data")
            print("-" * 80)
            
            # Check if callback_logs table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_name = 'callback_logs'
            """)
            
            if cursor.fetchone()['count'] > 0:
                cursor.execute("""
                    SELECT 
                        cl.request_data,
                        cl.created_at,
                        pt.txn_id
                    FROM callback_logs cl
                    INNER JOIN payout_transactions pt ON cl.txn_id = pt.txn_id
                    WHERE pt.pg_partner = 'PayTouch'
                    ORDER BY cl.created_at DESC
                    LIMIT 3
                """)
                
                callbacks = cursor.fetchall()
                
                if callbacks:
                    print(f"Found {len(callbacks)} recent PayTouch callbacks:")
                    for cb in callbacks:
                        print(f"\nCallback for {cb['txn_id']} at {cb['created_at']}:")
                        try:
                            data = json.loads(cb['request_data'])
                            print(f"  Fields: {list(data.keys())}")
                            
                            # Check for UTR-like fields
                            for key in data.keys():
                                if any(term in key.lower() for term in ['utr', 'ref', 'bank', 'rrn']):
                                    print(f"  {key}: {data[key]}")
                        except:
                            pass
                else:
                    print("No PayTouch callbacks found in logs")
            else:
                print("callback_logs table doesn't exist")
            
            # Step 5: Recommendations
            print("\n\n5. Recommendations")
            print("=" * 80)
            
            if no_utr_count > 0:
                print("⚠️  PayTouch is not providing UTR in their API responses")
                print("\nPossible solutions:")
                print("1. Contact PayTouch support to confirm:")
                print("   - What field name they use for UTR")
                print("   - Whether UTR is available in status check API")
                print("   - Whether UTR is only sent in callbacks")
                print()
                print("2. Check backend logs for actual callback data:")
                print("   grep -A 30 'PayTouch Payout Callback Received' /var/www/moneyone/logs/backend.log")
                print()
                print("3. If PayTouch uses a different field name, update:")
                print("   - paytouch_service.py (check_payout_status method)")
                print("   - paytouch_callback_routes.py (callback handler)")
            else:
                print("✅ UTR mapping appears to be working correctly")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    fix_paytouch_utr()
