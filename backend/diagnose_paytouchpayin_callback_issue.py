"""
Diagnose PayTouchPayin Callback Forwarding Issue
Check why merchant callbacks are not being forwarded
"""

from database_pooled import get_db_connection
from datetime import datetime
import json

def diagnose_callback_issue():
    """Diagnose callback forwarding issue"""
    
    print("\n" + "="*80)
    print("🔍 DIAGNOSING PAYTOUCHPAYIN CALLBACK FORWARDING ISSUE")
    print("="*80)
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get most recent PayTouchPayin transaction
    print("\n📋 Step 1: Finding most recent PayTouchPayin transaction...")
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
    
    txn = {
        'txn_id': txn_row[0],
        'merchant_id': txn_row[1],
        'order_id': txn_row[2],
        'status': txn_row[3],
        'amount': txn_row[4],
        'pg_txn_id': txn_row[5],
        'created_at': txn_row[6],
        'updated_at': txn_row[7]
    }
    
    print(f"✅ Found transaction:")
    print(f"  TXN ID: {txn['txn_id']}")
    print(f"  Merchant: {txn['merchant_id']}")
    print(f"  Status: {txn['status']}")
    print(f"  Amount: ₹{txn['amount']}")
    print(f"  Created: {txn['created_at']}")
    print(f"  Updated: {txn['updated_at']}")
    
    # Check merchant callback URL configuration
    print(f"\n📋 Step 2: Checking merchant callback URL configuration...")
    
    # Check merchants table
    cursor.execute("""
        SELECT callback_url
        FROM merchants
        WHERE merchant_id = %s
    """, (txn['merchant_id'],))
    
    merchant_row = cursor.fetchone()
    
    if merchant_row and merchant_row[0]:
        callback_url = merchant_row[0]
        print(f"✅ Callback URL found in 'merchants' table:")
        print(f"  URL: {callback_url}")
    else:
        print(f"❌ NO callback URL configured in 'merchants' table")
        callback_url = None
    
    # Check merchant_callbacks table (for payout)
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'merchant_callbacks'
    """)
    
    if cursor.fetchone()[0] > 0:
        cursor.execute("""
            SELECT payout_callback_url, is_active
            FROM merchant_callbacks
            WHERE merchant_id = %s
        """, (txn['merchant_id'],))
        
        payout_callback_row = cursor.fetchone()
        
        if payout_callback_row:
            print(f"\nℹ️  Found entry in 'merchant_callbacks' table:")
            print(f"  Payout Callback URL: {payout_callback_row[0] if payout_callback_row[0] else 'NOT SET'}")
            print(f"  Is Active: {payout_callback_row[1]}")
            print(f"  ⚠️  NOTE: This is for PAYOUT callbacks, not PAYIN!")
    
    # Check if callback was attempted
    print(f"\n📋 Step 3: Checking if callback was attempted...")
    
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
            print(f"✅ Callback attempt found:")
            print(f"  Log ID: {callback_log[0]}")
            print(f"  Callback URL: {callback_log[1]}")
            print(f"  Response Code: {callback_log[3]}")
            print(f"  Attempted At: {callback_log[5]}")
            
            if callback_log[2]:
                try:
                    request_data = json.loads(callback_log[2])
                    print(f"\n  Request Data:")
                    print(f"    {json.dumps(request_data, indent=4)}")
                except:
                    pass
            
            if callback_log[4]:
                print(f"\n  Response: {callback_log[4][:200]}")
        else:
            print(f"❌ NO callback attempt found in callback_logs")
            print(f"  This means the callback forwarding code was NOT executed")
    else:
        print(f"⚠️  callback_logs table does not exist")
    
    # Check server logs hint
    print(f"\n📋 Step 4: Checking what might be wrong...")
    
    issues_found = []
    
    if not callback_url:
        issues_found.append("❌ No callback URL configured for merchant")
        print(f"\n❌ ISSUE 1: No callback URL configured")
        print(f"  Solution: Configure callback_url in merchants table")
        print(f"  SQL: UPDATE merchants SET callback_url = 'https://...' WHERE merchant_id = '{txn['merchant_id']}';")
    
    if txn['status'] in ['INITIATED', 'pending']:
        issues_found.append("⚠️  Transaction still in pending status")
        print(f"\n⚠️  ISSUE 2: Transaction status is '{txn['status']}'")
        print(f"  This means callback from PayTouch has not been received yet")
        print(f"  OR callback handler is not processing it correctly")
    
    # Check if callback handler is looking in the right place
    print(f"\n📋 Step 5: Checking callback handler logic...")
    print(f"\n⚠️  CRITICAL: PayTouchPayin callbacks come to PayTouch2 endpoint!")
    print(f"  Endpoint: /api/callback/paytouch2/payout")
    print(f"  Handler must:")
    print(f"    1. Detect if callback is PAYIN (has 'txnid' + 'product' fields)")
    print(f"    2. For PAYIN: Look for callback_url in 'merchants' table")
    print(f"    3. For PAYOUT: Look for payout_callback_url in 'merchant_callbacks' table")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ DIAGNOSIS COMPLETE")
    print("="*80)
    
    if issues_found:
        print(f"\n🔴 Issues Found: {len(issues_found)}")
        for issue in issues_found:
            print(f"  {issue}")
    else:
        print(f"\n✅ No obvious issues found")
        print(f"  Check server logs for callback processing:")
        print(f"  sudo journalctl -u moneyone-backend -f | grep -i paytouch")
    
    print(f"\n💡 Next Steps:")
    print(f"  1. Ensure callback URL is configured: python3 check_merchant_callback_config.py")
    print(f"  2. Deploy fixed callback handler: ./deploy_paytouchpayin_callback_fix_final.sh")
    print(f"  3. Test with new transaction")
    print(f"  4. Monitor logs: sudo journalctl -u moneyone-backend -f | grep -i paytouch")


if __name__ == "__main__":
    try:
        diagnose_callback_issue()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
