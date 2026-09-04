#!/usr/bin/env python3
"""
Check table collation and character set
"""

import pymysql
from config import Config

def check_collation():
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Check merchants table
            print("Checking merchants table...")
            cursor.execute("SHOW CREATE TABLE merchants")
            result = cursor.fetchone()
            create_statement = list(result.values())[1]
            
            print("\nmerchants table CREATE statement:")
            print("=" * 80)
            print(create_statement)
            print("=" * 80)
            
            # Extract character set and collation
            if 'CHARSET=' in create_statement:
                charset = create_statement.split('CHARSET=')[1].split()[0]
                print(f"\n✓ Character Set: {charset}")
            
            if 'COLLATE=' in create_statement or 'COLLATE ' in create_statement:
                collate = create_statement.split('COLLATE')[1].split()[0].replace('=', '')
                print(f"✓ Collation: {collate}")
            
            # Check admin_users table
            print("\n" + "=" * 80)
            print("Checking admin_users table...")
            cursor.execute("SHOW CREATE TABLE admin_users")
            result = cursor.fetchone()
            create_statement = list(result.values())[1]
            
            print("\nadmin_users table CREATE statement:")
            print("=" * 80)
            print(create_statement)
            print("=" * 80)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    check_collation()
