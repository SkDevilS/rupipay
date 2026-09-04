#!/usr/bin/env python3
"""
Extract complete payout data for specific order IDs
Searches across all relevant fields and tables
"""

import pymysql
from config import Config
from datetime import datetime
import json

# Order IDs to extract
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
        print(f"✓ Connected to: {Config.DB_NAME}@{Config.DB_HOST}")
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def main():
    print("\n" + "=" * 80)
    print("PAYOUT ORDER IDS - COMPLETE DATA EXTRACTION")
    print("=" * 80)
    print(f"\nSearching for {len(ORDER_IDS)} order IDs...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    conn = get_db_connection()
    if not conn:
        return
    
    all_data = []
    
    try:
        with conn.cursor() as cursor:
            # Query payout_transactions - search in multiple fields
            print("📊 Querying payout_transactions table...")
            print("-" * 80)
            
            placeholders = ', '.join(['%s'] * len(ORDER_IDS))
            query = f"""
                SELECT *
                FROM payout_transactions
                WHERE order_id IN ({placeholders})
                   OR txn_id IN ({placeholders})
                   OR reference_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS + ORDER_IDS + ORDER_IDS)
            payouts = cursor.fetchall()
            
            print(f"\n✓ Found {len(payouts)} payout records\n")
            
            if len(payouts) == 0:
                print("⚠️  No payout records found for these order IDs")
                print("   These order IDs may not exist in the database\n")
            
            for payout in payouts:
                print("=" * 80)
                print(f"ORDER ID: {payout['order_id']}")
                print(f"TXN ID: {payout['txn_id']}")
                print("=" * 80)
                for key, value in payout.items():
                    print(f"  {key}: {value}")
                print()
                
                all_data.append({
                    'source': 'payout_transactions',
                    'order_id': payout['order_id'],
                    'txn_id': payout['txn_id'],
                    'data': payout
                })
            
            # Query admin_wallet_transactions using reference_id
            print("\n📊 Querying admin_wallet_transactions...")
            print("-" * 80)
            
            query = f"""
                SELECT *
                FROM admin_wallet_transactions
                WHERE reference_id IN ({placeholders})
                   OR txn_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS + ORDER_IDS)
            wallet_txns = cursor.fetchall()
            
            print(f"✓ Found {len(wallet_txns)} admin wallet transactions\n")
            
            for txn in wallet_txns:
                print(f"  Ref ID: {txn.get('reference_id', 'N/A')}")
                print(f"  Type: {txn.get('txn_type', 'N/A')}")
                print(f"  Amount: ₹{txn.get('amount', 0)}")
                print(f"  Created: {txn.get('created_at', 'N/A')}")
                print()
                
                all_data.append({
                    'source': 'admin_wallet_transactions',
                    'reference_id': txn.get('reference_id'),
                    'txn_id': txn.get('txn_id'),
                    'data': txn
                })
            
            # Query merchant_wallet_transactions using reference_id
            print("\n📊 Querying merchant_wallet_transactions...")
            print("-" * 80)
            
            query = f"""
                SELECT *
                FROM merchant_wallet_transactions
                WHERE reference_id IN ({placeholders})
                   OR txn_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS + ORDER_IDS)
            merchant_txns = cursor.fetchall()
            
            print(f"✓ Found {len(merchant_txns)} merchant wallet transactions\n")
            
            for txn in merchant_txns:
                print(f"  Ref ID: {txn.get('reference_id', 'N/A')}")
                print(f"  Merchant: {txn.get('merchant_id', 'N/A')}")
                print(f"  Type: {txn.get('txn_type', 'N/A')}")
                print(f"  Amount: ₹{txn.get('amount', 0)}")
                print(f"  Created: {txn.get('created_at', 'N/A')}")
                print()
                
                all_data.append({
                    'source': 'merchant_wallet_transactions',
                    'reference_id': txn.get('reference_id'),
                    'txn_id': txn.get('txn_id'),
                    'data': txn
                })
            
            # Query callback_logs using txn_id
            print("\n📊 Querying callback_logs...")
            print("-" * 80)
            
            query = f"""
                SELECT *
                FROM callback_logs
                WHERE txn_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS)
            callbacks = cursor.fetchall()
            
            print(f"✓ Found {len(callbacks)} callback logs\n")
            
            for cb in callbacks:
                print(f"  Txn ID: {cb.get('txn_id', 'N/A')}")
                print(f"  Merchant: {cb.get('merchant_id', 'N/A')}")
                print(f"  Response Code: {cb.get('response_code', 'N/A')}")
                print(f"  Created: {cb.get('created_at', 'N/A')}")
                print()
                
                all_data.append({
                    'source': 'callback_logs',
                    'txn_id': cb.get('txn_id'),
                    'data': cb
                })
    
    finally:
        conn.close()
    
    # Generate reports
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'payout_extraction_{timestamp}.txt'
    json_file = f'payout_extraction_{timestamp}.json'
    
    # Text report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PAYOUT ORDER IDS - COMPLETE DATA EXTRACTION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Order IDs Searched: {len(ORDER_IDS)}\n")
        f.write(f"Total Records Found: {len(all_data)}\n\n")
        
        f.write("Searched Order IDs:\n")
        for i, order_id in enumerate(ORDER_IDS, 1):
            f.write(f"  {i}. {order_id}\n")
        f.write("\n")
        
        if len(all_data) == 0:
            f.write("⚠️  NO RECORDS FOUND\n\n")
            f.write("These order IDs do not exist in the database.\n")
            f.write("Possible reasons:\n")
            f.write("  1. Order IDs are incorrect or typos\n")
            f.write("  2. Transactions were never created\n")
            f.write("  3. Data was deleted from database\n")
            f.write("  4. These are from a different environment/database\n")
        else:
            for order_id in ORDER_IDS:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"ORDER ID: {order_id}\n")
                f.write("=" * 80 + "\n\n")
                
                order_records = [rec for rec in all_data 
                               if rec.get('order_id') == order_id 
                               or rec.get('reference_id') == order_id
                               or rec.get('txn_id') == order_id]
                
                if not order_records:
                    f.write("❌ No records found\n")
                else:
                    f.write(f"✓ Found {len(order_records)} records\n\n")
                    
                    for record in order_records:
                        f.write(f"Source: {record['source']}\n")
                        f.write("-" * 80 + "\n")
                        for key, value in record['data'].items():
                            f.write(f"{key}: {value}\n")
                        f.write("\n")
    
    # JSON data
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'order_ids_searched': ORDER_IDS,
            'summary': {
                'total_order_ids': len(ORDER_IDS),
                'total_records_found': len(all_data),
                'by_source': {
                    'payout_transactions': len([r for r in all_data if r['source'] == 'payout_transactions']),
                    'admin_wallet_transactions': len([r for r in all_data if r['source'] == 'admin_wallet_transactions']),
                    'merchant_wallet_transactions': len([r for r in all_data if r['source'] == 'merchant_wallet_transactions']),
                    'callback_logs': len([r for r in all_data if r['source'] == 'callback_logs'])
                }
            },
            'records': all_data
        }, f, indent=2, default=str)
    
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\n✅ Reports generated:")
    print(f"   📄 {report_file}")
    print(f"   📄 {json_file}")
    print(f"\n📊 Summary:")
    print(f"   • Total records found: {len(all_data)}")
    print(f"   • Payout transactions: {len([r for r in all_data if r['source'] == 'payout_transactions'])}")
    print(f"   • Admin wallet txns: {len([r for r in all_data if r['source'] == 'admin_wallet_transactions'])}")
    print(f"   • Merchant wallet txns: {len([r for r in all_data if r['source'] == 'merchant_wallet_transactions'])}")
    print(f"   • Callback logs: {len([r for r in all_data if r['source'] == 'callback_logs'])}")
    
    if len(all_data) == 0:
        print(f"\n⚠️  WARNING: No records found for any of the {len(ORDER_IDS)} order IDs")
        print("   These order IDs may not exist in the database.")
    
    print("\n")

if __name__ == '__main__':
    main()
