"""
Fix the most recent SUCCESS payin transaction to credit unsettled wallet
This is a targeted fix for the specific transaction that was missed
"""

from database import get_db_connection
from wallet_service import wallet_service

def fix_recent_transaction():
    """Fix the most recent SUCCESS payin by crediting unsettled wallet"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get the most recent SUCCESS payin
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    order_id,
                    amount,
                    charge_amount,
                    net_amount,
                    created_at
                FROM payin_transactions
                WHERE status = 'SUCCESS'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            payin = cursor.fetchone()
            
            if not payin:
                print("❌ No SUCCESS payin found")
                return False
            
            print("=" * 80)
            print("MOST RECENT SUCCESS PAYIN")
            print("=" * 80)
            print(f"TXN ID: {payin['txn_id']}")
            print(f"Merchant: {payin['merchant_id']}")
            print(f"Order ID: {payin['order_id']}")
            print(f"Amount: ₹{payin['amount']:.2f}")
            print(f"Charge: ₹{payin['charge_amount']:.2f}")
            print(f"Net Amount: ₹{payin['net_amount']:.2f}")
            print(f"Created: {payin['created_at']}")
            print()
            
            # Check if wallet transaction already exists
            cursor.execute("""
                SELECT txn_id FROM merchant_wallet_transactions
                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
            """, (payin['txn_id'],))
            
            existing = cursor.fetchone()
            
            if existing:
                print("⚠ Wallet transaction already exists!")
                print(f"  Wallet TXN ID: {existing['txn_id']}")
                print()
                print("This transaction has already been credited to unsettled wallet.")
                return True
            
            # Get current unsettled balance
            cursor.execute("""
                SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
            """, (payin['merchant_id'],))
            wallet_result = cursor.fetchone()
            
            if wallet_result:
                unsettled_before = float(wallet_result['unsettled_balance'])
            else:
                # Create wallet if doesn't exist
                cursor.execute("""
                    INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                    VALUES (%s, 0.00, 0.00, 0.00)
                """, (payin['merchant_id'],))
                conn.commit()
                unsettled_before = 0.00
            
            net_amount = float(payin['net_amount'])
            unsettled_after = unsettled_before + net_amount
            
            print("=" * 80)
            print("FIXING TRANSACTION")
            print("=" * 80)
            print(f"Merchant: {payin['merchant_id']}")
            print(f"Net Amount: ₹{net_amount:.2f}")
            print(f"Unsettled Before: ₹{unsettled_before:.2f}")
            print(f"Unsettled After: ₹{unsettled_after:.2f}")
            print()
            
            # Update unsettled balance
            cursor.execute("""
                UPDATE merchant_wallet
                SET unsettled_balance = %s, last_updated = NOW()
                WHERE merchant_id = %s
            """, (unsettled_after, payin['merchant_id']))
            
            # Create wallet transaction
            wallet_txn_id = wallet_service.generate_txn_id('MWT')
            cursor.execute("""
                INSERT INTO merchant_wallet_transactions
                (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                VALUES (%s, %s, 'UNSETTLED_CREDIT', %s, %s, %s, %s, %s)
            """, (
                payin['merchant_id'],
                wallet_txn_id,
                net_amount,
                unsettled_before,
                unsettled_after,
                f"Fixed: Payin credited to unsettled wallet - {payin['order_id']}",
                payin['txn_id']
            ))
            
            conn.commit()
            
            print("✓ Transaction fixed successfully!")
            print(f"  Wallet TXN ID: {wallet_txn_id}")
            print()
            
            # Verify the fix
            cursor.execute("""
                SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
            """, (payin['merchant_id'],))
            updated_wallet = cursor.fetchone()
            
            cursor.execute("""
                SELECT txn_id, amount, balance_after FROM merchant_wallet_transactions
                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
            """, (payin['txn_id'],))
            wallet_txn = cursor.fetchone()
            
            print("=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            print(f"Current Unsettled Balance: ₹{float(updated_wallet['unsettled_balance']):.2f}")
            print(f"Wallet Transaction: {wallet_txn['txn_id']}")
            print(f"  Amount: ₹{wallet_txn['amount']:.2f}")
            print(f"  Balance After: ₹{wallet_txn['balance_after']:.2f}")
            print()
            
            if abs(float(updated_wallet['unsettled_balance']) - unsettled_after) < 0.01:
                print("✓ Verification passed!")
                return True
            else:
                print("❌ Verification failed - balance mismatch!")
                return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 80)
    print("FIX RECENT TRANSACTION - CREDIT TO UNSETTLED WALLET")
    print("=" * 80)
    print()
    
    success = fix_recent_transaction()
    
    print()
    print("=" * 80)
    if success:
        print("✓ FIX COMPLETE!")
        print()
        print("Next steps:")
        print("1. Check merchant dashboard - unsettled balance should show")
        print("2. Check admin dashboard - total unsettled should include this amount")
        print("3. Test settle wallet - should be able to settle this amount")
    else:
        print("❌ FIX FAILED!")
        print()
        print("Please check the error messages above and try again.")
    print("=" * 80)
