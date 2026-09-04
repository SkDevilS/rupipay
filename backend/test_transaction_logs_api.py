#!/usr/bin/env python3
"""
Test transaction logs API to see what data is being returned
"""
import requests
import json

# Test with a real transaction ID
TXN_ID = "AIRPAY_9000000001_TRD341068C3A671BA_20260405150541"

# Get JWT token first (you'll need to login)
# For now, let's just test the endpoint structure

print("Testing Transaction Logs API")
print("=" * 60)
print(f"Transaction ID: {TXN_ID}")
print()

# You would need to add your JWT token here
# headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
# response = requests.get(f"http://localhost:5000/api/admin/transaction-logs/payin/{TXN_ID}", headers=headers)

print("Expected API Response Structure:")
print(json.dumps({
    "success": True,
    "logs": {
        "transaction_id": "TXN123",
        "merchant_id": "9000000001",
        "merchant_name": "Test Merchant",
        "status": "SUCCESS",
        "amount": 2028.00,
        "service_name": "AIRPAY",
        "created_at": "2026-04-05T15:05:41",
        
        "merchant_request": {
            "amount": 2028.00,
            "order_id": "ORD123",
            "payee_name": "John Doe",
            "payee_mobile": "9876543210",
            "payee_email": "john@example.com"
        },
        
        "gateway_request": {
            "amount": "2028.00",
            "merchantTransactionId": "TXN123"
        },
        
        "gateway_response": {
            "status": "SUCCESS",
            "transactionId": "PG_TXN_123"
        },
        
        "callback_from_gateway": {
            "status": "SUCCESS",
            "amount": "2028.00",
            "utr": "316177962947"
        },
        
        "callback_to_merchant": {
            "forwarded": False,
            "forwarded_at": None,
            "merchant_callback_url": "https://merchant.com/callback",
            "response": None,
            "payload_sent": {
                "txn_id": "TXN123",
                "order_id": "ORD123",
                "status": "SUCCESS",
                "amount": 2028.00,
                "utr": "316177962947",
                "pg_txn_id": "PG_TXN_123"
            }
        },
        
        "additional_info": {
            "pg_txn_id": "1861632151",
            "utr": "316177962947",
            "bank_ref_no": "316177962947",
            "payment_mode": "UPI",
            "error_message": None,
            "remarks": None
        }
    }
}, indent=2))
