#!/usr/bin/env python3
"""
Script to extract all log data with timestamps for specific payout order IDs
Searches through application logs, error logs, and database records
"""

import json
import re
from datetime import datetime
import pymysql
from config import Config

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

# Log file paths - check multiple possible locations
LOG_FILES = [
    '/var/log/flask/app.log',
    '/var/log/flask/error.log',
    'app.log',
    'error.log'
]

def get_db_connection():
    """Get database connection"""
    try:
        return pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=3306,  # Default MySQL port
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def search_log_files():
    """Search through log files for order IDs"""
    print("=" * 80)
    print("SEARCHING LOG FILES")
    print("=" * 80)
    
    all_logs = []
    
    for log_file in LOG_FILES:
        print(f"\n📄 Searching: {log_file}")
        print("-" * 80)
        
        try:
            with open(log_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Check if any order ID is in this line
                    for order_id in ORDER_IDS:
                        if order_id in line:
                            try:
                                # Try to parse as JSON
                                log_entry = json.loads(line.strip())
                                log_entry['source'] = log_file
                                log_entry['line_number'] = line_num
                                log_entry['order_id'] = order_id
                                all_logs.append(log_entry)
                                
                                print(f"\n✓ Found {order_id} at line {line_num}")
                                print(f"  Timestamp: {log_entry.get('timestamp', 'N/A')}")
                                print(f"  Level: {log_entry.get('level', 'N/A')}")
                                print(f"  Message: {log_entry.get('message', 'N/A')[:100]}...")
                                
                            except json.JSONDecodeError:
                                # Not JSON, treat as plain text
                                all_logs.append({
                                    'timestamp': extract_timestamp_from_line(line),
                                    'source': log_file,
                                    'line_number': line_num,
                                    'order_id': order_id,
                                    'raw_line': line.strip()
                                })
                                print(f"\n✓ Found {order_id} at line {line_num} (plain text)")
                                print(f"  Content: {line.strip()[:100]}...")
                            
                            break  # Found in this line, move to next line
                            
        except FileNotFoundError:
            print(f"⚠️  Log file not found: {log_file}")
        except Exception as e:
            print(f"❌ Error reading {log_file}: {e}")
    
    return all_logs

def extract_timestamp_from_line(line):
    """Extract timestamp from plain text log line"""
    # Common timestamp patterns
    patterns = [
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # 2026-03-21 11:23:22
        r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',  # 21/03/2026 11:23:22
        r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}',  # 21-03-2026 11:23:22
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(0)
    
    return 'N/A'

def search_database():
    """Search database for payout records"""
    print("\n" + "=" * 80)
    print("SEARCHING DATABASE")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to database")
        return []
    
    all_records = []
    
    try:
        with conn.cursor() as cursor:
            # Search in payout table
            print("\n📊 Searching payout table...")
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
            
            print(f"\n✓ Found {len(payouts)} payout records")
            
            for payout in payouts:
                print(f"\n  Order ID: {payout['order_id']}")
                print(f"  Status: {payout['status']}")
                print(f"  PG: {payout['pg_name']}")
                print(f"  Amount: ₹{payout['amount']}")
                print(f"  Created: {payout['created_at']}")
                print(f"  Updated: {payout['updated_at']}")
                if payout.get('utr'):
                    print(f"  UTR: {payout['utr']}")
                if payout.get('error_message'):
                    print(f"  Error: {payout['error_message']}")
                
                all_records.append({
                    'source': 'database_payout',
                    'data': payout
                })
            
            # Search in payout_status_history table if it exists
            print("\n📊 Searching payout_status_history table...")
            print("-" * 80)
            
            try:
                query = f"""
                    SELECT 
                        psh.*,
                        p.order_id
                    FROM payout_status_history psh
                    JOIN payout p ON psh.payout_id = p.id
                    WHERE p.order_id IN ({placeholders})
                    ORDER BY psh.created_at DESC
                """
                
                cursor.execute(query, ORDER_IDS)
                history = cursor.fetchall()
                
                print(f"\n✓ Found {len(history)} status history records")
                
                for record in history:
                    print(f"\n  Order ID: {record['order_id']}")
                    print(f"  Status: {record['old_status']} → {record['new_status']}")
                    print(f"  Changed at: {record['created_at']}")
                    if record.get('remarks'):
                        print(f"  Remarks: {record['remarks']}")
                    
                    all_records.append({
                        'source': 'database_status_history',
                        'data': record
                    })
                    
            except Exception as e:
                print(f"⚠️  Status history table not found or error: {e}")
            
            # Search in transactions table
            print("\n📊 Searching transactions table...")
            print("-" * 80)
            
            try:
                query = f"""
                    SELECT 
                        t.*
                    FROM transactions t
                    WHERE t.pg_order_id IN ({placeholders})
                       OR t.order_id IN ({placeholders})
                    ORDER BY t.created_at DESC
                """
                
                cursor.execute(query, ORDER_IDS + ORDER_IDS)
                transactions = cursor.fetchall()
                
                print(f"\n✓ Found {len(transactions)} transaction records")
                
                for txn in transactions:
                    print(f"\n  Order ID: {txn.get('order_id') or txn.get('pg_order_id')}")
                    print(f"  Type: {txn['txn_type']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Created: {txn['created_at']}")
                    
                    all_records.append({
                        'source': 'database_transactions',
                        'data': txn
                    })
                    
            except Exception as e:
                print(f"⚠️  Transactions table search error: {e}")
            
    finally:
        conn.close()
    
    return all_records

def generate_report(log_entries, db_records):
    """Generate comprehensive report"""
    print("\n" + "=" * 80)
    print("GENERATING COMPREHENSIVE REPORT")
    print("=" * 80)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'payout_logs_report_{timestamp}.txt'
    json_file = f'payout_logs_data_{timestamp}.json'
    
    # Generate text report
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PAYOUT ORDER IDS LOG EXTRACTION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total Order IDs Searched: {len(ORDER_IDS)}\n")
        f.write(f"Total Log Entries Found: {len(log_entries)}\n")
        f.write(f"Total Database Records Found: {len(db_records)}\n\n")
        
        # Group by order ID
        for order_id in ORDER_IDS:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"ORDER ID: {order_id}\n")
            f.write("=" * 80 + "\n\n")
            
            # Log entries for this order
            order_logs = [log for log in log_entries if log.get('order_id') == order_id]
            f.write(f"Log Entries: {len(order_logs)}\n")
            f.write("-" * 80 + "\n")
            
            for log in sorted(order_logs, key=lambda x: x.get('timestamp', '')):
                f.write(f"\nTimestamp: {log.get('timestamp', 'N/A')}\n")
                f.write(f"Source: {log.get('source', 'N/A')}\n")
                f.write(f"Level: {log.get('level', 'N/A')}\n")
                
                if 'message' in log:
                    f.write(f"Message: {log['message']}\n")
                if 'raw_line' in log:
                    f.write(f"Content: {log['raw_line']}\n")
                
                f.write("-" * 40 + "\n")
            
            # Database records for this order
            order_records = [rec for rec in db_records 
                           if rec['data'].get('order_id') == order_id 
                           or rec['data'].get('pg_order_id') == order_id]
            
            f.write(f"\nDatabase Records: {len(order_records)}\n")
            f.write("-" * 80 + "\n")
            
            for record in order_records:
                f.write(f"\nSource: {record['source']}\n")
                f.write(f"Data: {json.dumps(record['data'], indent=2, default=str)}\n")
                f.write("-" * 40 + "\n")
    
    # Generate JSON data file
    all_data = {
        'generated_at': datetime.now().isoformat(),
        'order_ids': ORDER_IDS,
        'summary': {
            'total_order_ids': len(ORDER_IDS),
            'total_log_entries': len(log_entries),
            'total_db_records': len(db_records)
        },
        'log_entries': log_entries,
        'database_records': [rec['data'] for rec in db_records]
    }
    
    with open(json_file, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    
    print(f"\n✅ Reports generated:")
    print(f"   📄 Text Report: {report_file}")
    print(f"   📄 JSON Data: {json_file}")
    
    return report_file, json_file

def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("PAYOUT ORDER IDS LOG EXTRACTION")
    print("=" * 80)
    print(f"\nSearching for {len(ORDER_IDS)} order IDs:")
    for i, order_id in enumerate(ORDER_IDS, 1):
        print(f"  {i}. {order_id}")
    
    # Search log files
    log_entries = search_log_files()
    
    # Search database
    db_records = search_database()
    
    # Generate report
    report_file, json_file = generate_report(log_entries, db_records)
    
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   • Log entries found: {len(log_entries)}")
    print(f"   • Database records found: {len(db_records)}")
    print(f"   • Reports saved: {report_file}, {json_file}")
    print("\n")

if __name__ == '__main__':
    main()
