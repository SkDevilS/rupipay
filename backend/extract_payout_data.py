#!/usr/bin/env python3
"""
Simple script to extract payout data from database for specific order IDs
"""

import pymysql
from config import Config
from datetime import datetime
import json

# Order IDs to search for
ORDER_IDS = [
    "DP202603211123227D557A",
    "DP2026032111230879694C",
    "DP20260321112021D5DFE0",
    "DP20260321111935565DB1",
    "DP2026032111191828B4E8",
    "DP202603211117295EF78D",
    "DP202603211116582EA094",
    "DP20260321110813AC31E9",
    "DP202603211102490B25BF",
    "DP202603211102228BEE47",
    "DP202603211102088F7A3E",
    "DP20260321105452D21C4F",
    "DP20260321105102FC67AE"
]

def get_db_connection():
    """Get database connection"""
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=3306,
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✓ Connected to database: {Config.DB_NAME}@{Config.DB_HOST}")
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def extract_payout_data():
    """Extract payout data from database"""
    print("\n" + "=" * 80)
    print("PAYOUT DATA EXTRACTION")
    print("=" * 80)
    print(f"\nSearching for {len(ORDER_IDS)} order IDs in database...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    all_data = []
    
    try:
        with conn.cursor() as cursor:
            # Search payout table
            print("\n📊 Querying payout table...")
            print("-" * 80)
            
            placeholders = ', '.join(['%s'] * len(ORDER_IDS))
            query = f"""
                SELECT 
                    id,
                    order_id,
                    merchant_id,
                    admin_id,
                    amount,
                    charge,
                    final_amount,
                    account_number,
                    ifsc_code,
                    account_holder_name,
                    pg_name,
                    status,
                    pg_order_id,
                    pg_txn_id,
                    utr,
                    error_message,
                    created_at,
                    updated_at,
                    settled_at
                FROM payout
                WHERE order_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS)
            payouts = cursor.fetchall()
            
            print(f"\n✓ Found {len(payouts)} payout records\n")
            
            for payout in payouts:
                print("=" * 80)
                print(f"Order ID: {payout['order_id']}")
                print("-" * 80)
                print(f"  ID: {payout['id']}")
                print(f"  Merchant ID: {payout['merchant_id']}")
                print(f"  Admin ID: {payout['admin_id']}")
                print(f"  Amount: ₹{payout['amount']}")
                print(f"  Charge: ₹{payout['charge']}")
                print(f"  Final Amount: ₹{payout['final_amount']}")
                print(f"  Account: {payout['account_number']}")
                print(f"  IFSC: {payout['ifsc_code']}")
                print(f"  Holder: {payout['account_holder_name']}")
                print(f"  PG: {payout['pg_name']}")
                print(f"  Status: {payout['status']}")
                print(f"  PG Order ID: {payout['pg_order_id']}")
                print(f"  PG Txn ID: {payout['pg_txn_id']}")
                print(f"  UTR: {payout['utr']}")
                print(f"  Error: {payout['error_message']}")
                print(f"  Created: {payout['created_at']}")
                print(f"  Updated: {payout['updated_at']}")
                print(f"  Settled: {payout['settled_at']}")
                
                all_data.append({
                    'source': 'payout_table',
                    'data': payout
                })
            
            # Search transactions table
            print("\n📊 Querying transactions table...")
            print("-" * 80)
            
            query = f"""
                SELECT *
                FROM transactions
                WHERE pg_order_id IN ({placeholders})
                   OR order_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS + ORDER_IDS)
            transactions = cursor.fetchall()
            
            print(f"\n✓ Found {len(transactions)} transaction records\n")
            
            for txn in transactions:
                print("=" * 80)
                print(f"Transaction ID: {txn['id']}")
                print("-" * 80)
                print(f"  Order ID: {txn.get('order_id', 'N/A')}")
                print(f"  PG Order ID: {txn.get('pg_order_id', 'N/A')}")
                print(f"  Merchant ID: {txn.get('merchant_id', 'N/A')}")
                print(f"  Type: {txn['txn_type']}")
                print(f"  Amount: ₹{txn['amount']}")
                print(f"  Status: {txn.get('status', 'N/A')}")
                print(f"  Created: {txn['created_at']}")
                
                all_data.append({
                    'source': 'transactions_table',
                    'data': txn
                })
            
    finally:
        conn.close()
    
    # Generate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'payout_data_report_{timestamp}.txt'
    json_file = f'payout_data_{timestamp}.json'
    
    # Text report
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PAYOUT DATA EXTRACTION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Order IDs Searched: {len(ORDER_IDS)}\n")
        f.write(f"Total Records Found: {len(all_data)}\n\n")
        
        for order_id in ORDER_IDS:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"ORDER ID: {order_id}\n")
            f.write("=" * 80 + "\n\n")
            
            order_records = [rec for rec in all_data 
                           if rec['data'].get('order_id') == order_id 
                           or rec['data'].get('pg_order_id') == order_id]
            
            if not order_records:
                f.write("No records found\n")
            else:
                for record in order_records:
                    f.write(f"\nSource: {record['source']}\n")
                    f.write("-" * 80 + "\n")
                    for key, value in record['data'].items():
                        f.write(f"{key}: {value}\n")
                    f.write("-" * 80 + "\n")
    
    # JSON data
    with open(json_file, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'order_ids': ORDER_IDS,
            'total_records': len(all_data),
            'records': all_data
        }, f, indent=2, default=str)
    
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\n✅ Reports generated:")
    print(f"   📄 {report_file}")
    print(f"   📄 {json_file}")
    print(f"\n📊 Total records extracted: {len(all_data)}")
    print("\n")

if __name__ == '__main__':
    extract_payout_data()
