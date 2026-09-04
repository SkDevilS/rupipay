#!/usr/bin/env python3
"""Diagnose reconciliation feature - check tables and data"""

import sys
sys.path.insert(0, '/var/www/moneyone/backend')

from database import get_db_connection

def diagnose():
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # 1. Check payin_transactions table structure
            print("=" * 70)
            print("1. PAYIN_TRANSACTIONS TABLE")
            print("=" * 70)
            
            cursor.execute("DESCRIBE payin_transactions")
            payin_cols = cursor.fetchall()
            payin_col_names = [col['Field'] for col in payin_cols]
            
            print(f"Total columns: {len(payin_col_names)}")
            print(f"Columns: {', '.join(payin_col_names)}")
            
            # Check for INITIATED payins
            print("\n" + "=" * 70)
            print("2. CHECKING FOR INITIATED PAYINS")
            print("=" * 70)
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM payin_transactions 
                WHERE status = 'INITIATED'
            """)
            initiated_count = cursor.fetchone()
            print(f"Total INITIATED payins: {initiated_count['count']}")
            
            if initiated_count['count'] > 0:
                # Get sample data
                cursor.execute("""
                    SELECT merchant_id, COUNT(*) as count
                    FROM payin_transactions 
                    WHERE status = 'INITIATED'
                    GROUP BY merchant_id
                    ORDER BY count DESC
                    LIMIT 5
                """)
                merchants = cursor.fetchall()
                print("\nTop 5 merchants with INITIATED payins:")
                for m in merchants:
                    print(f"  - {m['merchant_id']}: {m['count']} transactions")
                
                # Get a sample transaction
                cursor.execute("""
                    SELECT * FROM payin_transactions 
                    WHERE status = 'INITIATED'
                    LIMIT 1
                """)
                sample = cursor.fetchone()
                print("\nSample INITIATED payin:")
                for key, value in sample.items():
                    print(f"  {key}: {value}")
            
            # 3. Check payout table
            print("\n" + "=" * 70)
            print("3. CHECKING PAYOUT TABLES")
            print("=" * 70)
            
            # Try different table names
            payout_table = None
            for table_name in ['payout_transactions', 'payouts', 'payout']:
                try:
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        payout_table = table_name
                        print(f"✓ Found payout table: {table_name}")
                        break
                except:
                    continue
            
            if not payout_table:
                print("✗ No payout table found!")
                print("\nAll tables in database:")
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                for table in tables:
                    table_name = list(table.values())[0]
                    print(f"  - {table_name}")
            else:
                # Check payout table structure
                cursor.execute(f"DESCRIBE {payout_table}")
                payout_cols = cursor.fetchall()
                payout_col_names = [col['Field'] for col in payout_cols]
                
                print(f"\nTotal columns in {payout_table}: {len(payout_col_names)}")
                print(f"Columns: {', '.join(payout_col_names)}")
                
                # Check for QUEUED/INITIATED payouts
                print("\n" + "=" * 70)
                print("4. CHECKING FOR QUEUED/INITIATED PAYOUTS")
                print("=" * 70)
                
                cursor.execute(f"""
                    SELECT COUNT(*) as count 
                    FROM {payout_table}
                    WHERE status IN ('QUEUED', 'INITIATED')
                """)
                payout_count = cursor.fetchone()
                print(f"Total QUEUED/INITIATED payouts: {payout_count['count']}")
                
                if payout_count['count'] > 0:
                    # Get sample data
                    cursor.execute(f"""
                        SELECT merchant_id, status, COUNT(*) as count
                        FROM {payout_table}
                        WHERE status IN ('QUEUED', 'INITIATED')
                        GROUP BY merchant_id, status
                        ORDER BY count DESC
                        LIMIT 5
                    """)
                    merchants = cursor.fetchall()
                    print("\nTop 5 merchants with QUEUED/INITIATED payouts:")
                    for m in merchants:
                        print(f"  - {m['merchant_id']} ({m['status']}): {m['count']} transactions")
                    
                    # Get a sample transaction
                    cursor.execute(f"""
                        SELECT * FROM {payout_table}
                        WHERE status IN ('QUEUED', 'INITIATED')
                        LIMIT 1
                    """)
                    sample = cursor.fetchone()
                    print("\nSample QUEUED/INITIATED payout:")
                    for key, value in sample.items():
                        print(f"  {key}: {value}")
            
            # 4. Test the actual query from reconciliation_routes.py
            print("\n" + "=" * 70)
            print("5. TESTING ACTUAL RECONCILIATION QUERY")
            print("=" * 70)
            
            # Get a merchant with INITIATED payins
            cursor.execute("""
                SELECT merchant_id 
                FROM payin_transactions 
                WHERE status = 'INITIATED'
                LIMIT 1
            """)
            test_merchant = cursor.fetchone()
            
            if test_merchant:
                merchant_id = test_merchant['merchant_id']
                print(f"\nTesting with merchant: {merchant_id}")
                
                # Test the query
                query = """
                    SELECT 
                        pt.id,
                        pt.txn_id,
                        pt.order_id,
                        pt.merchant_id,
                        pt.amount,
                        pt.charge_amount,
                        pt.net_amount,
                        pt.status,
                        pt.pg_partner,
                        pt.pg_txn_id,
                        pt.created_at,
                        pt.callback_url,
                        m.full_name as merchant_name,
                        m.mobile as merchant_mobile
                    FROM payin_transactions pt
                    LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                    WHERE pt.merchant_id = %s
                    AND pt.status = 'INITIATED'
                    ORDER BY pt.created_at DESC
                    LIMIT 5
                """
                
                cursor.execute(query, (merchant_id,))
                results = cursor.fetchall()
                
                print(f"Query returned {len(results)} results")
                
                if results:
                    print("\nFirst result:")
                    for key, value in results[0].items():
                        print(f"  {key}: {value}")
                else:
                    print("No results returned!")
            else:
                print("No merchant with INITIATED payins found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose()
