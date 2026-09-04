"""
Comprehensive PayTouch Callbacks Checker
Checks recent callbacks for both PayTouchPayin (PAYIN) and PayTouch2 (PAYOUT)
"""

from database_pooled import get_db_connection
from datetime import datetime
import json

def check_paytouchpayin_callbacks():
    """Check recent PayTouchPayin (PAYIN) callbacks"""
    
    print("\n" + "="*80)
    print("📥 PAYTOUCHPAYIN (PAYIN) CALLBACKS")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check payin_transactions table
    print("\n🔍 Checking payin_transactions table...")
    cursor.execute("""
        SELECT txn_id, merchant_id, status, amount, 
               pg_txn_id, created_at, updated_at
        FROM payin_transactions
        WHERE pg_partner = 'paytouchpayin'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    payin_txns = cursor.fetchall()
    
    if payin_txns:
        print(f"\n✅ Found {len(payin_txns)} recent PayTouchPayin transactions:")
        print(f"\n{'TXN ID':<20} {'Status':<10} {'Amount':<10} {'PG TXN ID':<20} {'Created':<20} {'Updated':<20}")
        print("-" * 110)
        
        for txn in payin_txns:
            txn_id = txn[0]
            status = txn[2]
            amount = txn[3]
            pg_txn_id = txn[4] or 'N/A'
            created = txn[5].strftime('%Y-%m-%d %H:%M:%S') if txn[5] else 'N/A'
            updated = txn[6].strftime('%Y-%m-%d %H:%M:%S') if txn[6] else 'N/A'
            
            print(f"{txn_id:<20} {status:<10} ₹{amount:<9} {pg_txn_id:<20} {created:<20} {updated:<20}")
    else:
        print("❌ No PayTouchPayin transactions found")
    
    # Check payin table (fallback)
    print("\n🔍 Checking payin table (fallback)...")
    cursor.execute("""
        SELECT txn_id, merchant_id, status, amount, utr,
               pg_txn_id, created_at, updated_at
        FROM payin
        WHERE pg_partner = 'paytouchpayin'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    payin_old = cursor.fetchall()
    
    if payin_old:
        print(f"\n✅ Found {len(payin_old)} transactions in payin table:")
        print(f"\n{'TXN ID':<20} {'Status':<10} {'Amount':<10} {'UTR':<15} {'Created':<20}")
        print("-" * 85)
        
        for txn in payin_old:
            txn_id = txn[0]
            status = txn[2]
            amount = txn[3]
            utr = txn[4] or 'N/A'
            created = txn[6].strftime('%Y-%m-%d %H:%M:%S') if txn[6] else 'N/A'
            
            print(f"{txn_id:<20} {status:<10} ₹{amount:<9} {utr:<15} {created:<20}")
    else:
        print("ℹ️  No transactions in payin table")
    
    cursor.close()
    conn.close()


def check_paytouch2_callbacks():
    """Check recent PayTouch2 (PAYOUT) callbacks"""
    
    print("\n" + "="*80)
    print("💸 PAYTOUCH2 (PAYOUT) CALLBACKS")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check payout_transactions table
    print("\n🔍 Checking payout_transactions table...")
    cursor.execute("""
        SELECT txn_id, merchant_id, admin_id, status, amount, utr,
               pg_txn_id, created_at, completed_at, updated_at
        FROM payout_transactions
        WHERE pg_partner = 'Paytouch2'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    payout_txns = cursor.fetchall()
    
    if payout_txns:
        print(f"\n✅ Found {len(payout_txns)} recent PayTouch2 transactions:")
        print(f"\n{'TXN ID':<20} {'Type':<10} {'Status':<10} {'Amount':<10} {'UTR':<15} {'Created':<20} {'Completed':<20}")
        print("-" * 120)
        
        for txn in payout_txns:
            txn_id = txn[0]
            merchant_id = txn[1]
            admin_id = txn[2]
            txn_type = 'Merchant' if merchant_id else ('Admin' if admin_id else 'Unknown')
            status = txn[3]
            amount = txn[4]
            utr = txn[5] or 'N/A'
            created = txn[7].strftime('%Y-%m-%d %H:%M:%S') if txn[7] else 'N/A'
            completed = txn[8].strftime('%Y-%m-%d %H:%M:%S') if txn[8] else 'N/A'
            
            print(f"{txn_id:<20} {txn_type:<10} {status:<10} ₹{amount:<9} {utr:<15} {created:<20} {completed:<20}")
    else:
        print("❌ No PayTouch2 transactions found")
    
    cursor.close()
    conn.close()


def check_callback_logs():
    """Check callback logs to see which endpoint received callbacks"""
    
    print("\n" + "="*80)
    print("📋 CALLBACK LOGS (Last 20)")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if callback_logs table exists
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'callback_logs'
    """)
    
    table_exists = cursor.fetchone()[0] > 0
    
    if not table_exists:
        print("ℹ️  callback_logs table does not exist")
        cursor.close()
        conn.close()
        return
    
    cursor.execute("""
        SELECT cl.id, cl.txn_id, cl.callback_url, cl.request_data,
               cl.response_code, cl.created_at,
               COALESCE(pt.pg_partner, pit.pg_partner) as pg_partner
        FROM callback_logs cl
        LEFT JOIN payout_transactions pt ON cl.txn_id = pt.txn_id
        LEFT JOIN payin_transactions pit ON cl.txn_id = pit.txn_id
        WHERE COALESCE(pt.pg_partner, pit.pg_partner) IN ('Paytouch2', 'paytouchpayin')
        ORDER BY cl.created_at DESC
        LIMIT 20
    """)
    
    logs = cursor.fetchall()
    
    if logs:
        print(f"\n✅ Found {len(logs)} callback logs:")
        print(f"\n{'ID':<8} {'TXN ID':<20} {'PG Partner':<15} {'Response':<10} {'Created':<20}")
        print("-" * 85)
        
        for log in logs:
            log_id = log[0]
            txn_id = log[1]
            pg_partner = log[6] or 'Unknown'
            response_code = log[4]
            created = log[5].strftime('%Y-%m-%d %H:%M:%S') if log[5] else 'N/A'
            
            print(f"{log_id:<8} {txn_id:<20} {pg_partner:<15} {response_code:<10} {created:<20}")
    else:
        print("ℹ️  No callback logs found for PayTouch services")
    
    cursor.close()
    conn.close()


def check_endpoint_routing():
    """Check which endpoint is handling which callbacks"""
    
    print("\n" + "="*80)
    print("🔀 ENDPOINT ROUTING ANALYSIS")
    print("="*80)
    
    print("\n📍 Expected Endpoints:")
    print("  PayTouchPayin (PAYIN):  /api/paytouchpayin/callback")
    print("  PayTouch2 (PAYOUT):     /api/callback/paytouch2/payout")
    
    print("\n🔍 Checking app.py for registered blueprints...")
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
            
            if 'paytouchpayin_callback_bp' in content:
                print("  ✅ paytouchpayin_callback_bp registered")
            else:
                print("  ❌ paytouchpayin_callback_bp NOT registered")
            
            if 'paytouch2_callback_bp' in content:
                print("  ✅ paytouch2_callback_bp registered")
            else:
                print("  ❌ paytouch2_callback_bp NOT registered")
    except Exception as e:
        print(f"  ⚠️  Could not read app.py: {e}")


def analyze_callback_issue():
    """Analyze if callbacks are going to wrong endpoint"""
    
    print("\n" + "="*80)
    print("🔬 CALLBACK ROUTING ISSUE ANALYSIS")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check recent PayTouchPayin transactions
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
               SUM(CASE WHEN status = 'pending' OR status = 'INITIATED' THEN 1 ELSE 0 END) as pending_count,
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
        FROM payin_transactions
        WHERE pg_partner = 'paytouchpayin'
        AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """)
    
    payin_stats = cursor.fetchone()
    
    # Check recent PayTouch2 transactions
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
               SUM(CASE WHEN status IN ('PENDING', 'QUEUED', 'INPROCESS', 'INITIATED') THEN 1 ELSE 0 END) as pending_count,
               SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count
        FROM payout_transactions
        WHERE pg_partner = 'Paytouch2'
        AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """)
    
    payout_stats = cursor.fetchone()
    
    print("\n📊 Last 24 Hours Statistics:")
    print("\nPayTouchPayin (PAYIN):")
    print(f"  Total: {payin_stats[0]}")
    print(f"  Success: {payin_stats[1]}")
    print(f"  Pending: {payin_stats[2]}")
    print(f"  Failed: {payin_stats[3]}")
    
    print("\nPayTouch2 (PAYOUT):")
    print(f"  Total: {payout_stats[0]}")
    print(f"  Success: {payout_stats[1]}")
    print(f"  Pending: {payout_stats[2]}")
    print(f"  Failed: {payout_stats[3]}")
    
    # Check for stuck transactions
    print("\n⚠️  Potential Issues:")
    
    if payin_stats[2] > 0:
        print(f"  - {payin_stats[2]} PayTouchPayin transactions stuck in pending")
        print("    → Callbacks may not be reaching the endpoint")
    
    if payout_stats[2] > 0:
        print(f"  - {payout_stats[2]} PayTouch2 transactions stuck in pending")
        print("    → Callbacks may not be reaching the endpoint")
    
    cursor.close()
    conn.close()


def main():
    """Main function"""
    
    print("\n" + "="*80)
    print("🔍 PAYTOUCH CALLBACKS COMPREHENSIVE CHECKER")
    print("="*80)
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Check PayTouchPayin callbacks
        check_paytouchpayin_callbacks()
        
        # Check PayTouch2 callbacks
        check_paytouch2_callbacks()
        
        # Check callback logs
        check_callback_logs()
        
        # Check endpoint routing
        check_endpoint_routing()
        
        # Analyze callback issues
        analyze_callback_issue()
        
        print("\n" + "="*80)
        print("✅ CHECK COMPLETE")
        print("="*80)
        
        print("\n💡 Next Steps:")
        print("  1. If callbacks are missing, check server logs:")
        print("     sudo journalctl -u moneyone-backend -f | grep -i paytouch")
        print("  2. Verify callback URLs are configured correctly with PayTouch team")
        print("  3. Check if both blueprints are registered in app.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
