#!/usr/bin/env python3
"""
Process the Airpay callback that was already received
This will update the transaction and credit wallets
"""

from airpay_service import airpay_service
from database import get_db_connection
from wallet_service import wallet_service
import json

def process_callback():
    """Process the callback data that was received"""
    
    print("=" * 100)
    print("PROCESSING AIRPAY CALLBACK")
    print("=" * 100)
    
    # The encrypted response from the callback
    encrypted_response = "3517178c795d0e691iUiWoUG62VlcOVhEAmXqp/G/1PMhB8q+CofaKLuYHL7o8vB0KKg6jGDGYwXKrcjA38+GPkbcbWDl0BgUJha+nCJC/yqtcbuecqrybCFymBEv892oa/4fgjwvGyqNyp4KCqXi+YOOXkxrDlHchxY5eVRF0cx1c5xHvpU/A9ua+7k3YrTXGmViHijJ5UdOWxcsDuAw2q5jAzGEyyNNTgJUT4f8KE1+f6ItDv116i3IgbGEieUnKnN/5bUIDh+ktk3HFl81uZrH9GNh3OKvlvbiFs4KoXNh10PTQ710VwK7ldTw0gwWFx4iouYwNpwCm6ZOv9/ug1Ee8QkkMVZDGn2eT2wsB0PWGg7n4tMxbx7RRtReX7K3y9EbyCX1UkugahmRx339idL8rBInA6dtv+oz3BJfS2k6rjxpyiyzcaOi6TWuMLdvz+A8sQp8EmPVEc62PKCq7R3n4X4SLrxD+hp10QceWW7dnC9z4KOA+sz6m5m857TERaTAjQ/YhLcBxj1S5Qn1GCUJl4coJrgSDiWkOnbaOz8mEjtp1ZbPjVrdk4zyb+wiO4coad2TTR0UVX4fUGOOUpoj/Uvw4f9FiRj1WY9ekclwKUsk/0SKQpqGDkWXMfcstWK7xtHkNdWwvLcZPNleieqz5tlvIEr0IXXIDQ+j/18NoSBo2plieeYuLLi4vGz+vFhAgbftZP+u6MNu147iU9dbLhJhy+FM4V8v7JOfnb6HZBzqL+43ucPmXbPnRIFfomdOjkRgUA3iU8SqZDSc15nuihRpR5tO8hNx3JfwIHf82Xxvg50ACu501Kq5CkFCmkooVaxHLW9u7dt6rqjuZHZAf40ofDswtaRFssa7IL8YEkZsm1ulYmFfRZR0lV/S14L8Pz4OJfExUTgIh6Mfe6ttExDzdZq3QFid2cUso7EUcKZ4QNjpqNc3jIuTJ3+15BJQrvNsJNI93wedP1kIkXVBuomO5HrJsgNVkT41nHfabPg9o5ePcsfWfHPLcrwbfkpYYfWQPaYF9MUdmJoYWKG3XXVtPko4yuteldfOvJSJWwRGV7+vysvynnKdwDj25JyIZ3mI5UBUJFg00q9iFc84XDJoImrcoIEymHhTtrEoxoZmyJXWz7BVoDb2DRPuKIR/vzKMO5rtqZMb5O2FGC6VikCU9QMzG9TfQ=="
    
    # Decrypt
    print("\n🔓 Decrypting callback...")
    decrypted_data = airpay_service.decrypt_data(encrypted_response)
    
    if not decrypted_data:
        print("❌ Decryption failed")
        return
    
    print("✅ Decryption successful")
    
    # Extract callback data
    if 'data' in decrypted_data:
        callback_data = decrypted_data['data']
    else:
        callback_data = decrypted_data
    
    # Extract fields
    orderid = callback_data.get('orderid')
    ap_transactionid = callback_data.get('ap_transactionid')
    transaction_status = callback_data.get('transaction_status')
    amount = callback_data.get('amount')
    rrn = callback_data.get('rrn')
    chmod = callback_data.get('chmod', 'upi')
    customer_vpa = callback_data.get('customer_vpa')
    
    print(f"\n📋 Callback Data:")
    print(f"  Order ID: {orderid}")
    print(f"  Airpay Txn ID: {ap_transactionid}")
    print(f"  Transaction Status: {transaction_status}")
    print(f"  Amount: ₹{amount}")
    print(f"  RRN/UTR: {rrn}")
    print(f"  Payment Channel: {chmod}")
    print(f"  Customer VPA: {customer_vpa}")
    
    # Map status
    if transaction_status == 200:
        new_status = 'SUCCESS'
    elif transaction_status in [400, 401, 402, 403, 405]:
        new_status = 'FAILED'
    elif transaction_status == 211:
        new_status = 'PROCESSING'
    else:
        new_status = 'PENDING'
    
    print(f"\n📊 Mapped Status: {new_status}")
    
    # Find transaction in database
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find transaction by order_id
            cursor.execute("""
                SELECT txn_id, merchant_id, order_id, amount, net_amount, charge_amount, status, callback_url
                FROM payin_transactions
                WHERE order_id = %s AND pg_partner = 'Airpay'
                ORDER BY created_at DESC
                LIMIT 1
            """, (orderid,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"\n❌ Transaction not found for order_id: {orderid}")
                return
            
            print(f"\n✅ Found transaction: {txn['txn_id']}")
            print(f"   Current Status: {txn['status']}")
            print(f"   Merchant ID: {txn['merchant_id']}")
            print(f"   Amount: ₹{txn['amount']}")
            print(f"   Net Amount: ₹{txn['net_amount']}")
            print(f"   Charge: ₹{txn['charge_amount']}")
            
            # Update transaction
            if txn['status'] != new_status:
                print(f"\n🔄 Updating transaction status from {txn['status']} to {new_status}...")
                
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
                
                print(f"✅ Transaction updated successfully")
                
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
                        wallet_result = wallet_service.credit_unsettled_wallet(
                            merchant_id=txn['merchant_id'],
                            amount=float(txn['net_amount']),
                            description=f"PayIn received (Airpay callback) - {orderid}",
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
                            description=f"PayIn charge (Airpay callback) - {orderid}",
                            reference_id=txn['txn_id']
                        )
                        
                        if admin_wallet_result['success']:
                            print(f"✅ Admin wallet credited: ₹{txn['charge_amount']}")
                        else:
                            print(f"❌ Failed to credit admin wallet: {admin_wallet_result.get('message')}")
                    else:
                        print(f"\n⚠️  Wallet already credited - skipping")
                
                conn.commit()
                print(f"\n✅ All changes committed to database")
            else:
                print(f"\n✓ Status unchanged ({txn['status']}), no update needed")
    
    finally:
        conn.close()
    
    print(f"\n{'='*100}")
    print("PROCESSING COMPLETE")
    print(f"{'='*100}")

if __name__ == '__main__':
    process_callback()
