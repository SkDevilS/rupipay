#!/usr/bin/env python3
"""
Decrypt Airpay Callback Data
Decrypts the encrypted callback received from Airpay
"""

from airpay_service import airpay_service
import json

def decrypt_callback():
    """Decrypt the callback data from the log"""
    
    print("=" * 100)
    print("AIRPAY CALLBACK DECRYPTION")
    print("=" * 100)
    
    # The encrypted response from the callback log
    encrypted_response = "3517178c795d0e691iUiWoUG62VlcOVhEAmXqp/G/1PMhB8q+CofaKLuYHL7o8vB0KKg6jGDGYwXKrcjA38+GPkbcbWDl0BgUJha+nCJC/yqtcbuecqrybCFymBEv892oa/4fgjwvGyqNyp4KCqXi+YOOXkxrDlHchxY5eVRF0cx1c5xHvpU/A9ua+7k3YrTXGmViHijJ5UdOWxcsDuAw2q5jAzGEyyNNTgJUT4f8KE1+f6ItDv116i3IgbGEieUnKnN/5bUIDh+ktk3HFl81uZrH9GNh3OKvlvbiFs4KoXNh10PTQ710VwK7ldTw0gwWFx4iouYwNpwCm6ZOv9/ug1Ee8QkkMVZDGn2eT2wsB0PWGg7n4tMxbx7RRtReX7K3y9EbyCX1UkugahmRx339idL8rBInA6dtv+oz3BJfS2k6rjxpyiyzcaOi6TWuMLdvz+A8sQp8EmPVEc62PKCq7R3n4X4SLrxD+hp10QceWW7dnC9z4KOA+sz6m5m857TERaTAjQ/YhLcBxj1S5Qn1GCUJl4coJrgSDiWkOnbaOz8mEjtp1ZbPjVrdk4zyb+wiO4coad2TTR0UVX4fUGOOUpoj/Uvw4f9FiRj1WY9ekclwKUsk/0SKQpqGDkWXMfcstWK7xtHkNdWwvLcZPNleieqz5tlvIEr0IXXIDQ+j/18NoSBo2plieeYuLLi4vGz+vFhAgbftZP+u6MNu147iU9dbLhJhy+FM4V8v7JOfnb6HZBzqL+43ucPmXbPnRIFfomdOjkRgUA3iU8SqZDSc15nuihRpR5tO8hNx3JfwIHf82Xxvg50ACu501Kq5CkFCmkooVaxHLW9u7dt6rqjuZHZAf40ofDswtaRFssa7IL8YEkZsm1ulYmFfRZR0lV/S14L8Pz4OJfExUTgIh6Mfe6ttExDzdZq3QFid2cUso7EUcKZ4QNjpqNc3jIuTJ3+15BJQrvNsJNI93wedP1kIkXVBuomO5HrJsgNVkT41nHfabPg9o5ePcsfWfHPLcrwbfkpYYfWQPaYF9MUdmJoYWKG3XXVtPko4yuteldfOvJSJWwRGV7+vysvynnKdwDj25JyIZ3mI5UBUJFg00q9iFc84XDJoImrcoIEymHhTtrEoxoZmyJXWz7BVoDb2DRPuKIR/vzKMO5rtqZMb5O2FGC6VikCU9QMzG9TfQ=="
    
    print(f"\n📦 Encrypted Response:")
    print(f"Length: {len(encrypted_response)} characters")
    print(f"Preview: {encrypted_response[:100]}...")
    
    print(f"\n🔓 Decrypting with Airpay service...")
    
    # Decrypt using airpay service
    decrypted_data = airpay_service.decrypt_data(encrypted_response)
    
    if not decrypted_data:
        print(f"\n❌ Decryption failed!")
        return
    
    print(f"\n✅ Decryption successful!")
    print(f"\n{'='*100}")
    print("DECRYPTED CALLBACK DATA")
    print(f"{'='*100}\n")
    
    # Pretty print the decrypted data
    print(json.dumps(decrypted_data, indent=2))
    
    # Extract key information
    print(f"\n{'='*100}")
    print("KEY INFORMATION")
    print(f"{'='*100}\n")
    
    if isinstance(decrypted_data, dict):
        # Check if it's the outer wrapper
        if 'data' in decrypted_data:
            data = decrypted_data.get('data', {})
        else:
            data = decrypted_data
        
        print(f"Status Code: {decrypted_data.get('status_code')}")
        print(f"Status: {decrypted_data.get('status')}")
        print(f"Message: {decrypted_data.get('message')}")
        
        if isinstance(data, dict):
            print(f"\nTransaction Details:")
            print(f"  Merchant ID: {data.get('merchant_id')}")
            print(f"  Order ID: {data.get('orderid')}")
            print(f"  Airpay Txn ID: {data.get('ap_transactionid')}")
            print(f"  Amount: ₹{data.get('amount')}")
            print(f"  Transaction Status: {data.get('transaction_status')}")
            print(f"  Payment Status: {data.get('transaction_payment_status')}")
            print(f"  Message: {data.get('message')}")
            print(f"  RRN/UTR: {data.get('rrn')}")
            print(f"  Payment Channel: {data.get('chmod')}")
            print(f"  Bank: {data.get('bank_name') or data.get('pgbank_name')}")
            print(f"  Customer VPA: {data.get('customer_vpa')}")
            print(f"  Customer Name: {data.get('customer_name')}")
            print(f"  Customer Email: {data.get('customer_email')}")
            print(f"  Customer Phone: {data.get('customer_phone')}")
    
    print(f"\n{'='*100}")
    print("ANALYSIS")
    print(f"{'='*100}\n")
    
    # Analyze the callback
    if isinstance(decrypted_data, dict):
        status_code = decrypted_data.get('status_code')
        
        if status_code == '200':
            print("✅ This is a SUCCESSFUL callback response")
            print("   The callback endpoint is working correctly")
        elif status_code == '400':
            print("⚠️  This is an ERROR response")
            print(f"   Error: {decrypted_data.get('message')}")
        else:
            print(f"ℹ️  Status Code: {status_code}")
        
        # Check if it's a callback or API response
        if 'data' in decrypted_data and isinstance(decrypted_data['data'], dict):
            data = decrypted_data['data']
            transaction_status = data.get('transaction_status')
            
            if transaction_status == 200:
                print("\n💰 PAYMENT SUCCESSFUL!")
                print("   Transaction completed successfully")
            elif transaction_status in [400, 401, 402, 403, 405]:
                print("\n❌ PAYMENT FAILED")
                print(f"   Status: {transaction_status}")
            elif transaction_status == 211:
                print("\n⏳ PAYMENT PROCESSING")
                print("   Transaction is still being processed")
            else:
                print(f"\nℹ️  Transaction Status: {transaction_status}")
    
    print(f"\n{'='*100}")

if __name__ == '__main__':
    decrypt_callback()
