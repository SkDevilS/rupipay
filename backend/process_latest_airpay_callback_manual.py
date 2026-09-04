#!/usr/bin/env python3
"""
Manually process the latest Airpay callback from the log file
"""

from airpay_service import airpay_service
from database import get_db_connection
from wallet_service import wallet_service
import json

# The latest encrypted callback from the log (19:00:46)
encrypted_response = "7cc36e46136b5906nC5VlVJQey3Jl7G/ZlwFsxhaBM7F+Z99zmTLZktN6dJ3lXZ80ZYLuwLaWuzCq1XJRhlHgVOQibY+NvOeB7crqQKBNjgKKXGZ2xNKqnn4wO7rFXbgh9zOeo+dczrRKZ1f86inyvSs/iuoBtIJWWM9N5OdXSkB2Qz+wUKC76QhmA+COrEaOJI5f8/wHIIBXExbtG5JYeIuMVZfmIN6McgCdSP3h++qNKJIqQ0sw4WRuxb2NXW7dHTEkrJ5Hx93aNjYTslbWVqCS2g76p/nttpB9TZNkJ6efB21nGWiBy9yU142wPWj2ZgL3HqwYCcYaAD29OCoPlHwhTb8ctUIqQL3QySMFsLcO7cCOVcN+W3cPwIkiNs+VFRWlbiYLT+uIZdOP4vXfVLWnOCeSaAln8EViKfvhK9osOPPIxRp2YrdilYCZfHHw3KgWGQME8aM6anDW9OOsBrBMeYplVq4kNiSsNAfA1lnIOAvf/vKyi7PjCaqRDld8JdO7JAVPpQTimoDuqGlI7bMCfLi++HwiagKOPpCeU83jbvFAZx0WSdt+/oAWITeytcFaDCfS6udZdnAHgLWi/16nYWv32awwdeZxQqIQfaOd3cStmxz/1e/PaY3Vt/i+oXwwgxMSzGskjmfHBi9dN6xCNgkvmuOx/ytOJCYo63w65bX33pqdz9aqR9+RzbA0gPZrZkm59aahGV3G9Sq0eKr3WqeMiViS2iAvBnUcwIDnRVmrfymrnl5SHeI4f1u4xRt38R/JKRJL1jZ/SUsYu4U6NPviWmrFS0oACnyPpsMXqHokE0E0njlTDm6242mp8Sdmc7pz0G9CS8J/8l+mZo6/brNuEQiZfrm5zo9nPCz52nUOoB5QsFobikunqGcCcNUCAeqcArnqgu6QdoUZsWIwCdEGOR9yLwdtbBSHC/iRv0bTgsJNxbUqmdG3PdufgPDbWhwt/21s4nNVUmt2m5ez5m5lLi6K2fvOVifGW5r0ZwcBkGbedqNag4Mx9hzIBdPQGavacPDHdpbNhGANSfdBrbWD5hxk2z+haMcG4CPYCnuH8UCZOwFX7cVdXFbVw2MOzyF5PymVXQ8xU7L4zRHWB04tzUyYRMwYBCPKKUe3hSegKZEc6AW0owNulx56v7FMh12mI65k+kKdiaKbG9LgsxZDwXdUsJwcA=="

print("=" * 100)
print("MANUALLY PROCESSING LATEST AIRPAY CALLBACK")
print("=" * 100)
print()

# Decrypt
print("🔓 Decrypting callback...")
decrypted_data = airpay_service.decrypt_data(encrypted_response)

if not decrypted_data:
    print("❌ Decryption failed")
    exit(1)

print("✅ Decryption successful")
print()

# Extract callback data
if 'data' in decrypted_data and isinstance(decrypted_data['data'], dict):
    callback_data = decrypted_data['data']
else:
    callback_data = decrypted_data

print(f"Decrypted data: {json.dumps(callback_data, indent=2)}")
print()

# Extract fields
orderid = callback_data.get('orderid')
ap_transactionid = callback_data.get('ap_transactionid')
transaction_status = callback_data.get('transaction_status')
amount = callback_data.get('amount')
rrn = callback_data.get('rrn')
chmod = callback_data.get('chmod', 'upi')
customvar = callback_data.get('customvar', '')

print(f"Order ID: {orderid}")
print(f"Airpay Txn ID: {ap_transactionid}")
print(f"Transaction Status: {transaction_status}")
print(f"Amount: ₹{amount}")
print(f"RRN/UTR: {rrn}")
print(f"Payment Channel: {chmod}")
print(f"Custom Var: {customvar}")
print()

