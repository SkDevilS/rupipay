#!/usr/bin/env python3
"""
Manually process the latest Airpay callback from logs
"""

import pymysql
import json
import os
import requests
from datetime import datetime
from config import DB_CONFIG
from airpay_service import airpay_service

def process_latest_callback():
    """Process the latest Airpay callback from log file"""
    
    print("=" * 100)
    print("MANUALLY PROCESSING LATEST AIRPAY CALLBACK")
    print("=" * 100)
    
    # Read the latest callback from log file
    log_file = f'/var/www/moneyone/moneyone/backend/logs/airpay_callbacks_{datetime.now().strftime("%Y%m%d")}.log'
    
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return
    
    # Read the log file and extract the latest callback
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Find the last FORM DATA section
    sections = content.split('=' * 100)
    if len(sections) < 2:
        print("❌ No callback data found in log file")
        return
    
    # Get the last section
    last_section = sections[-2]
    
    # Extract form data
    form_data = {}
    in_form_section = False
    
    for line in last_section.split('\n'):
        if 'FORM DATA:' in line:
            in_form_section = True
            continue
        if in_form_section and ':' in line:
            if line.strip().startswith('JSON DATA:') or line.strip().startswith('RAW DATA:'):
                break
            parts = line.strip().split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                form_data[key] = value
    
    if not form_data:
        print("❌ No form data found in log")
        return
    
    print(f"📋 Found callback data with {len(form_data)} fields")
    
    # Check if encrypted
    if 'response' in form_data and 'merchant_id' in form_data:
        print(f"🔓 Decrypting callback...")
        encrypted_response = form_data.get('response')
        
        # Decrypt
        decrypted_data = airpay_service.decrypt_data(encrypted_response)
        
        if not decrypted_data:
            print("❌ Decryption failed")
            return
        
        print(f"✅ Decryption successful")
        print(f"Decrypted data: {json.dumps(decrypted_data, indent=2)}")
        
        # Extract transaction data
        if 'data' in decrypted_data and isinstance(decrypted_data['data'], dict):
            callback_data = decrypted_data['data']
        else:
            callback_data = decrypted_data
    else:
        callback_data = form_data
    
    # Extract fields
    orderid = callback_data.get('orderid')
    ap_transactionid = callback_data.get('ap_transactionid')
    transaction_status = callback_data.get('transaction_status')
    amount = callback_data.get('amount')
    rrn = callback_data.get('rrn') or callback_data.get('utr_no') or callback_data.get('bank_ref_no')
    chmod = callback_data.get('chmod', 'upi')
    customvar = callback_data.get('customvar', '')
    
    print(f"Order ID: {orderid}")
    print(f"Airpay Txn ID: {ap_transactionid}")
    print(f"Transaction Status: {transaction_status}")
    print(f"Amount: ₹{amount}")
    print(f"RRN/UTR: {rrn}")
    print(f"Payment Channel: {chmod}")
    print(f"Custom Var: {customvar}")
    
    # Map status
    if transaction_status == 200:
        new_status = 'SUCCESS'
    elif transaction_status == 211:
        new_status = 'PROCESSING'
    elif transaction_status in [400, 401, 402, 403, 405]:
        new_status = 'FAILED'
    else:
        new_status = 'INITIATED'
    
    print(f"Mapped Status: {new_status}")
    
    # Find transaction in database
    conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT txn_id, merchant_id, order_id, amount, net_amount, charge_amount, status
                FROM payin_transactions
                WHERE order_id = %s AND pg_partner = 'Airpay'
                ORDER BY created_at DESC
                LIMIT 1
            """, (orderid,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction not found for order_id: {orderid}")
                return
            
            print(f"\n✅ Found transaction: {txn['txn_id']}, Current Status: {txn['status']}")
            
            # Update transaction
            if new_status in ['SUCCESS', 'FAILED']:
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = %s,
                        pg_txn_id = %s,
                        bank_ref_no = %s,
                        payment_mode = %s,
                        completed_at = NOW(),
                        updated_at = NOW()
                    WHERE txn_id = %s
                """, (new_status, ap_transactionid, rrn, chmod.upper(), txn['txn_id']))
            else:
                cursor.execute("""
                    UPDATE payin_transactions
                    SET status = %s,
                        pg_txn_id = %s,
                        bank_ref_no = %s,
                        payment_mode = %s,
                        updated_at = NOW()
                    WHERE txn_id = %s
                """, (new_status, ap_transactionid, rrn, chmod.upper(), txn['txn_id']))
            
            print(f"✅ Updated transaction status to {new_status}")
            
            # If successful, credit wallets
            if new_status == 'SUCCESS':
                # Check if wallet already credited
                cursor.execute("""
                    SELECT COUNT(*) as count FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (txn['txn_id'],))
                
                wallet_already_credited = cursor.fetchone()['count'] > 0
                
                if not wallet_already_credited:
                    print(f"\n💰 Crediting wallets...")
                    
                    # Credit merchant unsettled wallet
                    from wallet_service import wallet_service as wallet_svc
                    wallet_result = wallet_svc.credit_unsettled_wallet(
                        merchant_id=txn['merchant_id'],
                        amount=float(txn['net_amount']),
                        description=f"Airpay Payin credited to unsettled wallet - {orderid}",
                        reference_id=txn['txn_id']
                    )
                    
                    if wallet_result['success']:
                        print(f"✅ Merchant unsettled wallet credited: ₹{txn['net_amount']}")
                    else:
                        print(f"❌ Failed to credit merchant wallet: {wallet_result.get('message')}")
                    
                    # Credit admin unsettled wallet
                    admin_wallet_result = wallet_svc.credit_admin_unsettled_wallet(
                        admin_id='admin',
                        amount=float(txn['charge_amount']),
                        description=f"Airpay Payin charge - {orderid}",
                        reference_id=txn['txn_id']
                    )
                    
                    if admin_wallet_result['success']:
                        print(f"✅ Admin unsettled wallet credited: ₹{txn['charge_amount']}")
                    else:
                        print(f"❌ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                else:
                    print(f"\n⚠️  Wallet already credited - skipping")
            
            conn.commit()
            
            # Forward callback to merchant
            print(f"\n📞 Forwarding callback to merchant...")
            
            # Extract callback URL from customvar
            merchant_callback_url = None
            
            if customvar and 'callback_url=' in customvar:
                try:
                    parts = customvar.split('|')
                    for part in parts:
                        if part.startswith('callback_url='):
                            merchant_callback_url = part.split('callback_url=', 1)[1]
                            print(f"✅ Extracted callback URL: {merchant_callback_url}")
                            break
                except Exception as e:
                    print(f"❌ Error parsing customvar: {e}")
            
            if not merchant_callback_url:
                # Try to get from merchant_callbacks table
                cursor.execute("""
                    SELECT payin_callback_url
                    FROM merchant_callbacks
                    WHERE merchant_id = %s
                """, (txn['merchant_id'],))
                
                callback_config = cursor.fetchone()
                if callback_config and callback_config['payin_callback_url']:
                    merchant_callback_url = callback_config['payin_callback_url']
                    print(f"✅ Got callback URL from merchant_callbacks table: {merchant_callback_url}")
            
            if not merchant_callback_url:
                print(f"⚠️  No callback URL found")
                return
            
            # Prepare callback payload
            merchant_callback_data = {
                'txn_id': txn['txn_id'],
                'order_id': orderid,
                'status': new_status,
                'amount': str(txn['amount']),
                'net_amount': str(txn['net_amount']),
                'charge_amount': str(txn['charge_amount']),
                'utr': rrn,
                'pg_txn_id': ap_transactionid,
                'payment_mode': chmod.upper(),
                'pg_partner': 'Airpay',
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n📤 Sending callback to: {merchant_callback_url}")
            print(f"Payload: {json.dumps(merchant_callback_data, indent=2)}")
            
            try:
                callback_response = requests.post(
                    merchant_callback_url,
                    json=merchant_callback_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                print(f"\n✅ Callback sent successfully")
                print(f"Response Code: {callback_response.status_code}")
                print(f"Response: {callback_response.text[:500]}")
                
                # Log callback
                cursor.execute("""
                    INSERT INTO callback_logs 
                    (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    txn['merchant_id'],
                    txn['txn_id'],
                    merchant_callback_url,
                    json.dumps(merchant_callback_data),
                    callback_response.status_code,
                    callback_response.text[:1000]
                ))
                conn.commit()
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Failed to send callback: {e}")
                
                # Log failed callback
                cursor.execute("""
                    INSERT INTO callback_logs 
                    (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    txn['merchant_id'],
                    txn['txn_id'],
                    merchant_callback_url,
                    json.dumps(merchant_callback_data),
                    0,
                    str(e)[:1000]
                ))
                conn.commit()
            
            print("\n" + "=" * 100)
            print("PROCESSING COMPLETE")
            print("=" * 100)
            
    finally:
        conn.close()

if __name__ == '__main__':
    process_latest_callback()
