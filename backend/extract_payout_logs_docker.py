#!/usr/bin/env python3
"""
Script to extract payout logs from Docker containers
Searches through docker logs and database records
"""

import json
import subprocess
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

def get_docker_containers():
    """Get list of running backend containers"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=backend', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            check=True
        )
        containers = result.stdout.strip().split('\n')
        return [c for c in containers if c]
    except Exception as e:
        print(f"Error getting Docker containers: {e}")
        return []

def search_docker_logs(container_name):
    """Search Docker logs for order IDs"""
    print(f"\n🐳 Searching container: {container_name}")
    print("-" * 80)
    
    found_logs = []
    
    for order_id in ORDER_IDS:
        try:
            # Search for order_id in docker logs
            result = subprocess.run(
                ['docker', 'logs', container_name, '--since', '24h'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logs = result.stdout + result.stderr
            
            for line in logs.split('\n'):
                if order_id in line:
                    found_logs.append({
                        'container': container_name,
                        'order_id': order_id,
                        'log_line': line.strip(),
                        'timestamp': extract_timestamp(line)
                    })
                    print(f"  ✓ Found {order_id}")
                    
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Timeout searching for {order_id}")
        except Exception as e:
            print(f"  ❌ Error searching for {order_id}: {e}")
    
    return found_logs

def extract_timestamp(line):
    """Extract timestamp from log line"""
    import re
    patterns = [
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
        r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
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
            placeholders = ', '.join(['%s'] * len(ORDER_IDS))
            
            # Search payout table
            print("\n📊 Searching payout table...")
            query = f"""
                SELECT 
                    id, order_id, merchant_id, admin_id, amount, charge, final_amount,
                    account_number, ifsc_code, account_holder_name, pg_name, status,
                    pg_order_id, pg_txn_id, utr, error_message,
                    created_at, updated_at, settled_at
                FROM payout
                WHERE order_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS)
            payouts = cursor.fetchall()
            
            print(f"✓ Found {len(payouts)} payout records")
            
            for payout in payouts:
                print(f"\n  Order: {payout['order_id']}")
                print(f"  Status: {payout['status']}")
                print(f"  PG: {payout['pg_name']}")
                print(f"  Amount: ₹{payout['amount']}")
                print(f"  Created: {payout['created_at']}")
                
                all_records.append({
                    'source': 'payout_table',
                    'order_id': payout['order_id'],
                    'data': payout
                })
            
            # Search transactions
            print("\n📊 Searching transactions table...")
            query = f"""
                SELECT *
                FROM transactions
                WHERE pg_order_id IN ({placeholders})
                   OR order_id IN ({placeholders})
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, ORDER_IDS + ORDER_IDS)
            transactions = cursor.fetchall()
            
            print(f"✓ Found {len(transactions)} transaction records")
            
            for txn in transactions:
                all_records.append({
                    'source': 'transactions_table',
                    'order_id': txn.get('order_id') or txn.get('pg_order_id'),
                    'data': txn
                })
            
    finally:
        conn.close()
    
    return all_records

def generate_report(docker_logs, db_records):
    """Generate comprehensive report"""
    print("\n" + "=" * 80)
    print("GENERATING REPORT")
    print("=" * 80)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'payout_logs_report_{timestamp}.txt'
    json_file = f'payout_logs_data_{timestamp}.json'
    
    # Text report
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PAYOUT ORDER IDS LOG EXTRACTION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Order IDs Searched: {len(ORDER_IDS)}\n")
        f.write(f"Docker Log Entries: {len(docker_logs)}\n")
        f.write(f"Database Records: {len(db_records)}\n\n")
        
        for order_id in ORDER_IDS:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"ORDER ID: {order_id}\n")
            f.write("=" * 80 + "\n\n")
            
            # Docker logs
            order_logs = [log for log in docker_logs if log['order_id'] == order_id]
            f.write(f"Docker Logs: {len(order_logs)}\n")
            f.write("-" * 80 + "\n")
            
            for log in order_logs:
                f.write(f"\nContainer: {log['container']}\n")
                f.write(f"Timestamp: {log['timestamp']}\n")
                f.write(f"Log: {log['log_line']}\n")
                f.write("-" * 40 + "\n")
            
            # Database records
            order_records = [rec for rec in db_records if rec['order_id'] == order_id]
            f.write(f"\nDatabase Records: {len(order_records)}\n")
            f.write("-" * 80 + "\n")
            
            for record in order_records:
                f.write(f"\nSource: {record['source']}\n")
                f.write(f"Data: {json.dumps(record['data'], indent=2, default=str)}\n")
                f.write("-" * 40 + "\n")
    
    # JSON data
    all_data = {
        'generated_at': datetime.now().isoformat(),
        'order_ids': ORDER_IDS,
        'summary': {
            'total_order_ids': len(ORDER_IDS),
            'docker_log_entries': len(docker_logs),
            'database_records': len(db_records)
        },
        'docker_logs': docker_logs,
        'database_records': db_records
    }
    
    with open(json_file, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    
    print(f"\n✅ Reports generated:")
    print(f"   📄 {report_file}")
    print(f"   📄 {json_file}")
    
    return report_file, json_file

def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("PAYOUT LOGS EXTRACTION (Docker Version)")
    print("=" * 80)
    print(f"\nSearching for {len(ORDER_IDS)} order IDs")
    
    # Get Docker containers
    print("\n🐳 Finding Docker containers...")
    containers = get_docker_containers()
    
    if containers:
        print(f"✓ Found {len(containers)} backend containers")
        for container in containers:
            print(f"  • {container}")
    else:
        print("⚠️  No Docker containers found, will search database only")
    
    # Search Docker logs
    all_docker_logs = []
    for container in containers:
        logs = search_docker_logs(container)
        all_docker_logs.extend(logs)
    
    # Search database
    db_records = search_database()
    
    # Generate report
    report_file, json_file = generate_report(all_docker_logs, db_records)
    
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   • Docker log entries: {len(all_docker_logs)}")
    print(f"   • Database records: {len(db_records)}")
    print(f"   • Reports: {report_file}, {json_file}")
    print("\n")

if __name__ == '__main__':
    main()
