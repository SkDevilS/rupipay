#!/usr/bin/env python3
"""
Check merchants table structure
"""
import pymysql
from config import Config

try:
    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = conn.cursor()
    
    # Get table structure
    cursor.execute("DESCRIBE merchants")
    columns = cursor.fetchall()
    
    print("=" * 60)
    print("MERCHANTS TABLE STRUCTURE")
    print("=" * 60)
    for col in columns:
        print(f"Column: {col['Field']}")
        print(f"  Type: {col['Type']}")
        print(f"  Null: {col['Null']}")
        print(f"  Key: {col['Key']}")
        print(f"  Default: {col['Default']}")
        print()
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
