#!/usr/bin/env python3
"""Check merchant_callbacks table structure"""

import pymysql
from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Check merchant_callbacks table structure
cursor.execute('DESCRIBE merchant_callbacks')
columns = cursor.fetchall()

print('merchant_callbacks table columns:')
for col in columns:
    print(f'  {col}')

conn.close()
