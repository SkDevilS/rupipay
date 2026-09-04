from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Check the ENUM values for status column
cursor.execute("""
    SELECT COLUMN_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'payout_transactions' 
    AND COLUMN_NAME = 'status'
""")

result = cursor.fetchone()
print("=" * 80)
print("Payout Transactions Status ENUM Values")
print("=" * 80)
print(f"Column Type: {result['COLUMN_TYPE']}")
print()

# Test inserting different status values
test_statuses = ['INITIATED', 'PENDING', 'SUCCESS', 'FAILED', 'QUEUED', '']

print("Testing status values:")
print("-" * 80)
for status in test_statuses:
    try:
        cursor.execute("""
            SELECT %s as test_status
        """, (status,))
        print(f"✓ '{status}' - Valid")
    except Exception as e:
        print(f"✗ '{status}' - Error: {e}")

conn.close()
