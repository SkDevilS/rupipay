#!/usr/bin/env python3
"""Check database table structures for reconciliation feature"""

import sys
sys.path.insert(0, '/var/www/moneyone/backend')

from database import get_db_connection

def check_tables():
    """Check payin_transactions and payout tables structure"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # Check payin_transactions table
            print("=" * 60)
            print("PAYIN_TRANSACTIONS TABLE STRUCTURE")
            print("=" * 60)
            cursor.execute("DESCRIBE payin_transactions")
            payin_columns = cursor.fetchall()
            
            print("\nColumns in payin_transactions:")
            for col in payin_columns:
                print(f"  - {col['Field']} ({col['Type']})")
            
            payin_col_names = [col['Field'] for col in payin_columns]
            print("\n" + "=" * 60)
            print("CHECKING FOR REQUIRED COLUMNS")
            print("=" * 60)
            
            required_payin = ['txn_id', 'order_id', 'merchant_id', 'amount', 'status', 
                             'created_at', 'callback_url', 'charge_amount', 'net_amount']
            
            for col in required_payin:
                if col in payin_col_names:
                    print(f"✓ {col} - EXISTS")
                else:
                    print(f"✗ {col} - MISSING")
            
            # Check for service_name or pg_partner
            if 'service_name' in payin_col_names:
                print(f"✓ service_name - EXISTS")
            else:
                print(f"✗ service_name - MISSING (will use pg_partner instead)")
            
            if 'pg_partner' in payin_col_names:
                print(f"✓ pg_partner - EXISTS")
            else:
                print(f"✗ pg_partner - MISSING")
            
            # Check payout tables
            print("\n" + "=" * 60)
            print("CHECKING PAYOUT TABLES")
            print("=" * 60)
            
            # Try different possible table names
            payout_tables = ['payouts', 'payout_transactions', 'payout']
            payout_table_found = None
            
            for table_name in payout_tables:
                try:
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    result = cursor.fetchone()
                    if result:
                        payout_table_found = table_name
                        print(f"✓ Found payout table: {table_name}")
                        break
                except Exception as e:
                    continue
            
            if not payout_table_found:
                print("✗ No payout table found!")
                print("\nAvailable tables:")
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                for table in tables:
                    table_name = list(table.values())[0]
                    if 'payout' in table_name.lower():
                        print(f"  - {table_name}")
            else:
                # Show payout table structure
                print(f"\n{payout_table_found.upper()} TABLE STRUCTURE")
                print("=" * 60)
                cursor.execute(f"DESCRIBE {payout_table_found}")
                payout_columns = cursor.fetchall()
                
                print(f"\nColumns in {payout_table_found}:")
                for col in payout_columns:
                    print(f"  - {col['Field']} ({col['Type']})")
                
                payout_col_names = [col['Field'] for col in payout_columns]
                
                print("\n" + "=" * 60)
                print("CHECKING FOR REQUIRED COLUMNS")
                print("=" * 60)
                
                required_payout = ['txn_id', 'reference_id', 'order_id', 'merchant_id', 
                                  'amount', 'status', 'created_at', 'callback_url',
                                  'charge_amount', 'net_amount', 'bene_name', 
                                  'account_no', 'ifsc_code']
                
                for col in required_payout:
                    if col in payout_col_names:
                        print(f"✓ {col} - EXISTS")
                    else:
                        print(f"✗ {col} - MISSING")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    check_tables()
