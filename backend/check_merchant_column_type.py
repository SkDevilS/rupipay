#!/usr/bin/env python3
"""
Check the actual column type of merchant_id in merchants table
"""

import pymysql
from config import Config

def check_column_type():
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Check merchants table structure
            print("Checking merchants table structure...")
            cursor.execute("DESCRIBE merchants")
            columns = cursor.fetchall()
            
            print("\nmerchants table columns:")
            print("-" * 80)
            for col in columns:
                if col['Field'] == 'merchant_id':
                    print(f"✓ Found merchant_id column:")
                    print(f"  Type: {col['Type']}")
                    print(f"  Null: {col['Null']}")
                    print(f"  Key: {col['Key']}")
                    print(f"  Default: {col['Default']}")
                    print(f"  Extra: {col['Extra']}")
            
            # Check admin_users table structure
            print("\n" + "=" * 80)
            print("Checking admin_users table structure...")
            cursor.execute("DESCRIBE admin_users")
            columns = cursor.fetchall()
            
            print("\nadmin_users table columns:")
            print("-" * 80)
            for col in columns:
                if col['Field'] == 'admin_id':
                    print(f"✓ Found admin_id column:")
                    print(f"  Type: {col['Type']}")
                    print(f"  Null: {col['Null']}")
                    print(f"  Key: {col['Key']}")
                    print(f"  Default: {col['Default']}")
                    print(f"  Extra: {col['Extra']}")
            
            print("\n" + "=" * 80)
            print("Recommendation:")
            print("The merchant_ip_security table should use the EXACT same type")
            print("as the merchants.merchant_id column for the foreign key to work.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    check_column_type()
