"""
Script to identify and optionally fix negative wallet balances
"""
import pymysql
from database import get_db_connection

def find_negative_balances():
    """Find all merchants with negative wallet balances"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find merchants with negative balances
            cursor.execute("""
                SELECT 
                    mw.merchant_id,
                    m.business_name,
                    mw.balance
                FROM merchant_wallet mw
                JOIN merchants m ON mw.merchant_id = m.merchant_id
                WHERE mw.balance < 0
                ORDER BY mw.balance ASC
            """)
            negative_balances = cursor.fetchall()
            
            if not negative_balances:
                print("✅ No negative balances found!")
                return
            
            print("=" * 80)
            print("MERCHANTS WITH NEGATIVE BALANCES")
            print("=" * 80)
            
            for row in negative_balances:
                merchant_id = row['merchant_id']
                business_name = row['business_name']
                balance = float(row['balance'])
                
                print(f"\n❌ {business_name} ({merchant_id})")
                print(f"   Current Balance: ₹{balance:.2f}")
                
                # Get recent transactions
                cursor.execute("""
                    SELECT 
                        txn_id,
                        txn_type,
                        amount,
                        balance_before,
                        balance_after,
                        description,
                        created_at
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (merchant_id,))
                transactions = cursor.fetchall()
                
                print(f"\n   Recent Transactions:")
                for txn in transactions:
                    txn_type = txn['txn_type']
                    amount = float(txn['amount'])
                    balance_before = float(txn['balance_before'])
                    balance_after = float(txn['balance_after'])
                    description = txn['description']
                    created_at = txn['created_at']
                    
                    symbol = "+" if txn_type == "CREDIT" else "-"
                    print(f"   {created_at} | {txn_type:6} | {symbol}₹{amount:8.2f} | ₹{balance_before:8.2f} → ₹{balance_after:8.2f} | {description}")
                
                # Get payout transactions
                cursor.execute("""
                    SELECT 
                        COUNT(*) as count,
                        SUM(amount) as total_amount,
                        status
                    FROM payout_transactions
                    WHERE merchant_id = %s
                    GROUP BY status
                """, (merchant_id,))
                payouts = cursor.fetchall()
                
                print(f"\n   Payout Summary:")
                for payout in payouts:
                    count = payout['count']
                    total = float(payout['total_amount'])
                    status = payout['status']
                    print(f"   {status:10} | {count:3} transactions | ₹{total:.2f}")
            
            print("\n" + "=" * 80)
            print("\nRECOMMENDATIONS:")
            print("1. Review the transactions above to understand why balance went negative")
            print("2. Check if payouts were processed without wallet debit")
            print("3. Consider adding fund requests to bring balance back to positive")
            print("4. Deploy the wallet debit fix to prevent future occurrences")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

def reset_to_zero(merchant_id):
    """Reset a merchant's negative balance to zero (use with caution!)"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get current balance
            cursor.execute("""
                SELECT balance FROM merchant_wallet WHERE merchant_id = %s
            """, (merchant_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                print(f"❌ Wallet not found for merchant {merchant_id}")
                return
            
            current_balance = float(wallet['balance'])
            
            if current_balance >= 0:
                print(f"✅ Balance is already positive: ₹{current_balance:.2f}")
                return
            
            # Calculate adjustment needed
            adjustment = abs(current_balance)
            
            print(f"Current Balance: ₹{current_balance:.2f}")
            print(f"Adjustment Needed: ₹{adjustment:.2f}")
            
            confirm = input(f"\n⚠️  Are you sure you want to reset balance to ₹0.00? (yes/no): ")
            
            if confirm.lower() != 'yes':
                print("❌ Operation cancelled")
                return
            
            # Update balance
            cursor.execute("""
                UPDATE merchant_wallet 
                SET balance = 0.00
                WHERE merchant_id = %s
            """, (merchant_id,))
            
            # Record transaction
            cursor.execute("""
                INSERT INTO merchant_wallet_transactions 
                (merchant_id, txn_id, txn_type, amount, balance_before, balance_after,
                 description, reference_id)
                VALUES (%s, %s, 'CREDIT', %s, %s, 0.00, %s, %s)
            """, (merchant_id, f"ADJ{merchant_id[:8]}", adjustment, current_balance,
                  "Balance adjustment - negative balance reset", "MANUAL_ADJUSTMENT"))
            
            conn.commit()
            print(f"✅ Balance reset to ₹0.00")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        if len(sys.argv) < 3:
            print("Usage: python3 fix_negative_balances.py reset <merchant_id>")
            sys.exit(1)
        reset_to_zero(sys.argv[2])
    else:
        find_negative_balances()
