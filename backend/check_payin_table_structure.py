#!/usr/bin/env python3
"""
Check payin_transactions table structure
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_table_structure():
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            cursor.execute("DESCRIBE payin_transactions")
            columns = cursor.fetchall()
            
            print("\n" + "="*80)
            print("PAYIN_TRANSACTIONS TABLE STRUCTURE")
            print("="*80 + "\n")
            
            for col in columns:
                print(f"{col['Field']:30s} {col['Type']:30s} {col['Null']:5s} {col['Key']:5s}")
            
            print("\n" + "="*80 + "\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_table_structure()
