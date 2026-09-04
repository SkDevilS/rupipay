#!/usr/bin/env python3
"""
Check Airpay Callback Logs
Shows the most recent callbacks received at https://api.moneyone.co.in/api/callback/airpay/payin
"""

import os
import json
from datetime import datetime, timedelta
from database import get_db_connection

def check_callback_log_files():
    """Check callback log files for recent Airpay callbacks"""
    
    print("=" * 100)
    print("AIRPAY CALLBACK LOG FILES")
    print("=" * 100)
    
    log_dir = '/var/www/moneyone/moneyone/backend/logs'
    
    if not os.path.exists(log_dir):
        print(f"❌ Log directory not found: {log_dir}")
        return
    
    # Find Airpay callback log files
    log_files = []
    try:
        for filename in os.listdir(log_dir):
            if filename.startswith('airpay_callbacks_') and filename.endswith('.log'):
                filepath = os.path.join(log_dir, filename)
                log_files.append((filepath, os.path.getmtime(filepath)))
    except Exception as e:
        print(f"❌ Error reading log directory: {e}")
        return
    
    if not log_files:
        print(f"⚠️  No Airpay callback log files found in {log_dir}")
        print(f"\nThis means no callbacks have been received yet.")
        return
    
    # Sort by modification time (most recent first)
    log_files.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n📁 Found {len(log_files)} callback log file(s):")
    for filepath, mtime in log_files:
        mod_time = datetime.fromtimestamp(mtime)
        print(f"  - {os.path.basename(filepath)} (Modified: {mod_time})")
    
    # Read the most recent log file
    most_recent_log = log_files[0][0]
    print(f"\n📖 Reading most recent log: {os.path.basename(most_recent_log)}")
    print("=" * 100)
    
    try:
        with open(most_recent_log, 'r') as f:
            content = f.read()
            
            if not content.strip():
                print("⚠️  Log file is empty - no callbacks received yet")
                return
            
            # Split by separator
            entries = content.split("=" * 100)
            
            # Filter out empty entries
            entries = [e.strip() for e in entries if e.strip()]
            
            print(f"\n📊 Total callback entries: {len(entries)}")
            
            # Show last 5 entries
            num_to_show = min(5, len(entries))
            print(f"\n🔍 Showing last {num_to_show} callback(s):")
            
            for i, entry in enumerate(entries[-num_to_show:], 1):
                print(f"\n{'─'*100}")
                print(f"CALLBACK #{i}")
                print(f"{'─'*100}")
                print(entry)
                
    except Exception as e:
        print(f"❌ Error reading log file: {e}")

