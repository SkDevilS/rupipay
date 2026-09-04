#!/usr/bin/env python3
"""Check merchants table structure"""

from database_pooled import get_db_connection

def check_merchants_table():
    """Check the structure of merchants table"""
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get table structure
            cursor.execute("DESCRIBE merchants")
            columns = cursor.fetchall()
            
            print("\n" + "="*60)
            print("MERCHANTS TABLE STRUCTURE")
            print("="*60)
            
            for col in columns:
                print(f"Column: {col['Field']}")
                print(f"  Type: {col['Type']}")
                print(f"  Null: {col['Null']}")
                print(f"  Key: {col['Key']}")
                print(f"  Default: {col['Default']}")
                print()
            
            print("="*60)
            
            # Check if there's an is_active or active column
            column_names = [col['Field'] for col in columns]
            print("\nAll column names:")
            for name in column_names:
                print(f"  - {name}")
            
            print("\n" + "="*60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_merchants_table()
