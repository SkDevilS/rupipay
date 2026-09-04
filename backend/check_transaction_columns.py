#!/usr/bin/env python3
"""Check transaction table columns"""

from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

print("=== PAYIN_TRANSACTIONS COLUMNS ===")
cursor.execute("DESCRIBE payin_transactions")
for row in cursor.fetchall():
    print(f"{row['Field']}: {row['Type']}")

print("\n=== PAYOUT_TRANSACTIONS COLUMNS ===")
cursor.execute("DESCRIBE payout_transactions")
for row in cursor.fetchall():
    print(f"{row['Field']}: {row['Type']}")

cursor.close()
conn.close()
