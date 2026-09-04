import requests
import json

# Test the callback endpoint with sample Mudrape data
callback_url = "http://localhost:5000/api/callback/mudrape/payout"

# Sample callback data from Mudrape (based on the response you shared)
callback_data = {
    "success": True,
    "status": "SUCCESS",
    "source": "API",
    "utr": "e86c6ac3d7a4c141e9d707c352148803",
    "data": {
        "clientTxnId": "ADMIN20260222121840D2DF44",
        "payoutReferenceId": "ADMIN20260222121840D2DF44",
        "amount": 1,
        "charges": 7,
        "tax": 1.26,
        "adjustment": 0,
        "commission": 0,
        "closing": 383.51,
        "tds": 0,
        "channel": "IMPS",
        "processedAt": "2026-02-22T06:51:35.952Z",
        "createdAt": "2026-02-22T06:48:47.300Z",
        "errorMessage": None,
        "clientTransactionId": "ADMIN20260222121840D2DF44",
        "bankRefNo": "605312540116",
        "account": "003521711678324",
        "ifsc": "JIOP0000001",
        "name": "Soham Karmakar",
        "mobile": 7376582857,
        "email": "grosmartventuresdl@gmail.com",
        "paymentMode": "IMPS",
        "txnId": "NIFI64299004482696",
        "transactionDate": "2026-02-22T12:18:45.000Z"
    },
    "deduction": {
        "amount": 0,
        "charges": 7,
        "tax": 1.26,
        "adjustment": 0,
        "commission": 0,
        "closing": 383.51,
        "tds": 0
    },
    "statusCode": 10000,
    "message": "ACPT",
    "uniqueId": "e86c6ac3d7a4c141e9d707c352148803",
    "timestamp": "2026-02-22T12:21:34+05:30",
    "environment": "production",
    "apiTxnId": "ADMIN20260222121840D2DF44",
    "payoutStatus": "SUCCESS"
}

print("=" * 80)
print("Testing Mudrape Payout Callback")
print("=" * 80)
print(f"URL: {callback_url}")
print(f"Payload: {json.dumps(callback_data, indent=2)}")
print("=" * 80)

try:
    response = requests.post(
        callback_url,
        json=callback_data,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        print("\n✓ Callback processed successfully!")
    else:
        print("\n✗ Callback failed!")
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
