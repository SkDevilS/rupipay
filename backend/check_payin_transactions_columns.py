#!/usr/bin/env python3
"""
Check payin_transactions table structure
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
    cursor.execute("DESCRIBE payin_transactions")
    columns = cursor.fetchall()
    
    print("=" * 60)
    print("PAYIN_TRANSACTIONS TABLE STRUCTURE")
    print("=" * 60)
    for col in columns:
        print(f"Column: {col['Field']}")
        print(f"  Type: {col['Type']}")
        print(f"  Null: {col['Null']}")
        print()
    
    # Check if there are any columns for storing request/response data
    print("\n" + "=" * 60)
    print("COLUMNS THAT MIGHT STORE API DATA:")
    print("=" * 60)
    
    api_related_columns = []
    for col in columns:
        field_name = col['Field'].lower()
        if any(keyword in field_name for keyword in ['request', 'response', 'callback', 'pg_', 'payload', 'data']):
            api_related_columns.append(col['Field'])
            print(f"✓ {col['Field']} ({col['Type']})")
    
    if not api_related_columns:
        print("⚠ No API-related columns found!")
        print("\nYou may need to add columns like:")
        print("  - request_payload (TEXT/JSON)")
        print("  - pg_request (TEXT/JSON)")
        print("  - pg_response (TEXT/JSON)")
        print("  - callback_data (TEXT/JSON)")
        print("  - callback_response (TEXT/JSON)")
        print("  - callback_forwarded_at (TIMESTAMP)")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
