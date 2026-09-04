"""
Check merchants table structure
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_table():
    """Check merchants table structure"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("="*80)
    print("MERCHANTS TABLE STRUCTURE")
    print("="*80)
    print()
    
    cursor.execute("DESCRIBE merchants")
    columns = cursor.fetchall()
    
    print("Columns in merchants table:")
    print()
    for col in columns:
        print(f"  - {col}")
    
    print()
    print("="*80)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_table()
