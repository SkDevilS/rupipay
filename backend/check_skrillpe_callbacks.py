"""
Check SkrillPe callback activity and recent transactions
"""

from database import get_db_connection
from datetime import datetime, timedelta

print("=" * 80)
print("SkrillPe Callback & Transaction Check")
print("=" * 80)

conn = get_db_connection()
if not conn:
    print("ERROR: Database connection failed")
    exit(1)

try:
    with conn.cursor() as cursor:
        # Check recent SkrillPe transactions
        print("\n1. Recent SkrillPe Transactions (Last 24 hours):")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                txn_id,
                order_id,
                amount,
                status,
                pg_txn_id,
                bank_ref_no as utr,
                created_at,
                updated_at,
                completed_at
            FROM payin_transactions
            WHERE pg_partner = 'SkrillPe'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        transactions = cursor.fetchall()
        
        if transactions:
            for txn in transactions:
                print(f"\nTXN ID: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Amount: ₹{txn['amount']}")
                print(f"  Status: {txn['status']}")
                print(f"  PG TXN ID: {txn['pg_txn_id']}")
                print(f"  UTR: {txn['utr']}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Updated: {txn['updated_at']}")
                print(f"  Completed: {txn['completed_at']}")
        else:
            print("No SkrillPe transactions found in last 24 hours")
        
        # Check INITIATED transactions
        print("\n2. INITIATED SkrillPe Transactions (Waiting for payment):")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                txn_id,
                order_id,
                amount,
                created_at,
                TIMESTAMPDIFF(MINUTE, created_at, NOW()) as age_minutes
            FROM payin_transactions
            WHERE pg_partner = 'SkrillPe'
            AND status = 'INITIATED'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        initiated = cursor.fetchall()
        
        if initiated:
            for txn in initiated:
                print(f"\nTXN ID: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Amount: ₹{txn['amount']}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Age: {txn['age_minutes']} minutes")
        else:
            print("No INITIATED transactions found")
        
        # Check wallet credits
        print("\n3. Recent Wallet Credits from SkrillPe:")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                mwt.merchant_id,
                mwt.amount,
                mwt.reference_id,
                mwt.description,
                mwt.created_at,
                pt.order_id,
                pt.status
            FROM merchant_wallet_transactions mwt
            JOIN payin_transactions pt ON mwt.reference_id = pt.txn_id
            WHERE pt.pg_partner = 'SkrillPe'
            AND mwt.txn_type = 'UNSETTLED_CREDIT'
            AND mwt.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY mwt.created_at DESC
            LIMIT 10
        """)
        
        credits = cursor.fetchall()
        
        if credits:
            for credit in credits:
                print(f"\nMerchant: {credit['merchant_id']}")
                print(f"  Amount: ₹{credit['amount']}")
                print(f"  Reference: {credit['reference_id']}")
                print(f"  Order ID: {credit['order_id']}")
                print(f"  Status: {credit['status']}")
                print(f"  Created: {credit['created_at']}")
        else:
            print("No wallet credits found in last 24 hours")
        
        # Summary
        print("\n4. Summary:")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM payin_transactions
            WHERE pg_partner = 'SkrillPe'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY status
        """)
        
        summary = cursor.fetchall()
        
        if summary:
            for row in summary:
                print(f"{row['status']}: {row['count']} transactions, ₹{row['total_amount']}")
        else:
            print("No transactions in last 24 hours")

finally:
    conn.close()

print("\n" + "=" * 80)
print("Check Complete")
print("=" * 80)
print("\nTo check server logs for callback activity:")
print("sudo journalctl -u moneyone-api -f | grep -i skrillpe")
