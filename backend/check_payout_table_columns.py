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
print("CHECKING PAYOUT_TRANSACTIONS TABLE STRUCTURE")
print("="*80 + "\n")

cursor.execute("DESCRIBE payout_transactions")
columns = cursor.fetchall()

print("payout_transactions columns:")
for col in columns:
    print(f"  {col['Field']} - {col['Type']}")

print("\n" + "="*80 + "\n")

cursor.close()
connection.close()
