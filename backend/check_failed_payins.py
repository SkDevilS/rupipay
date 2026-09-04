#!/usr/bin/env python3
"""
Script to check the status of payin transactions for a merchant within a time range.
Shows current status, when they were updated, and callback information.
"""

import sys
import argparse
from datetime import datetime
from database import get_db_connection

def check_payin_status(merchant_id, start_time, end_time):
    """
    Check payin transaction status for a merchant in a time range
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
                pt.updated_at,
                pt.callback_url as txn_callback_url,
                mc.payin_callback_url as merchant_callback_url,
                m.full_name as merchant_name
            FROM payin_transactions pt
            JOIN merchants m ON pt.merchant_id = m.merchant_id
            LEFT JOIN merchant_callbacks mc ON pt.merchant_id = mc.merchant_id
            WHERE pt.merchant_id = %s
            AND pt.created_at BETWEEN %s AND %s
            ORDER BY pt.created_at DESC
        """
        
        cursor.execute(query, (merchant_id, start_time, end_time))
        transactions = cursor.fetchall()
        
        if not transactions:
            print(f"No transactions found for merchant {merchant_id} between {start_time} and {end_time}")
            return
        
        # Count by status
        status_counts = {}
        for txn in transactions:
            status = txn['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        callback_url = transactions[0]['txn_callback_url'] or transactions[0]['merchant_callback_url']
        
        print(f"\n{'='*100}")
        print(f"Transaction Status Report for Merchant {merchant_id}")
        print(f"Merchant Name: {transactions[0]['merchant_name']}")
        print(f"Callback URL: {callback_url or 'Not configured'}")
        print(f"Time Range: {start_time} to {end_time}")
        print(f"{'='*100}\n")
        
        print("Status Summary:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count} transaction(s)")
        
        print(f"\n{'='*100}")
        print("Transaction Details:")
        print(f"{'='*100}\n")
        
        for txn in transactions:
            print(f"Order ID: {txn['order_id']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Status: {txn['status']}")
            print(f"  Created: {txn['created_at']}")
            print(f"  Updated: {txn['updated_at']}")
            print(f"  PG Txn ID: {txn['pg_txn_id'] or 'N/A'}")
            print()
        
        print(f"{'='*100}")
        print(f"Total: {len(transactions)} transaction(s)")
        print(f"{'='*100}\n")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Check payin transaction status for a merchant'
    )
    parser.add_argument('--merchant', required=True, help='Merchant ID')
    parser.add_argument('--start', required=True, help='Start time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', required=True, help='End time (YYYY-MM-DD HH:MM:SS)')
    
    args = parser.parse_args()
    
    # Validate datetime format
    try:
        datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        print("Error: Invalid datetime format. Use YYYY-MM-DD HH:MM:SS")
        sys.exit(1)
    
    check_payin_status(
        merchant_id=args.merchant,
        start_time=args.start,
        end_time=args.end
    )


if __name__ == '__main__':
    main()
