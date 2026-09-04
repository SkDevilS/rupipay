#!/usr/bin/env python3
"""Check wallet-related tables"""

import sys
sys.path.insert(0, '/var/www/moneyone/backend')

from database import get_db_connection

def check_tables():
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # Check for wallet-related tables
            cursor.execute("SHOW TABLES LIKE '%wallet%'")
            wallet_tables = cursor.fetchall()
            
            print("=" * 60)
            print("WALLET-RELATED TABLES")
            print("=" * 60)
            for table in wallet_tables:
                table_name = list(table.values())[0]
                print(f"\n{table_name}:")
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  - {col['Field']} ({col['Type']})")
            
            # Check merchants table for balance columns
            print("\n" + "=" * 60)
            print("CHECKING MERCHANTS TABLE FOR BALANCE/WALLET COLUMNS")
            print("=" * 60)
            cursor.execute("DESCRIBE merchants")
            columns = cursor.fetchall()
            
            balance_cols = [col for col in columns if 'balance' in col['Field'].lower() or 'wallet' in col['Field'].lower()]
            
            if balance_cols:
                print("\nFound balance/wallet columns:")
                for col in balance_cols:
                    print(f"  - {col['Field']} ({col['Type']})")
            else:
                print("\nNo balance/wallet columns found in merchants table")
                print("\nAll columns in merchants table:")
                for col in columns:
                    print(f"  - {col['Field']}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    check_tables()
