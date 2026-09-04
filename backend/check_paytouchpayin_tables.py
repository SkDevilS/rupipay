"""
Check which table PayTouch Payin is using
"""

from database_pooled import get_db_connection

def check_tables():
    """Check both payin and payin_transactions tables"""
    
    print("="*80)
    print("🔍 Checking PayTouch Payin Tables")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check payin table
    print("\n📋 Checking 'payin' table:")
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM payin
        WHERE pg_partner = 'paytouchpayin'
    """)
    payin_count = cursor.fetchone()
    print(f"  Records in 'payin': {payin_count['count']}")
    
    if payin_count['count'] > 0:
        cursor.execute("""
            SELECT txn_id, merchant_id, status, amount, created_at
            FROM payin
            WHERE pg_partner = 'paytouchpayin'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        records = cursor.fetchall()
        print(f"\n  Recent records in 'payin':")
        for r in records:
            print(f"    - {r['txn_id']}: {r['status']} | ₹{r['amount']} | {r['created_at']}")
    
    # Check payin_transactions table
    print("\n📋 Checking 'payin_transactions' table:")
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM payin_transactions
        WHERE pg_partner = 'paytouchpayin'
    """)
    payin_txn_count = cursor.fetchone()
    print(f"  Records in 'payin_transactions': {payin_txn_count['count']}")
    
    if payin_txn_count['count'] > 0:
        cursor.execute("""
            SELECT txn_id, merchant_id, status, amount, created_at
            FROM payin_transactions
            WHERE pg_partner = 'paytouchpayin'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        records = cursor.fetchall()
        print(f"\n  Recent records in 'payin_transactions':")
        for r in records:
            print(f"    - {r['txn_id']}: {r['status']} | ₹{r['amount']} | {r['created_at']}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("🔍 Analysis:")
    print("="*80)
    
    if payin_count['count'] > 0 and payin_txn_count['count'] == 0:
        print("✅ Using 'payin' table (callback handler is correct)")
    elif payin_txn_count['count'] > 0 and payin_count['count'] == 0:
        print("❌ Using 'payin_transactions' table but callback queries 'payin'")
        print("   This is why callback forwarding fails!")
    elif payin_count['count'] > 0 and payin_txn_count['count'] > 0:
        print("⚠️  Records in BOTH tables - need to check which is active")
    else:
        print("ℹ️  No records found in either table")

if __name__ == "__main__":
    check_tables()
