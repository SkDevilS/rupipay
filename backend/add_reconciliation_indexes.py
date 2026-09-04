#!/usr/bin/env python3
"""
Add indexes for manual reconciliation performance optimization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def add_indexes():
    """Add indexes for reconciliation queries"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            print("=" * 60)
            print("Adding Reconciliation Performance Indexes")
            print("=" * 60)
            
            # Check and add index for payin_transactions
            print("\n1. Checking payin_transactions indexes...")
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = 'payin_transactions' 
                AND index_name = 'idx_merchant_status_created'
            """)
            result = cursor.fetchone()
            
            if result['count'] == 0:
                print("   Creating idx_merchant_status_created on payin_transactions...")
                cursor.execute("""
                    CREATE INDEX idx_merchant_status_created 
                    ON payin_transactions(merchant_id, status, created_at)
                """)
                print("   ✓ Index created successfully")
            else:
                print("   ✓ Index already exists")
            
            # Check and add index for payout_transactions
            print("\n2. Checking payout_transactions indexes...")
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = 'payout_transactions' 
                AND index_name = 'idx_merchant_status_created'
            """)
            result = cursor.fetchone()
            
            if result['count'] == 0:
                print("   Creating idx_merchant_status_created on payout_transactions...")
                cursor.execute("""
                    CREATE INDEX idx_merchant_status_created 
                    ON payout_transactions(merchant_id, status, created_at)
                """)
                print("   ✓ Index created successfully")
            else:
                print("   ✓ Index already exists")
            
            conn.commit()
            
            # Show all indexes
            print("\n" + "=" * 60)
            print("Current Indexes on Transaction Tables")
            print("=" * 60)
            
            cursor.execute("""
                SELECT 
                    table_name,
                    index_name,
                    GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
                    index_type
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                AND table_name IN ('payin_transactions', 'payout_transactions')
                GROUP BY table_name, index_name, index_type
                ORDER BY table_name, index_name
            """)
            
            indexes = cursor.fetchall()
            
            if indexes:
                current_table = None
                for idx in indexes:
                    # Handle both dict and tuple formats
                    try:
                        if isinstance(idx, dict):
                            table = idx.get('table_name')
                            index = idx.get('index_name')
                            cols = idx.get('columns')
                            itype = idx.get('index_type')
                        elif isinstance(idx, (list, tuple)):
                            table = idx[0]
                            index = idx[1]
                            cols = idx[2]
                            itype = idx[3]
                        else:
                            # Try to access as object attributes
                            table = getattr(idx, 'table_name', None)
                            index = getattr(idx, 'index_name', None)
                            cols = getattr(idx, 'columns', None)
                            itype = getattr(idx, 'index_type', None)
                        
                        if table and index:
                            if current_table != table:
                                current_table = table
                                print(f"\n{current_table}:")
                            print(f"  - {index}: ({cols}) [{itype}]")
                    except Exception as e:
                        print(f"  Warning: Could not parse index entry: {e}")
                        continue
            else:
                print("\nNo indexes found.")
            
            print("\n" + "=" * 60)
            print("✓ All indexes added successfully!")
            print("=" * 60)
            
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error adding indexes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()
    
    return True

if __name__ == '__main__':
    success = add_indexes()
    sys.exit(0 if success else 1)
