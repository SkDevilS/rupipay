"""
Test script to verify wallet debit happens immediately on payout
"""
import pymysql
from database import get_db_connection

def check_wallet_and_payout_sync():
    """Check if wallet debits match payout transactions"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get all merchants
            cursor.execute("SELECT merchant_id, business_name FROM merchants")
            merchants = cursor.fetchall()
            
            print("=" * 80)
            print("WALLET vs PAYOUT SYNC CHECK")
            print("=" * 80)
            
            for merchant in merchants:
                merchant_id = merchant['merchant_id']
                business_name = merchant['business_name']
                
                print(f"\n📊 Merchant: {business_name} ({merchant_id})")
                print("-" * 80)
                
                # Get wallet balance
                cursor.execute("""
                    SELECT balance FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                wallet = cursor.fetchone()
                wallet_balance = float(wallet['balance']) if wallet else 0.0
                
                # Get total wallet debits for payouts
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_debits
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s 
                    AND txn_type = 'DEBIT'
                    AND description LIKE '%Payout%'
                """, (merchant_id,))
                total_debits = float(cursor.fetchone()['total_debits'])
                
                # Get total payout transactions (amount + charges)
                cursor.execute("""
                    SELECT 
                        COUNT(*) as count,
                        COALESCE(SUM(amount), 0) as total_amount,
                        status
                    FROM payout_transactions
                    WHERE merchant_id = %s
                    GROUP BY status
                """, (merchant_id,))
                payouts = cursor.fetchall()
                
                print(f"💰 Current Wallet Balance: ₹{wallet_balance:.2f}")
                print(f"💸 Total Wallet Debits (Payouts): ₹{total_debits:.2f}")
                print(f"\n📋 Payout Transactions:")
                
                total_payout_amount = 0
                for payout in payouts:
                    count = payout['count']
                    amount = float(payout['total_amount'])
                    status = payout['status']
                    total_payout_amount += amount
                    print(f"   {status}: {count} transactions, ₹{amount:.2f}")
                
                print(f"\n🔍 Analysis:")
                if total_debits == total_payout_amount:
                    print(f"   ✅ SYNCED: Wallet debits match payout amounts")
                else:
                    print(f"   ⚠️  MISMATCH: Wallet debits (₹{total_debits:.2f}) != Payout amounts (₹{total_payout_amount:.2f})")
                    print(f"   Difference: ₹{abs(total_debits - total_payout_amount):.2f}")
                
                # Check for negative balance
                if wallet_balance < 0:
                    print(f"   ❌ NEGATIVE BALANCE DETECTED: ₹{wallet_balance:.2f}")
                else:
                    print(f"   ✅ Balance is positive")
            
            print("\n" + "=" * 80)
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_wallet_and_payout_sync()
