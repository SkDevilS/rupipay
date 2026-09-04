#!/usr/bin/env python3
"""Check merchant table wallet columns"""

import sys
sys.path.insert(0, '/var/www/moneyone/backend')

from database import get_db_connection

def check_columns():
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            print("=" * 60)
            print("MERCHANTS TABLE WALLET COLUMNS")
            print("=" * 60)
            
            cursor.execute("DESCRIBE merchants")
            columns = cursor.fetchall()
            
            print("\nAll wallet-related columns:")
            for col in columns:
                if 'wallet' in col['Field'].lower() or 'balance' in col['Field'].lower():
                    print(f"  - {col['Field']} ({col['Type']}) - Null: {col['Null']}, Default: {col['Default']}")
            
            print("\n" + "=" * 60)
            print("ALL COLUMNS IN MERCHANTS TABLE")
            print("=" * 60)
            for col in columns:
                print(f"  - {col['Field']}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    check_columns()
