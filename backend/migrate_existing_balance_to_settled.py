"""
Migrate existing balance to settled_balance for all merchants
This is a one-time migration to move old balance data to the new settled_balance field
"""

from database import get_db_connection

def migrate_balance_to_settled():
    """Migrate existing balance to settled_balance"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get all merchant wallets
            cursor.execute("""
                SELECT merchant_id, balance, settled_balance, unsettled_balance
                FROM merchant_wallet
            """)
            wallets = cursor.fetchall()
            
            print("=" * 80)
            print("MIGRATE EXISTING BALANCE TO SETTLED_BALANCE")
            print("=" * 80)
            print(f"Found {len(wallets)} merchant wallets")
            print()
            
            updated_count = 0
            for wallet in wallets:
                merchant_id = wallet['merchant_id']
                old_balance = float(wallet['balance'])
                current_settled = float(wallet['settled_balance'])
                current_unsettled = float(wallet['unsettled_balance'])
                
                # If settled_balance is 0 but balance has value, migrate it
                if current_settled == 0 and old_balance > 0:
                    print(f"Merchant: {merchant_id}")
                    print(f"  Old Balance: ₹{old_balance:.2f}")
                    print(f"  Current Settled: ₹{current_settled:.2f}")
                    print(f"  Current Unsettled: ₹{current_unsettled:.2f}")
                    print(f"  → Migrating ₹{old_balance:.2f} to settled_balance")
                    
                    # Update settled_balance to match old balance
                    cursor.execute("""
                        UPDATE merchant_wallet
                        SET settled_balance = %s, last_updated = NOW()
                        WHERE merchant_id = %s
                    """, (old_balance, merchant_id))
                    
                    updated_count += 1
                    print(f"  ✓ Updated")
                    print()
                elif current_settled > 0:
                    print(f"Merchant: {merchant_id}")
                    print(f"  Settled Balance already set: ₹{current_settled:.2f}")
                    print(f"  Skipping...")
                    print()
            
            if updated_count > 0:
                conn.commit()
                print("=" * 80)
                print(f"✓ MIGRATION COMPLETE - Updated {updated_count} wallets")
                print("=" * 80)
            else:
                print("=" * 80)
                print("✓ NO MIGRATION NEEDED - All wallets already have settled_balance")
                print("=" * 80)
            
            # Verify the migration
            print()
            print("=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            cursor.execute("""
                SELECT merchant_id, balance, settled_balance, unsettled_balance
                FROM merchant_wallet
            """)
            updated_wallets = cursor.fetchall()
            
            for wallet in updated_wallets:
                print(f"Merchant: {wallet['merchant_id']}")
                print(f"  Balance (legacy): ₹{float(wallet['balance']):.2f}")
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
    print("MIGRATE EXISTING WALLET BALANCE TO SETTLED_BALANCE")
    print("=" * 80)
    print()
    print("This will copy the existing 'balance' field to 'settled_balance'")
    print("for all merchants where settled_balance is currently 0.")
    print()
    
    success = migrate_balance_to_settled()
    
    print()
    if success:
        print("✓ Migration completed successfully!")
        print()
        print("Next steps:")
        print("1. Restart backend: sudo systemctl restart moneyone-api")
        print("2. Check merchant dashboard - wallet balance should be correct")
        print("3. Run backfill for unsettled payins if needed")
    else:
        print("❌ Migration failed!")
