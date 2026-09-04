#!/usr/bin/env python3
"""
Script to mark initiated payin transactions as failed for a specific merchant
within a time range and send failure callbacks to their payin callback URL.

Usage:
    python markfailedpayincallback.py --merchant <merchant_id> --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS"
"""

import sys
import argparse
import requests
from datetime import datetime
from database import get_db_connection

def mark_payins_failed_and_callback(merchant_id, start_time, end_time, dry_run=True):
    """
    Mark initiated payins as failed and send failure callbacks
    
    Args:
        merchant_id: The merchant ID
        start_time: Start datetime string (YYYY-MM-DD HH:MM:SS)
        end_time: End datetime string (YYYY-MM-DD HH:MM:SS)
        dry_run: If True, only show what would be done without making changes
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Find all initiated transactions for the merchant in the time range
        query = """
            SELECT 
                pt.id,
                pt.merchant_id,
                pt.order_id,
                pt.pg_txn_id,
                pt.amount,
                pt.status,
                pt.created_at,
                pt.callback_url as txn_callback_url,
                mc.payin_callback_url as merchant_callback_url,
                m.full_name as merchant_name
            FROM payin_transactions pt
            JOIN merchants m ON pt.merchant_id = m.merchant_id
            LEFT JOIN merchant_callbacks mc ON pt.merchant_id = mc.merchant_id
            WHERE pt.merchant_id = %s
            AND pt.status = 'INITIATED'
            AND pt.created_at BETWEEN %s AND %s
            ORDER BY pt.created_at DESC
        """
        
        cursor.execute(query, (merchant_id, start_time, end_time))
        transactions = cursor.fetchall()
        
        if not transactions:
            print(f"No initiated transactions found for merchant {merchant_id} between {start_time} and {end_time}")
            return
        
        # Determine callback URL (transaction-level takes precedence over merchant-level)
        callback_url = transactions[0]['txn_callback_url'] or transactions[0]['merchant_callback_url']
        
        print(f"\nFound {len(transactions)} initiated transaction(s) for merchant {merchant_id}")
        print(f"Merchant Name: {transactions[0]['merchant_name']}")
        print(f"Callback URL: {callback_url or 'Not configured'}")
        print(f"\nTransactions to be marked as FAILED:")
        print("-" * 100)
        
        for txn in transactions:
            print(f"ID: {txn['id']} | Order ID: {txn['order_id']} | Amount: ₹{txn['amount']} | Created: {txn['created_at']}")
        
        print("-" * 100)
        
        if dry_run:
            print("\n[DRY RUN MODE] No changes made. Use --execute to apply changes.")
            return
        
        # Confirm before proceeding
        confirm = input(f"\nAre you sure you want to mark {len(transactions)} transaction(s) as FAILED? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return
        
        # Process each transaction
        success_count = 0
        callback_success_count = 0
        
        for txn in transactions:
            try:
                # Update transaction status to FAILED
                update_query = """
                    UPDATE payin_transactions 
                    SET status = 'FAILED',
                        updated_at = NOW()
                    WHERE id = %s
                """
                cursor.execute(update_query, (txn['id'],))
                conn.commit()
                success_count += 1
                
                print(f"\n✓ Marked transaction {txn['order_id']} as FAILED")
                
                # Determine callback URL (transaction-level takes precedence)
                callback_url = txn['txn_callback_url'] or txn['merchant_callback_url']
                
                # Send callback if callback URL exists
                if callback_url:
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
                            print(f"  ✓ Callback sent successfully to {callback_url}")
                            print(f"    Response: {response.text[:100]}")
                            callback_success_count += 1
                        else:
                            print(f"  ✗ Callback failed with status {response.status_code}")
                            print(f"    Response: {response.text[:100]}")
                    
                    except requests.exceptions.RequestException as e:
                        print(f"  ✗ Callback request failed: {str(e)}")
                else:
                    print(f"  ⚠ No callback URL configured for this merchant")
            
            except Exception as e:
                print(f"\n✗ Error processing transaction {txn['order_id']}: {str(e)}")
                conn.rollback()
        
        print(f"\n{'='*100}")
        print(f"Summary:")
        print(f"  Total transactions: {len(transactions)}")
        print(f"  Successfully marked as FAILED: {success_count}")
        print(f"  Callbacks sent successfully: {callback_success_count}")
        print(f"{'='*100}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Mark initiated payin transactions as failed and send failure callbacks'
    )
    parser.add_argument('--merchant', required=True, help='Merchant ID')
    parser.add_argument('--start', required=True, help='Start time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', required=True, help='End time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--execute', action='store_true', help='Execute the changes (default is dry-run)')
    
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
        print("RUNNING IN DRY-RUN MODE - No changes will be made")
        print("="*100 + "\n")
    
    mark_payins_failed_and_callback(
        merchant_id=args.merchant,
        start_time=args.start,
        end_time=args.end,
        dry_run=dry_run
    )


if __name__ == '__main__':
    main()
