#!/usr/bin/env python3
"""
Fix Payout Admin ID Issue
Adds admin_id column and migrates existing data
"""

from database import get_db_connection

def add_admin_id_column():
    """Add admin_id column to payout_transactions"""
    print("=" * 80)
    print("ADDING admin_id COLUMN TO payout_transactions")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if column already exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'payout_transactions'
                AND COLUMN_NAME = 'admin_id'
            """)
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print("✅ admin_id column already exists")
            else:
                print("Adding admin_id column...")
                cursor.execute("""
                    ALTER TABLE payout_transactions
                    ADD COLUMN admin_id VARCHAR(50) NULL AFTER merchant_id
                """)
                print("✅ admin_id column added")
            
            # Check if index exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'payout_transactions'
                AND INDEX_NAME = 'idx_admin_id'
            """)
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print("✅ idx_admin_id index already exists")
            else:
                print("Adding index on admin_id...")
                cursor.execute("""
                    ALTER TABLE payout_transactions
                    ADD INDEX idx_admin_id (admin_id)
                """)
                print("✅ idx_admin_id index added")
            
            conn.commit()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error adding admin_id column: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False


def migrate_existing_data():
    """Migrate existing admin payouts to use admin_id column"""
    print("\n" + "=" * 80)
    print("MIGRATING EXISTING ADMIN PAYOUTS")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Find records where merchant_id is not in merchants table
            cursor.execute("""
                SELECT 
                    pt.id,
                    pt.txn_id,
                    pt.merchant_id,
                    pt.admin_id
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE m.merchant_id IS NULL 
                AND pt.merchant_id IS NOT NULL
                AND pt.merchant_id != ''
                AND pt.admin_id IS NULL
            """)
            records_to_migrate = cursor.fetchall()
            
            if not records_to_migrate:
                print("✅ No records need migration")
                conn.close()
                return True
            
            print(f"\n📊 Found {len(records_to_migrate)} records to migrate:")
            for record in records_to_migrate:
                print(f"   TXN ID: {record['txn_id']}, merchant_id: {record['merchant_id']}")
            
            # Migrate records
            print(f"\nMigrating {len(records_to_migrate)} records...")
            cursor.execute("""
                UPDATE payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                SET pt.admin_id = pt.merchant_id,
                    pt.merchant_id = NULL
                WHERE m.merchant_id IS NULL 
                AND pt.merchant_id IS NOT NULL
                AND pt.merchant_id != ''
                AND pt.admin_id IS NULL
            """)
            
            migrated_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ Migrated {migrated_count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error migrating data: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False


def verify_migration():
    """Verify the migration was successful"""
    print("\n" + "=" * 80)
    print("VERIFYING MIGRATION")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_payouts,
                    SUM(CASE WHEN merchant_id IS NOT NULL THEN 1 ELSE 0 END) as merchant_payouts,
                    SUM(CASE WHEN admin_id IS NOT NULL THEN 1 ELSE 0 END) as admin_payouts,
                    SUM(CASE WHEN merchant_id IS NULL AND admin_id IS NULL THEN 1 ELSE 0 END) as orphaned
                FROM payout_transactions
            """)
            stats = cursor.fetchone()
            
            print(f"\n📊 Payout Statistics:")
            print(f"   Total Payouts: {stats['total_payouts']}")
            print(f"   Merchant Payouts: {stats['merchant_payouts']}")
            print(f"   Admin Payouts: {stats['admin_payouts']}")
            print(f"   Orphaned Records: {stats['orphaned']}")
            
            # Check for any remaining issues
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.admin_id
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE pt.merchant_id IS NOT NULL
                AND m.merchant_id IS NULL
            """)
            issues = cursor.fetchall()
            
            if issues:
                print(f"\n⚠️  Found {len(issues)} records with invalid merchant_id:")
                for issue in issues:
                    print(f"   TXN ID: {issue['txn_id']}, merchant_id: {issue['merchant_id']}, admin_id: {issue['admin_id']}")
            else:
                print(f"\n✅ No invalid merchant_id records found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying migration: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PAYOUT ADMIN ID FIX")
    print("=" * 80)
    
    # Step 1: Add admin_id column
    if not add_admin_id_column():
        print("\n❌ Failed to add admin_id column")
        exit(1)
    
    # Step 2: Migrate existing data
    if not migrate_existing_data():
        print("\n❌ Failed to migrate existing data")
        exit(1)
    
    # Step 3: Verify migration
    if not verify_migration():
        print("\n❌ Failed to verify migration")
        exit(1)
    
    print("\n" + "=" * 80)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Update payout_routes.py to use admin_id column for admin payouts")
    print("2. Update report queries to handle both merchant and admin payouts")
    print("3. Deploy changes to all backend instances")
    print("=" * 80)
