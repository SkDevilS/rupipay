from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Check table structure
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'payout_transactions'
    AND COLUMN_NAME IN ('status', 'completed_at', 'created_at')
    ORDER BY ORDINAL_POSITION
""")

print("=" * 80)
print("Payout Transactions Table Structure")
print("=" * 80)
for row in cursor.fetchall():
    print(f"{row['COLUMN_NAME']}: {row['DATA_TYPE']} | Nullable: {row['IS_NULLABLE']} | Default: {row['COLUMN_DEFAULT']}")

# Check recent transactions
cursor.execute("""
    SELECT txn_id, reference_id, status, pg_txn_id, created_at, completed_at, updated_at
    FROM payout_transactions
    WHERE pg_partner = 'Mudrape'
    ORDER BY created_at DESC
    LIMIT 5
""")

print("\n" + "=" * 80)
print("Recent Mudrape Transactions")
print("=" * 80)
for row in cursor.fetchall():
    print(f"TXN: {row['txn_id']}")
    print(f"  Ref ID: {row['reference_id']}")
    print(f"  Status: {row['status']}")
    print(f"  PG TXN ID: {row['pg_txn_id']}")
    print(f"  Created: {row['created_at']}")
    print(f"  Completed: {row['completed_at']}")
    print(f"  Updated: {row['updated_at']}")
    print()

conn.close()
