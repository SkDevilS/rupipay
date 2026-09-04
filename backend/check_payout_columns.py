#!/usr/bin/env python3
"""Check table structures to understand the schema"""

import pymysql
from config import Config

conn = pymysql.connect(
    host=Config.DB_HOST,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME,
    port=3306
)

print(f"✓ Connected to: {Config.DB_NAME}\n")

tables = ['payout_transactions', 'admin_wallet_transactions', 'merchant_wallet_transactions', 'callback_logs']

with conn.cursor() as cursor:
    for table in tables:
        print("=" * 80)
        print(f"TABLE: {table}")
        print("=" * 80)
        cursor.execute(f"DESCRIBE {table}")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]:<30} {col[1]:<20} {col[2]}")
        print()

conn.close()
