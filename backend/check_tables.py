#!/usr/bin/env python3
"""Check what tables exist in the database"""

import pymysql
from config import Config

try:
    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        port=3306
    )
    
    print(f"✓ Connected to: {Config.DB_NAME}@{Config.DB_HOST}\n")
    
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print("Available tables:")
        print("=" * 50)
        for table in tables:
            print(f"  • {table[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