def check_server_logs():
    """Check systemd journal logs for Airpay callbacks"""
    
    print(f"\n{'='*100}")
    print("SYSTEMD JOURNAL LOGS (Last 2 hours)")
    print("=" * 100)
    
    print("\n🔍 Searching for Airpay callback entries in systemd logs...")
    print("(This may take a moment...)\n")
    
    import subprocess
    
    try:
        # Search for Airpay callback logs in the last 2 hours
        cmd = [
            'sudo', 'journalctl', '-u', 'moneyone-backend',
            '--since', '2 hours ago',
            '--no-pager'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ Error running journalctl: {result.stderr}")
            return
        
        # Filter for Airpay-related lines
        lines = result.stdout.split('\n')
        airpay_lines = [line for line in lines if 'airpay' in line.lower() or 'Airpay' in line]
        
        if not airpay_lines:
            print("⚠️  No Airpay-related entries found in the last 2 hours")
            return
        
        print(f"📊 Found {len(airpay_lines)} Airpay-related log entries")
        print(f"\n🔍 Showing last 20 entries:\n")
        
        for line in airpay_lines[-20:]:
            print(line)
            
    except subprocess.TimeoutExpired:
        print("⏱️  Command timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_database_transactions():
    """Check database for Airpay transactions and their status"""
    
    print(f"\n{'='*100}")
    print("DATABASE TRANSACTIONS")
    print("=" * 100)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent Airpay transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    payment_mode,
                    callback_url,
                    created_at,
                    updated_at,
                    completed_at
                FROM payin_transactions
                WHERE pg_partner = 'Airpay'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("⚠️  No Airpay transactions found in database")
                return
            
            print(f"\n📊 Found {len(transactions)} recent Airpay transaction(s):\n")
            
            for idx, txn in enumerate(transactions, 1):
                print(f"{'─'*100}")
                print(f"TRANSACTION #{idx}")
                print(f"{'─'*100}")
                print(f"Transaction ID: {txn['txn_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Merchant ID: {txn['merchant_id']}")
                print(f"Amount: ₹{txn['amount']}")
                print(f"Net Amount: ₹{txn['net_amount']}")
                print(f"Charge: ₹{txn['charge_amount']}")
                print(f"Status: {txn['status']}")
                print(f"PG Txn ID: {txn['pg_txn_id']}")
                print(f"Bank Ref/UTR: {txn['bank_ref_no']}")
                print(f"Payment Mode: {txn['payment_mode']}")
                print(f"Callback URL: {txn['callback_url']}")
                print(f"Created: {txn['created_at']}")
                print(f"Updated: {txn['updated_at']}")
                print(f"Completed: {txn['completed_at']}")
                
                # Check if callback was received
                if txn['created_at'] != txn['updated_at']:
                    time_diff = txn['updated_at'] - txn['created_at']
                    print(f"\n✅ Transaction was updated (callback likely received)")
                    print(f"   Time difference: {time_diff}")
                else:
                    print(f"\n⚠️  Transaction not updated (no callback received yet)")
                
                # Check wallet transactions
                cursor.execute("""
                    SELECT 
                        wallet_txn_id,
                        txn_type,
                        amount,
                        balance_after,
                        description,
                        created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (txn['txn_id'],))
                
                wallet_txns = cursor.fetchall()
                
                if wallet_txns:
                    print(f"\n💰 Wallet Transactions:")
                    for wtxn in wallet_txns:
                        print(f"  - {wtxn['txn_type']}: ₹{wtxn['amount']} (Balance: ₹{wtxn['balance_after']})")
                        print(f"    {wtxn['description']}")
                else:
                    print(f"\n⚠️  No wallet transactions (wallet not credited)")
                
                print()
    
    finally:
        conn.close()

def check_callback_endpoint_status():
    """Check if the callback endpoint is accessible"""
    
    print(f"\n{'='*100}")
    print("CALLBACK ENDPOINT STATUS")
    print("=" * 100)
    
    callback_url = "https://api.moneyone.co.in/api/callback/airpay/payin"
    
    print(f"\n🌐 Callback URL: {callback_url}")
    print(f"\nChecking if endpoint is accessible...")
    
    import requests
    
    try:
        # Try to access the endpoint (should return 400 or 405 for GET)
        response = requests.get(callback_url, timeout=10)
        
        print(f"\n✅ Endpoint is accessible!")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
        if response.status_code == 405:
            print(f"\n✓ Endpoint correctly rejects GET requests (expects POST)")
        
    except requests.exceptions.SSLError as e:
        print(f"\n⚠️  SSL Error: {e}")
        print(f"   The endpoint may have SSL certificate issues")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print(f"   The endpoint is not accessible")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def main():
    """Main function to check all callback sources"""
    
    print("=" * 100)
    print("AIRPAY CALLBACK DIAGNOSTIC TOOL")
    print("=" * 100)
    print(f"\nChecking callbacks received at: https://api.moneyone.co.in/api/callback/airpay/payin")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check 1: Callback log files
    check_callback_log_files()
    
    # Check 2: Database transactions
    check_database_transactions()
    
    # Check 3: Server logs
    check_server_logs()
    
    # Check 4: Endpoint accessibility
    check_callback_endpoint_status()
    
    # Summary
    print(f"\n{'='*100}")
    print("SUMMARY")
    print("=" * 100)
    print(f"""
📋 What was checked:
  1. Callback log files in /var/www/moneyone/moneyone/backend/logs/
  2. Database transactions (payin_transactions table)
  3. Systemd journal logs (last 2 hours)
  4. Callback endpoint accessibility

🔍 How to interpret results:
  - If log files exist with entries → Callbacks were received
  - If transactions show updated_at != created_at → Callback processed
  - If wallet transactions exist → Payment was successful and credited
  - If no logs/updates → No callbacks received yet from Airpay

💡 Next steps if no callbacks:
  1. Make a test payment using the QR code
  2. Wait 60 seconds for auto status check
  3. Check if Airpay domain is whitelisted
  4. Contact Airpay support to verify callback configuration

📞 Airpay Support:
  - Email: support@airpay.co.in
  - Merchant ID: 354479
  - Callback URL: https://api.moneyone.co.in/api/callback/airpay/payin
""")
    print("=" * 100)

if __name__ == '__main__':
    main()
