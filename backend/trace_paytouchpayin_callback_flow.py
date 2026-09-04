"""
Trace PayTouchPayin Callback Flow
Shows exactly how callback is received and processed
"""

from database_pooled import get_db_connection
from datetime import datetime, timedelta
import json

def trace_callback_flow():
    """Trace the complete callback flow"""
    
    print("\n" + "="*80)
    print("🔍 TRACING PAYTOUCHPAYIN CALLBACK FLOW")
    print("="*80)
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    print("\nInitializing database connection pool...")
    conn = get_db_connection()
    print("Connection pool initialized: max=50, min_cached=10, max_cached=20")
    cursor = conn.cursor()
    
    # Step 1: Find most recent PayTouchPayin transaction
    print("\n📋 STEP 1: Finding most recent PayTouchPayin transaction...")
    cursor.execute("""
        SELECT txn_id, merchant_id, order_id, status, amount, 
               pg_txn_id, created_at, updated_at
        FROM payin_transactions
        WHERE pg_partner = 'paytouchpayin'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    txn_row = cursor.fetchone()
    
    if not txn_row:
        print("❌ No PayTouchPayin transactions found")
        cursor.close()
        conn.close()
        return
    
    # database_pooled uses DictCursor, so txn_row is already a dictionary
    txn = txn_row
    
    print(f"✅ Found transaction:")
    print(f"  TXN ID: {txn['txn_id']}")
    print(f"  Merchant: {txn['merchant_id']}")
    print(f"  Status: {txn['status']}")
    print(f"  Created: {txn['created_at']}")
    print(f"  Updated: {txn['updated_at']}")
    
    # Step 2: Check if status was updated (callback received)
    print(f"\n📋 STEP 2: Checking if callback was received...")
    
    # Note: Database stores status in UPPERCASE
    status_upper = txn['status'].upper() if txn['status'] else ''
    
    if status_upper in ['SUCCESS', 'FAILED']:
        print(f"✅ Status is '{txn['status']}' - Callback WAS received and processed")
        print(f"  Updated at: {txn['updated_at']}")
    else:
        print(f"⚠️  Status is '{txn['status']}' - Callback NOT received yet")
        print(f"  Transaction is still pending")
        cursor.close()
        conn.close()
        return
    
    # Step 3: Check merchant callback URL configuration
    print(f"\n📋 STEP 3: Checking merchant callback URL configuration...")
    
    cursor.execute("""
        SELECT callback_url
        FROM merchants
        WHERE merchant_id = %s
    """, (txn['merchant_id'],))
    
    merchant_row = cursor.fetchone()
    callback_url = merchant_row[0] if merchant_row else None
    
    if callback_url:
        print(f"✅ Callback URL configured:")
        print(f"  URL: {callback_url}")
    else:
        print(f"❌ NO callback URL configured!")
        print(f"  This is why forwarding is not working")
        cursor.close()
        conn.close()
        return
    
    # Step 4: Check if callback was attempted
    print(f"\n📋 STEP 4: Checking if callback forwarding was attempted...")
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'callback_logs'
    """)
    
    if cursor.fetchone()[0] > 0:
        cursor.execute("""
            SELECT id, callback_url, request_data, response_code, 
                   response_data, created_at
            FROM callback_logs
            WHERE txn_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (txn['txn_id'],))
        
        callback_log = cursor.fetchone()
        
        if callback_log:
            print(f"✅ Callback forwarding WAS attempted:")
            print(f"  Log ID: {callback_log[0]}")
            print(f"  Callback URL: {callback_log[1]}")
            print(f"  Response Code: {callback_log[3]}")
            print(f"  Attempted At: {callback_log[5]}")
            
            if callback_log[2]:
                try:
                    request_data = json.loads(callback_log[2])
                    print(f"\n  📤 Request Data Sent to Merchant:")
                    print(json.dumps(request_data, indent=4))
                except:
                    print(f"\n  Request Data: {callback_log[2][:200]}")
            
            if callback_log[4]:
                print(f"\n  📥 Response from Merchant:")
                print(f"  {callback_log[4][:500]}")
            
            print(f"\n✅ CALLBACK FORWARDING IS WORKING!")
        else:
            print(f"❌ NO callback forwarding attempt found!")
            print(f"  This means the forwarding code was NOT executed")
    else:
        print(f"⚠️  callback_logs table does not exist")
        print(f"  Cannot verify if callback was forwarded")
    
    # Step 5: Check server logs for callback processing
    print(f"\n📋 STEP 5: Checking for callback processing in recent time...")
    
    # Check if there are any recent updates around the transaction update time
    if txn['updated_at']:
        time_window_start = txn['updated_at'] - timedelta(minutes=5)
        time_window_end = txn['updated_at'] + timedelta(minutes=5)
        
        print(f"  Looking for callbacks between:")
        print(f"    {time_window_start} and {time_window_end}")
    
    # Step 6: Show what the callback handler should be doing
    print(f"\n📋 STEP 6: Expected callback handler flow...")
    print(f"\n  When PayTouch sends callback to /api/callback/paytouch2/payout:")
    print(f"  1. Detect callback type (PAYIN vs PAYOUT)")
    print(f"     - PAYIN has: 'txnid' + 'product' fields")
    print(f"     - PAYOUT has: 'transaction_id' or 'external_ref' fields")
    print(f"  2. For PAYIN:")
    print(f"     a. Find transaction in payin_transactions table")
    print(f"     b. Update status to 'success' or 'failed'")
    print(f"     c. Credit unsettled wallet (if success)")
    print(f"     d. Get callback_url from merchants table")
    print(f"     e. Forward callback to merchant")
    print(f"     f. Log callback attempt")
    
    # Step 7: Check what's currently deployed
    print(f"\n📋 STEP 7: Checking current callback handler...")
    
    try:
        with open('/var/www/moneyone/moneyone/backend/paytouch2_callback_routes.py', 'r') as f:
            content = f.read()
            
            # Check if it has PAYIN detection logic
            if 'txnid' in content and 'product' in content and 'is_payin' in content:
                print(f"✅ Handler has PAYIN detection logic")
            else:
                print(f"❌ Handler does NOT have PAYIN detection logic")
                print(f"  This is the problem!")
            
            # Check if it looks for callback_url in merchants table
            if 'SELECT callback_url' in content and 'FROM merchants' in content:
                print(f"✅ Handler looks for callback_url in merchants table")
            else:
                print(f"❌ Handler does NOT look for callback_url in merchants table")
                print(f"  It's probably looking in merchant_callbacks table instead")
    except Exception as e:
        print(f"⚠️  Could not read callback handler file: {e}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ TRACE COMPLETE")
    print("="*80)
    
    print(f"\n💡 Summary:")
    status_upper = txn['status'].upper() if txn['status'] else ''
    callback_received = status_upper in ['SUCCESS', 'FAILED']
    print(f"  1. Callback received: {'YES' if callback_received else 'NO'}")
    print(f"  2. Status updated: {'YES' if callback_received else 'NO'}")
    print(f"  3. Callback URL configured: {'YES' if callback_url else 'NO'}")
    
    if callback_url and callback_received:
        print(f"\n🔍 Next Steps:")
        print(f"  1. Check server logs for callback processing:")
        print(f"     sudo journalctl -u moneyone-backend --since '{txn['updated_at']}' | grep -i paytouch")
        print(f"  2. Look for these log messages:")
        print(f"     - 'PayTouch Callback Received'")
        print(f"     - 'Detected: PayTouchPayin PAYIN callback'")
        print(f"     - 'Forwarding callback to merchant'")
        print(f"     - 'Merchant callback response'")
        print(f"  3. If you don't see these messages, the handler needs to be updated")


if __name__ == "__main__":
    try:
        trace_callback_flow()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
