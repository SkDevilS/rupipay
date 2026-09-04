#!/usr/bin/env python3
"""
Script to send failure callbacks for FAILED transactions
"""

import sys
import argparse
import requests
from datetime import datetime
from database import get_db_connection

def send_callbacks(merchant_id, callback_url, start_time, end_time, dry_run=True):
    """
    Send failure callbacks for FAILED transactions
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT 
                pt.id,
                pt.merchant_id,
                pt.order_id,
                pt.pg_txn_id,
                pt.amount,
                pt.status,
                pt.created_at,
                pt.updated_at
            FROM payin_transactions pt
            WHERE pt.merchant_id = %s
            AND pt.status = 'FAILED'
            AND pt.created_at BETWEEN %s AND %s
            ORDER BY pt.created_at DESC
        """
        
        cursor.execute(query, (merchant_id, start_time, end_time))
        transactions = cursor.fetchall()
        
        if not transactions:
            print(f"No FAILED transactions found for merchant {merchant_id}")
            return
        
        print(f"\n{'='*100}")
        print(f"Found {len(transactions)} FAILED transaction(s)")
        print(f"Callback URL: {callback_url}")
        print(f"{'='*100}\n")
        
        if dry_run:
            print("[DRY RUN MODE] Showing first 5 transactions that would receive callbacks:\n")
            for txn in transactions[:5]:
                print(f"Order ID: {txn['order_id']} | Amount: ₹{txn['amount']} | Created: {txn['created_at']}")
            print(f"\n... and {len(transactions) - 5} more" if len(transactions) > 5 else "")
            print("\nUse --execute to send callbacks")
            return
        
        # Confirm before proceeding
        confirm = input(f"\nSend failure callbacks for {len(transactions)} transaction(s)? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return
        
        # Send callbacks
        success_count = 0
        failed_count = 0
        
        for i, txn in enumerate(transactions, 1):
            callback_payload = {
                'order_id': txn['order_id'],
                'pg_order_id': txn['pg_txn_id'],
                'amount': float(txn['amount']),
                'status': 'FAILURE',
                'message': 'PAYMENT NOT RECEIVED',
                'merchant_id': txn['merchant_id']
            }
            
            try:
                response = requests.post(
                    callback_url,
                    json=callback_payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    success_count += 1
                    if i % 100 == 0:
                        print(f"Progress: {i}/{len(transactions)} callbacks sent...")
                else:
                    failed_count += 1
                    print(f"✗ Failed for {txn['order_id']}: HTTP {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                failed_count += 1
                print(f"✗ Error for {txn['order_id']}: {str(e)}")
        
        print(f"\n{'='*100}")
        print(f"Summary:")
        print(f"  Total transactions: {len(transactions)}")
        print(f"  Callbacks sent successfully: {success_count}")
        print(f"  Callbacks failed: {failed_count}")
        print(f"{'='*100}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Send failure callbacks for FAILED transactions'
    )
    parser.add_argument('--merchant', required=True, help='Merchant ID')
    parser.add_argument('--callback-url', required=True, help='Callback URL')
    parser.add_argument('--start', required=True, help='Start time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', required=True, help='End time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--execute', action='store_true', help='Execute the callbacks (default is dry-run)')
    
    args = parser.parse_args()
    
    # Validate datetime format
    try:
        datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        print("Error: Invalid datetime format. Use YYYY-MM-DD HH:MM:SS")
        sys.exit(1)
    
    dry_run = not args.execute
    
    if dry_run:
        print("\n" + "="*100)
        print("RUNNING IN DRY-RUN MODE - No callbacks will be sent")
        print("="*100 + "\n")
    
    send_callbacks(
        merchant_id=args.merchant,
        callback_url=args.callback_url,
        start_time=args.start,
        end_time=args.end,
        dry_run=dry_run
    )


if __name__ == '__main__':
    main()
