#!/usr/bin/env python3
"""
Check payin_transactions table structure
"""

from database import get_db_connection

print("=" * 80)
print("PAYIN_TRANSACTIONS TABLE STRUCTURE")
print("=" * 80)

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("DESCRIBE payin_transactions")
columns = cursor.fetchall()

print("\nColumns in payin_transactions table:")
for col in columns:
    print(f"  - {col['Field']} ({col['Type']}) - Null: {col['Null']}, Default: {col['Default']}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
