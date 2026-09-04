import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

connection = pymysql.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    cursorclass=pymysql.cursors.DictCursor
)

cursor = connection.cursor()

print("\n" + "="*80)
print("CHECKING ALL WALLET-RELATED TABLES")
print("="*80 + "\n")

# Get all tables
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()

wallet_tables = []
for table in tables:
    table_name = list(table.values())[0]
    if 'wallet' in table_name.lower() or 'transaction' in table_name.lower():
        wallet_tables.append(table_name)
        print(f"Found table: {table_name}")

print("\n" + "="*80)
print("CHECKING STRUCTURE OF EACH TABLE")
print("="*80 + "\n")

for table_name in wallet_tables:
    print(f"\n{table_name} columns:")
    print("-" * 80)
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['Field']} - {col['Type']}")

cursor.close()
connection.close()
