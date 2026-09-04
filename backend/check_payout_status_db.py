"""
Check payout transaction status in database
"""
from database import get_db_connection

def check_status():
    conn = get_db_connection()
    if not conn:
        print("Database connection failed")
        return
    
    with conn.cursor() as cursor:
        # Check recent payout transactions
        cursor.execute("""
            SELECT txn_id, reference_id, merchant_id, amount, status, 
                   pg_partner, pg_txn_id, utr, created_at, completed_at
            FROM payout_transactions
            WHERE pg_partner = 'Mudrape'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        transactions = cursor.fetchall()
        
        print("\n" + "=" * 120)
        print("Recent Mudrape Payout Transactions")
        print("=" * 120)
        print(f"{'TXN ID':<20} {'Reference ID':<25} {'Amount':<10} {'Status':<15} {'PG TXN ID':<30} {'Created':<20}")
        print("-" * 120)
        
        for txn in transactions:
            print(f"{txn['txn_id']:<20} {txn['reference_id']:<25} {txn['amount']:<10} "
                  f"{str(txn['status']):<15} {str(txn['pg_txn_id']):<30} {str(txn['created_at']):<20}")
        
        print("=" * 120)
        
        # Check for NULL status
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM payout_transactions
            WHERE pg_partner = 'Mudrape' AND (status IS NULL OR status = '')
        """)
        
        null_count = cursor.fetchone()['count']
        print(f"\nTransactions with NULL/empty status: {null_count}")
        
    conn.close()

if __name__ == '__main__':
    check_status()
