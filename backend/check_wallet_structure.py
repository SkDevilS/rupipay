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
print("CHECKING WALLET TABLE STRUCTURE")
print("="*80 + "\n")

# Check merchant_wallet columns
cursor.execute("DESCRIBE merchant_wallet")
wallet_columns = cursor.fetchall()

print("merchant_wallet columns:")
for col in wallet_columns:
    print(f"  {col['Field']} - {col['Type']} - {col['Null']} - {col['Key']} - {col['Default']}")

print("\n" + "="*80 + "\n")

cursor.close()
connection.close()
