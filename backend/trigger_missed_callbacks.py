#!/usr/bin/env python3
"""
Manually trigger callbacks for successful transactions that didn't receive them
"""

from database import get_db_connection
import requests
import json
from datetime import datetime

def trigger_missed_callbacks():
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed!")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find SUCCESS transactions without callback logs
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.order_id,
                    pt.amount,
                    pt.status,
                    pt.callback_url,
                    pt.bank_ref_no as utr,
                    pt.pg_txn_id,
                    pt.completed_at
                FROM payin_transactions pt
                WHERE pt.pg_partner = 'Mudrape'
                AND pt.status = 'SUCCESS'
                AND pt.callback_url IS NOT NULL
                AND pt.callback_url != ''
                AND NOT EXISTS (
                    SELECT 1 FROM callback_logs cl 
                    WHERE cl.txn_id = pt.txn_id
                )
                ORDER BY pt.completed_at DESC
            """)
            
            missed_txns = cursor.fetchall()
            
            if not missed_txns:
                print("✓ No missed callbacks found!")
                return
            
            print("=" * 80)
            print(f"Found {len(missed_txns)} transactions without callbacks")
            print("=" * 80)
            print()
            
            for txn in missed_txns:
                print(f"\nProcessing: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Amount: {txn['amount']}")
                print(f"  UTR: {txn['utr']}")
                print(f"  Callback URL: {txn['callback_url']}")
                
                # Prepare callback payload
                callback_data = {
                    'txn_id': txn['txn_id'],
                    'order_id': txn['order_id'],
                    'status': txn['status'],
                    'amount': float(txn['amount']),
                    'utr': txn['utr'],
                    'pg_txn_id': txn['pg_txn_id'],
                    'pg_partner': 'Mudrape',
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"  Sending callback...")
                
                try:
                    response = requests.post(
                        txn['callback_url'],
                        json=callback_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                    
                    print(f"  Response: {response.status_code}")
                    
                    # Log the callback attempt
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        txn['merchant_id'],
                        txn['txn_id'],
                        txn['callback_url'],
                        json.dumps(callback_data),
                        response.status_code,
                        response.text[:1000]
                    ))
                    
                    conn.commit()
                    
                    if response.status_code == 200:
                        print(f"  ✓ Callback sent successfully!")
                    else:
                        print(f"  ⚠ Callback sent but got non-200 response")
                        print(f"  Response: {response.text[:200]}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"  ❌ Failed to send callback: {e}")
                    
                    # Log failed attempt
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        txn['merchant_id'],
                        txn['txn_id'],
                        txn['callback_url'],
                        json.dumps(callback_data),
                        0,
                        str(e)[:1000]
                    ))
                    
                    conn.commit()
            
            print("\n" + "=" * 80)
            print("DONE")
            print("=" * 80)
            print(f"\nProcessed {len(missed_txns)} callbacks")
            print("\nRun check_recent_callbacks.py again to verify")
            
    finally:
        conn.close()

if __name__ == '__main__':
    trigger_missed_callbacks()
