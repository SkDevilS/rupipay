"""
Calculate and set the correct settled_balance for all merchants
settled_balance = Topups (approved fund requests) - Payouts - Fetch Fund
"""

from database import get_db_connection

def calculate_and_set_settled_balance():
    """Calculate the correct settled_balance and update the database"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get all merchants
            cursor.execute("SELECT merchant_id FROM merchants")
            merchants = cursor.fetchall()
            
            print("=" * 80)
            print("CALCULATE AND SET SETTLED BALANCE")
            print("=" * 80)
            print(f"Found {len(merchants)} merchants")
            print()
            
            for merchant in merchants:
                merchant_id = merchant['merchant_id']
                
                # Get total approved fund requests (topups)
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_topup
                    FROM fund_requests
                    WHERE merchant_id = %s AND status = 'APPROVED'
                """, (merchant_id,))
                topup_result = cursor.fetchone()
                total_topup = float(topup_result['total_topup'])
                
                # Get total payouts
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_payouts
                    FROM payout_transactions
                    WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS')
                """, (merchant_id,))
                payout_result = cursor.fetchone()
                total_payouts = float(payout_result['total_payouts'])
                
                # Get total fetched by admin
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total_fetched
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s 
                    AND txn_type = 'DEBIT'
                    AND description LIKE '%%fetched by admin%%'
                """, (merchant_id,))
                fetch_result = cursor.fetchone()
                total_fetched = float(fetch_result['total_fetched'])
                
                # Calculate settled balance
                settled_balance = total_topup - total_payouts - total_fetched
                
                print(f"Merchant: {merchant_id}")
                print(f"  Total Topup: ₹{total_topup:.2f}")
                print(f"  Total Payouts: ₹{total_payouts:.2f}")
                print(f"  Total Fetched: ₹{total_fetched:.2f}")
                print(f"  Calculated Settled Balance: ₹{settled_balance:.2f}")
                
                # Update or create wallet
                cursor.execute("""
                    SELECT merchant_id FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                wallet_exists = cursor.fetchone()
                
                if wallet_exists:
                    cursor.execute("""
                        UPDATE merchant_wallet
                        SET settled_balance = %s, balance = %s, last_updated = NOW()
                        WHERE merchant_id = %s
                    """, (settled_balance, settled_balance, merchant_id))
                    print(f"  ✓ Updated wallet")
                else:
                    cursor.execute("""
                        INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                        VALUES (%s, %s, %s, 0.00)
                    """, (merchant_id, settled_balance, settled_balance))
                    print(f"  ✓ Created wallet")
                
                print()
            
            conn.commit()
            
            print("=" * 80)
            print("✓ CALCULATION COMPLETE")
            print("=" * 80)
            print()
            
            # Verify the results
            print("=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            cursor.execute("""
                SELECT merchant_id, balance, settled_balance, unsettled_balance
                FROM merchant_wallet
            """)
            wallets = cursor.fetchall()
            
            for wallet in wallets:
                print(f"Merchant: {wallet['merchant_id']}")
                print(f"  Balance: ₹{float(wallet['balance']):.2f}")
                print(f"  Settled Balance: ₹{float(wallet['settled_balance']):.2f}")
                print(f"  Unsettled Balance: ₹{float(wallet['unsettled_balance']):.2f}")
                print()
            
            return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 80)
    print("CALCULATE AND SET SETTLED BALANCE")
    print("=" * 80)
    print()
    print("Formula: settled_balance = Topups - Payouts - Fetch Fund")
    print()
    
    success = calculate_and_set_settled_balance()
    
    print()
    if success:
        print("✓ Calculation completed successfully!")
        print()
        print("Next steps:")
        print("1. Restart backend: sudo systemctl restart moneyone-api")
        print("2. Check merchant dashboard - wallet balance should be correct")
    else:
        print("❌ Calculation failed!")
