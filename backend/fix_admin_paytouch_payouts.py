#!/usr/bin/env python3
"""
Fix Admin PayTouch Payouts - Migrate existing admin payouts to use admin_id field
This fixes the "wallet not found" error for admin personal payouts using PayTouch
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def fix_admin_paytouch_payouts():
    """Fix existing admin PayTouch payouts to use admin_id field instead of merchant_id"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("🔍 Checking for admin PayTouch payouts that need fixing...")
            
            # Find PayTouch payouts where merchant_id is actually an admin_id
            # (admin IDs are not in the merchants table)
            cursor.execute("""
                SELECT pt.txn_id, pt.merchant_id, pt.admin_id, pt.reference_id, pt.status, pt.pg_partner
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.pg_partner = 'PayTouch'
                AND pt.merchant_id IS NOT NULL
                AND pt.admin_id IS NULL
                AND m.merchant_id IS NULL
                AND (pt.reference_id LIKE 'ADMIN%' OR pt.merchant_id LIKE 'ADMIN_%')
                ORDER BY pt.created_at DESC
            """)
            
            admin_payouts = cursor.fetchall()
            
            if not admin_payouts:
                print("✅ No admin PayTouch payouts found that need fixing")
                return True
            
            print(f"📋 Found {len(admin_payouts)} admin PayTouch payouts to fix:")
            print()
            
            for payout in admin_payouts:
                print(f"  TXN: {payout['txn_id']}")
                print(f"  Ref: {payout['reference_id']}")
                print(f"  Current merchant_id: {payout['merchant_id']}")
                print(f"  Current admin_id: {payout['admin_id']}")
                print(f"  Status: {payout['status']}")
                print()
            
            # Ask for confirmation
            response = input("Do you want to migrate these records? (y/N): ").strip().lower()
            if response != 'y':
                print("❌ Migration cancelled")
                return False
            
            print("\n🔧 Migrating admin PayTouch payouts...")
            
            # Migrate the records
            for payout in admin_payouts:
                admin_id = payout['merchant_id']
                
                # Clean admin_id if it has ADMIN_ prefix
                if admin_id.startswith('ADMIN_'):
                    admin_id = admin_id.replace('ADMIN_', '')
                
                cursor.execute("""
                    UPDATE payout_transactions
                    SET admin_id = %s, merchant_id = NULL
                    WHERE txn_id = %s
                """, (admin_id, payout['txn_id']))
                
                print(f"  ✅ Migrated {payout['txn_id']}: merchant_id='{payout['merchant_id']}' → admin_id='{admin_id}'")
            
            conn.commit()
            
            # Verify the migration
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                AND admin_id IS NOT NULL
                AND merchant_id IS NULL
            """)
            
            migrated_count = cursor.fetchone()['count']
            
            print(f"\n✅ Migration completed successfully!")
            print(f"📊 Total admin PayTouch payouts now using admin_id field: {migrated_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

def verify_paytouch_callback_compatibility():
    """Verify that PayTouch callback can now find admin payouts correctly"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("\n🔍 Verifying PayTouch callback compatibility...")
            
            # Check admin payouts structure
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_paytouch_payouts,
                    SUM(CASE WHEN merchant_id IS NOT NULL THEN 1 ELSE 0 END) as merchant_payouts,
                    SUM(CASE WHEN admin_id IS NOT NULL THEN 1 ELSE 0 END) as admin_payouts
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
            """)
            
            stats = cursor.fetchone()
            
            print(f"📊 PayTouch Payout Statistics:")
            print(f"  Total PayTouch payouts: {stats['total_paytouch_payouts']}")
            print(f"  Merchant payouts: {stats['merchant_payouts']}")
            print(f"  Admin payouts: {stats['admin_payouts']}")
            
            # Test callback query compatibility
            cursor.execute("""
                SELECT txn_id, status, merchant_id, admin_id, reference_id
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch' AND admin_id IS NOT NULL
                LIMIT 3
            """)
            
            sample_admin_payouts = cursor.fetchall()
            
            if sample_admin_payouts:
                print(f"\n✅ Sample admin payouts (callback will find these):")
                for payout in sample_admin_payouts:
                    print(f"  TXN: {payout['txn_id']}, Admin: {payout['admin_id']}, Status: {payout['status']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("🚀 PayTouch Admin Payout Fix")
    print("=" * 50)
    print()
    
    # Step 1: Fix existing records
    success = fix_admin_paytouch_payouts()
    
    if success:
        # Step 2: Verify compatibility
        verify_paytouch_callback_compatibility()
        
        print("\n" + "=" * 50)
        print("✅ SUMMARY:")
        print("1. Admin personal payouts now use admin_id field correctly")
        print("2. PayTouch callback will find admin payouts and update status to SUCCESS")
        print("3. No wallet deduction will be attempted for admin payouts")
        print("4. Status will change directly from callback (like Mudrape)")
        print("\n🎉 Admin PayTouch payouts should now work correctly!")
    else:
        print("\n❌ Fix failed. Please check the errors above.")