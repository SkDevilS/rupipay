"""
Check how net_amount is stored in payin_transactions and payout_transactions
"""
import sys
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from database import get_db_connection

def check_net_amount():
    """Check net_amount calculation in database"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("\n" + "="*100)
            print("PAYIN TRANSACTIONS - Net Amount Check")
            print("="*100 + "\n")
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    amount,
                    charges,
                    net_amount,
                    (amount - charges) as calculated_net
                FROM payin_transactions
                WHERE status = 'SUCCESS'
                AND DATE(created_at) = CURDATE()
                LIMIT 5
            """)
            
            payins = cursor.fetchall()
            
            if payins:
                print("Sample PayIn Transactions:")
                for txn in payins:
                    print(f"\nTransaction: {txn['txn_id']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Charges: ₹{txn['charges']}")
                    print(f"  Stored net_amount: ₹{txn['net_amount']}")
                    print(f"  Calculated (amount - charges): ₹{txn['calculated_net']}")
                    if float(txn['net_amount']) == float(txn['calculated_net']):
                        print(f"  ✅ MATCH: net_amount = amount - charges")
                    else:
                        print(f"  ❌ MISMATCH!")
            else:
                print("No successful PayIn transactions found today")
            
            print("\n" + "="*100)
            print("PAYOUT TRANSACTIONS - Net Amount Check")
            print("="*100 + "\n")
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    amount,
                    charges,
                    net_amount,
                    (amount + charges) as calculated_net
                FROM payout_transactions
                WHERE status = 'SUCCESS'
                AND DATE(created_at) = CURDATE()
                LIMIT 5
            """)
            
            payouts = cursor.fetchall()
            
            if payouts:
                print("Sample Payout Transactions:")
                for txn in payouts:
                    print(f"\nTransaction: {txn['txn_id']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Charges: ₹{txn['charges']}")
                    print(f"  Stored net_amount: ₹{txn['net_amount']}")
                    print(f"  Calculated (amount + charges): ₹{txn['calculated_net']}")
                    if float(txn['net_amount']) == float(txn['calculated_net']):
                        print(f"  ✅ MATCH: net_amount = amount + charges")
                    else:
                        print(f"  ❌ MISMATCH!")
            else:
                print("No successful Payout transactions found today")
            
            print("\n" + "="*100)
            print("SUMMARY")
            print("="*100)
            print("\nIf net_amount is stored correctly in database:")
            print("  ✅ Just use: SUM(net_amount)")
            print("\nIf net_amount is NOT stored correctly:")
            print("  ❌ Need to calculate:")
            print("     PayIn: SUM(amount - charges)")
            print("     Payout: SUM(amount + charges)")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_net_amount()
