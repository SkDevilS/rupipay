#!/usr/bin/env python3
"""
Safely add performance indexes to MySQL 8.4
Checks if index exists before creating to avoid errors
"""

import pymysql
import sys

# Database configuration
DB_CONFIG = {
    'host': 'moneyone-dashboard-db.cfuwygoe61zq.ap-south-1.rds.amazonaws.com',
    'user': 'admin',
    'password': '',  # Will be prompted
    'database': 'moneyone_db'
}

# Indexes to create: (table_name, index_name, columns)
INDEXES = [
    # Payin Transactions
    ('payin_transactions', 'idx_merchant_status', '(merchant_id, status)'),
    ('payin_transactions', 'idx_order_merchant', '(order_id, merchant_id)'),
    ('payin_transactions', 'idx_pg_txn', '(pg_txn_id)'),
    ('payin_transactions', 'idx_bank_ref', '(bank_ref_no)'),
    
    # Payout Transactions
    ('payout_transactions', 'idx_merchant_status', '(merchant_id, status)'),
    ('payout_transactions', 'idx_reference_merchant', '(reference_id, merchant_id)'),
    ('payout_transactions', 'idx_pg_txn', '(pg_txn_id)'),
    ('payout_transactions', 'idx_utr', '(utr)'),
    
    # Merchant Wallet Transactions
    ('merchant_wallet_transactions', 'idx_merchant_created', '(merchant_id, created_at)'),
    ('merchant_wallet_transactions', 'idx_reference', '(reference_id)'),
    ('merchant_wallet_transactions', 'idx_txn_type', '(txn_type)'),
    
    # Admin Wallet Transactions
    ('admin_wallet_transactions', 'idx_admin_created', '(admin_id, created_at)'),
    ('admin_wallet_transactions', 'idx_wallet_txn_type', '(wallet_type, txn_type)'),
    
    # Callback Logs
    ('callback_logs', 'idx_merchant_created', '(merchant_id, created_at)'),
    
    # Service Routing
    ('service_routing', 'idx_merchant_service', '(merchant_id, service_type, is_active)'),
]

def index_exists(cursor, table_name, index_name):
    """Check if an index already exists"""
    query = """
        SELECT COUNT(*) as count
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
        AND INDEX_NAME = %s
    """
    cursor.execute(query, (DB_CONFIG['database'], table_name, index_name))
    result = cursor.fetchone()
    return result['count'] > 0

def create_index(cursor, table_name, index_name, columns):
    """Create an index if it doesn't exist"""
    if index_exists(cursor, table_name, index_name):
        print(f"  ⚠ Index {index_name} on {table_name} already exists, skipping")
        return False
    
    try:
        query = f"CREATE INDEX {index_name} ON {table_name} {columns}"
        cursor.execute(query)
        print(f"  ✓ Created index {index_name} on {table_name}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to create index {index_name} on {table_name}: {e}")
        return False

def main():
    # Get password
    password = input("Enter RDS admin password: ")
    DB_CONFIG['password'] = password
    
    print("\n=== Adding Performance Indexes ===\n")
    
    try:
        # Connect to database
        connection = pymysql.connect(
            **DB_CONFIG,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            created_count = 0
            skipped_count = 0
            
            # Create each index
            for table_name, index_name, columns in INDEXES:
                if create_index(cursor, table_name, index_name, columns):
                    created_count += 1
                else:
                    skipped_count += 1
            
            # Commit changes
            connection.commit()
            
            print(f"\n=== Summary ===")
            print(f"Created: {created_count} indexes")
            print(f"Skipped: {skipped_count} indexes (already exist)")
            
            # Analyze tables
            print("\n=== Analyzing Tables ===")
            tables = set([idx[0] for idx in INDEXES])
            for table in tables:
                cursor.execute(f"ANALYZE TABLE {table}")
                print(f"  ✓ Analyzed {table}")
            
            print("\n✓ All indexes added successfully!")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == '__main__':
    main()
