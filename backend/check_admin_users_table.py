#!/usr/bin/env python3
"""
Check admin_users table structure
"""
from database_pooled import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

print("=" * 60)
print("ADMIN_USERS TABLE STRUCTURE")
print("=" * 60)

cursor.execute("DESCRIBE admin_users")
columns = cursor.fetchall()

for col in columns:
    print(f"Column: {col['Field']}")
    print(f"Type: {col['Type']}")
    print(f"Null: {col['Null']}")
    print(f"Key: {col['Key']}")
    print(f"Default: {col['Default']}")
    print()

cursor.close()
conn.close()
