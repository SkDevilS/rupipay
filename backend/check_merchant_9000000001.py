#!/usr/bin/env python3
"""
Investigate merchant 9000000001 - why are their payouts being deleted?
"""

from database import get_db_connection

def investigate_merchant():
    """Check merchant 9000000001 details and their payouts"""
    print("=" * 80)
    print("INVESTIGATING MERCHANT 9000000001")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check if merchant exists
            cursor.execute("""
                SELECT * FROM merchants WHERE merchant_id = '9000000001'
            """)
            merchant = cursor.fetchone()
            
            if merchant:
                print(f"\n✅ Merchant EXISTS:")
                print(f"  Merchant ID: {merchant['merchant_id']}")
                print(f"  Full Name: {merchant['full_name']}")
                print(f"  Email: {merchant['email']}")
                print(f"  Mobile: {merchant['mobile']}")
                print(f"  Type: {merchant['merchant_type']}")
                print(f"  Active: {merchant['is_active']}")
                print(f"  Created: {merchant['created_at']}")
            else:
                print(f"\n❌ Merchant 9000000001 NOT FOUND in merchants table!")
                print(f"   This could be why payouts are being deleted!")
            
            # Check payouts for this merchant
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
                    MIN(created_at) as first_payout,
                    MAX(created_at) as last_payout
                FROM payout_transactions
                WHERE merchant_id = '9000000001'
            """)
            stats = cursor.fetchone()
            
            print(f"\n📊 Payout Statistics for 9000000001:")
            print(f"  Total Payouts: {stats['total']}")
            print(f"  Success: {stats['success_count']}")
            print(f"  Failed: {stats['failed_count']}")
            print(f"  First Payout: {stats['first_payout']}")
            print(f"  Last Payout: {stats['last_payout']}")
            
            # Check recent payouts
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    order_id,
                    amount,
                    status,
                    created_at,
                    updated_at
                FROM payout_transactions
                WHERE merchant_id = '9000000001'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent = cursor.fetchall()
            
            print(f"\n📋 Recent Payouts:")
            for payout in recent:
                print(f"  - {payout['reference_id']}: ₹{payout['amount']:.2f} ({payout['status']}) at {payout['created_at']}")
            
            # Check wallet
            cursor.execute("""
                SELECT * FROM merchant_wallet WHERE merchant_id = '9000000001'
            """)
            wallet = cursor.fetchone()
            
            if wallet:
                print(f"\n💰 Wallet Balance:")
                print(f"  Balance: ₹{wallet.get('balance', 0):.2f}")
                print(f"  Settled: ₹{wallet.get('settled_balance', 0):.2f}")
                print(f"  Unsettled: ₹{wallet.get('unsettled_balance', 0):.2f}")
            
            # Check wallet transactions
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN txn_type = 'DEBIT' AND description LIKE '%Payout%' THEN 1 ELSE 0 END) as payout_debits
                FROM merchant_wallet_transactions
                WHERE merchant_id = '9000000001'
            """)
            wallet_txns = cursor.fetchone()
            
            print(f"\n📊 Wallet Transactions:")
            print(f"  Total: {wallet_txns['total']}")
            print(f"  Payout Debits: {wallet_txns['payout_debits']}")
            
            # Check for foreign key constraints
            cursor.execute("""
                SELECT 
                    CONSTRAINT_NAME,
                    TABLE_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME,
                    DELETE_RULE
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = 'moneyone_db'
                AND TABLE_NAME = 'payout_transactions'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            constraints = cursor.fetchall()
            
            print(f"\n🔗 Foreign Key Constraints on payout_transactions:")
            for constraint in constraints:
                print(f"  - {constraint['CONSTRAINT_NAME']}")
                print(f"    Column: {constraint['COLUMN_NAME']} -> {constraint['REFERENCED_TABLE_NAME']}.{constraint['REFERENCED_COLUMN_NAME']}")
                print(f"    On Delete: {constraint['DELETE_RULE']}")
            
            # Check if merchant is being deleted and recreated
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM merchants
                WHERE merchant_id LIKE '9000000%'
            """)
            similar = cursor.fetchone()
            
            print(f"\n🔍 Similar Merchant IDs (9000000*):")
            print(f"  Found: {similar['count']} merchant(s)")
            
            if similar['count'] > 1:
                cursor.execute("""
                    SELECT merchant_id, full_name, created_at, is_active
                    FROM merchants
                    WHERE merchant_id LIKE '9000000%'
                    ORDER BY created_at DESC
                """)
                all_similar = cursor.fetchall()
                for m in all_similar:
                    print(f"  - {m['merchant_id']}: {m['full_name']} (Active: {m['is_active']}, Created: {m['created_at']})")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    investigate_merchant()