# Map status
if transaction_status == 200:
    new_status = 'SUCCESS'
elif transaction_status in [400, 401, 402, 403, 405]:
    new_status = 'FAILED'
elif transaction_status == 211:
    new_status = 'PROCESSING'
else:
    new_status = 'INITIATED'

print(f"Mapped Status: {new_status}")
print()

# Find transaction in database
conn = get_db_connection()
if not conn:
    print("❌ Database connection failed")
    exit(1)

try:
    with conn.cursor() as cursor:
        # Find transaction by order_id
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
            exit(1)
        
        print(f"✅ Found transaction: {txn['txn_id']}")
        print(f"   Current Status: {txn['status']}")
        print(f"   Merchant ID: {txn['merchant_id']}")
        print(f"   Amount: ₹{txn['amount']}")
        print(f"   Net Amount: ₹{txn['net_amount']}")
        print(f"   Charge: ₹{txn['charge_amount']}")
        print()
        
        # Update transaction
        print(f"🔄 Updating transaction status to {new_status}...")
        
        payment_mode = chmod.upper() if chmod else 'UPI'
        
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
            """, (new_status, ap_transactionid, rrn, payment_mode, txn['txn_id']))
        else:
            cursor.execute("""
                UPDATE payin_transactions
                SET status = %s,
                    pg_txn_id = %s,
                    bank_ref_no = %s,
                    payment_mode = %s,
                    updated_at = NOW()
                WHERE txn_id = %s
            """, (new_status, ap_transactionid, rrn, payment_mode, txn['txn_id']))
        
        print(f"✅ Transaction updated successfully")
        print()
        
        # If successful, credit wallets
        if new_status == 'SUCCESS':
            # Check if wallet already credited
            cursor.execute("""
                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
            """, (txn['txn_id'],))
            
            wallet_already_credited = cursor.fetchone()['count'] > 0
            
            if not wallet_already_credited:
                print(f"💰 Crediting wallets...")
                
                # Credit merchant unsettled wallet
                wallet_result = wallet_service.credit_unsettled_wallet(
                    merchant_id=txn['merchant_id'],
                    amount=float(txn['net_amount']),
                    description=f"Airpay Payin - {orderid}",
                    reference_id=txn['txn_id']
                )
                
                if wallet_result['success']:
                    print(f"✅ Merchant wallet credited: ₹{txn['net_amount']}")
                else:
                    print(f"❌ Failed to credit merchant wallet: {wallet_result.get('message')}")
                
                # Credit admin unsettled wallet
                admin_wallet_result = wallet_service.credit_admin_unsettled_wallet(
                    admin_id='admin',
                    amount=float(txn['charge_amount']),
                    description=f"Airpay Payin charge - {orderid}",
                    reference_id=txn['txn_id']
                )
                
                if admin_wallet_result['success']:
                    print(f"✅ Admin wallet credited: ₹{txn['charge_amount']}")
                else:
                    print(f"❌ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
            else:
                print(f"⚠️  Wallet already credited - skipping")
        
        conn.commit()
        print()
        print(f"✅ All changes committed to database")
        print()
        
        # Extract callback URL from customvar
        merchant_callback_url = None
        if customvar and 'callback_url=' in customvar:
            try:
                parts = customvar.split('|')
                for part in parts:
                    if part.startswith('callback_url='):
                        merchant_callback_url = part.split('callback_url=', 1)[1]
                        print(f"✓ Extracted callback URL: {merchant_callback_url}")
                        break
            except Exception as e:
                print(f"ERROR parsing customvar: {e}")
        
        if merchant_callback_url:
            print(f"📞 Forwarding callback to merchant...")
            import requests
            from datetime import datetime
            
            merchant_callback_data = {
                'txn_id': txn['txn_id'],
                'order_id': orderid,
                'status': new_status,
                'amount': str(txn['amount']),
                'net_amount': str(txn['net_amount']),
                'charge_amount': str(txn['charge_amount']),
                'utr': rrn,
                'pg_txn_id': ap_transactionid,
                'payment_mode': payment_mode,
                'pg_partner': 'Airpay',
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                response = requests.post(
                    merchant_callback_url,
                    json=merchant_callback_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                print(f"✅ Merchant callback sent: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            except Exception as e:
                print(f"❌ Failed to send merchant callback: {e}")
        else:
            print(f"⚠️  No callback URL found in customvar")

finally:
    conn.close()

print()
print("=" * 100)
print("PROCESSING COMPLETE")
print("=" * 100)
