"""
Script to manually trigger callbacks for payin transactions
Useful for resending callbacks that failed or were missed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import requests
import json
from datetime import datetime

def send_callback(txn_id=None, order_id=None, callback_url=None):
    """
    Manually send callback for a transaction
    
    Args:
        txn_id: Transaction ID (optional if order_id provided)
        order_id: Order ID (optional if txn_id provided)
        callback_url: Override callback URL (optional, will use transaction's URL if not provided)
    """
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Find transaction
            if txn_id:
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE txn_id = %s
                """, (txn_id,))
            elif order_id:
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE order_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order_id,))
            else:
                print("ERROR: Either txn_id or order_id must be provided")
                return False
            
            txn = cursor.fetchone()
            
            if not txn:
                print("ERROR: Transaction not found")
                return False
            
            print("=" * 80)
            print("Transaction Details:")
            print("=" * 80)
            print(f"TXN ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Merchant ID: {txn['merchant_id']}")
            print(f"Amount: {txn['amount']}")
            print(f"Status: {txn['status']}")
            print(f"PG Partner: {txn.get('pg_partner', 'PayU')}")
            print(f"PG TXN ID: {txn.get('pg_txn_id')}")
            print(f"UTR/Bank Ref: {txn.get('bank_ref_no')}")
            print(f"Transaction Callback URL: {txn.get('callback_url')}")
            
            # Determine callback URL
            target_url = callback_url or txn.get('callback_url')
            
            # If no callback URL in transaction, check merchant_callbacks table
            if not target_url:
                cursor.execute("""
                    SELECT payin_callback_url FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (txn['merchant_id'],))
                
                merchant_callback = cursor.fetchone()
                target_url = merchant_callback.get('payin_callback_url') if merchant_callback else None
            
            if not target_url:
                print("\nERROR: No callback URL found")
                print("  - Not in transaction record")
                print("  - Not in merchant_callbacks table")
                print("  - Not provided as parameter")
                return False
            
            print(f"\nTarget Callback URL: {target_url}")
            
            # Prepare callback payload
            callback_data = {
                'txn_id': txn['txn_id'],
                'order_id': txn['order_id'],
                'status': txn['status'],
                'amount': float(txn['amount']),
                'utr': txn.get('bank_ref_no'),
                'pg_txn_id': txn.get('pg_txn_id'),
                'pg_partner': txn.get('pg_partner', 'PayU'),
                'payment_mode': txn.get('payment_mode'),
                'timestamp': datetime.now().isoformat()
            }
            
            print("\n" + "=" * 80)
            print("Callback Payload:")
            print("=" * 80)
            print(json.dumps(callback_data, indent=2))
            
            # Send callback
            print("\n" + "=" * 80)
            print("Sending Callback...")
            print("=" * 80)
            
            try:
                response = requests.post(
                    target_url,
                    json=callback_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                print(f"Response Status: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print(f"Response Body: {response.text[:500]}")
                
                # Log callback attempt
                cursor.execute("""
                    INSERT INTO callback_logs 
                    (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    txn['merchant_id'],
                    txn['txn_id'],
                    target_url,
                    json.dumps(callback_data),
                    response.status_code,
                    response.text[:1000]
                ))
                conn.commit()
                
                print("\n✓ Callback sent successfully and logged")
                return True
                
            except requests.exceptions.RequestException as e:
                print(f"\n✗ ERROR: Failed to send callback: {e}")
                
                # Log failed callback attempt
                cursor.execute("""
                    INSERT INTO callback_logs 
                    (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    txn['merchant_id'],
                    txn['txn_id'],
                    target_url,
                    json.dumps(callback_data),
                    0,
                    str(e)[:1000]
                ))
                conn.commit()
                
                return False
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def send_bulk_callbacks(merchant_id=None, status='SUCCESS', limit=10):
    """
    Send callbacks for multiple transactions
    
    Args:
        merchant_id: Filter by merchant ID (optional)
        status: Filter by status (default: SUCCESS)
        limit: Maximum number of transactions to process
    """
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find transactions
            query = """
                SELECT txn_id, order_id, merchant_id, status, callback_url
                FROM payin_transactions
                WHERE status = %s
            """
            params = [status]
            
            if merchant_id:
                query += " AND merchant_id = %s"
                params.append(merchant_id)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            
            if not transactions:
                print("No transactions found")
                return
            
            print(f"Found {len(transactions)} transactions")
            print("=" * 80)
            
            success_count = 0
            failed_count = 0
            
            for txn in transactions:
                print(f"\nProcessing: {txn['txn_id']}")
                
                if send_callback(txn_id=txn['txn_id']):
                    success_count += 1
                else:
                    failed_count += 1
                
                print("-" * 80)
            
            print("\n" + "=" * 80)
            print(f"Bulk callback completed!")
            print(f"  Success: {success_count}")
            print(f"  Failed: {failed_count}")
            print(f"  Total: {len(transactions)}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Manually trigger payin callbacks')
    parser.add_argument('--txn-id', help='Transaction ID')
    parser.add_argument('--order-id', help='Order ID')
    parser.add_argument('--callback-url', help='Override callback URL')
    parser.add_argument('--merchant-id', help='Merchant ID (for bulk mode)')
    parser.add_argument('--bulk', action='store_true', help='Bulk mode - send callbacks for multiple transactions')
    parser.add_argument('--status', default='SUCCESS', help='Status filter for bulk mode (default: SUCCESS)')
    parser.add_argument('--limit', type=int, default=10, help='Limit for bulk mode (default: 10)')
    
    args = parser.parse_args()
    
    if args.bulk:
        print("Running in BULK mode")
        print("=" * 80)
        send_bulk_callbacks(
            merchant_id=args.merchant_id,
            status=args.status,
            limit=args.limit
        )
    else:
        if not args.txn_id and not args.order_id:
            print("ERROR: Either --txn-id or --order-id must be provided")
            parser.print_help()
            sys.exit(1)
        
        send_callback(
            txn_id=args.txn_id,
            order_id=args.order_id,
            callback_url=args.callback_url
        )
