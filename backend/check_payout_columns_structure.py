#!/usr/bin/env python3
"""
Check the structure of payout_transactions table
"""

import pymysql
from database_pooled import get_db_connection

def check_table_structure():
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Get table structure
        cursor.execute("DESCRIBE payout_transactions")
        columns = cursor.fetchall()
        
        print("=" * 60)
        print("PAYOUT_TRANSACTIONS TABLE STRUCTURE")
        print("=" * 60)
        
        for col in columns:
            print(f"{col['Field']:20} {col['Type']:20} {col['Null']:5} {col['Key']:5}")
        
        print("\n" + "=" * 60)
        
        # Check for a sample record
        cursor.execute("SELECT * FROM payout_transactions LIMIT 1")
        sample = cursor.fetchone()
        
        if sample:
            print("\nSAMPLE RECORD (Column Names):")
            print("=" * 60)
            for key in sample.keys():
                print(f"  {key}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    check_table_structure()
