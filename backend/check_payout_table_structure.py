#!/usr/bin/env python3
"""
Check Payout Table Structure
Checks the actual columns in the payout_transactions table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_table_structure():
    """
    Check the structure of payout_transactions table
    """
    
    print("=" * 80)
    print("Payout Transactions Table Structure")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get table structure
            cursor.execute("DESCRIBE payout_transactions")
            columns = cursor.fetchall()
            
            print("Available columns:")
            print("-" * 40)
            for col in columns:
                print(f"  {col['Field']} - {col['Type']} - {col['Null']} - {col['Key']} - {col['Default']}")
            
            print(f"\nTotal columns: {len(columns)}")
            
            # Get column names only
            column_names = [col['Field'] for col in columns]
            print(f"\nColumn names: {', '.join(column_names)}")
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    check_table_structure()