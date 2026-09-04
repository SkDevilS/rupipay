#!/usr/bin/env python3
"""
Test Airpay callback processing with real callback data
"""

import requests
import json

# The actual encrypted callback you received
encrypted_callback = {
    "merchant_id": "354479",
    "response": "3517178c795d0e691iUiWoUG62VlcOVhEAmXqp/G/1PMhB8q+CofaKLuYHL7o8vB0KKg6jGDGYwXKrcjA38+GPkbcbWDl0BgUJha+nCJC/yqtcbuecqrybCFymBEv892oa/4fgjwvGyqNyp4KCqXi+YOOXkxrDlHchxY5eVRF0cx1c5xHvpU/A9ua+7k3YrTXGmViHijJ5UdOWxcsDuAw2q5jAzGEyyNNTgJUT4f8KE1+f6ItDv116i3IgbGEieUnKnN/5bUIDh+ktk3HFl81uZrH9GNh3OKvlvbiFs4KoXNh10PTQ710VwK7ldTw0gwWFx4iouYwNpwCm6ZOv9/ug1Ee8QkkMVZDGn2eT2wsB0PWGg7n4tMxbx7RRtReX7K3y9EbyCX1UkugahmRx339idL8rBInA6dtv+oz3BJfS2k6rjxpyiyzcaOi6TWuMLdvz+A8sQp8EmPVEc62PKCq7R3n4X4SLrxD+hp10QceWW7dnC9z4KOA+sz6m5m857TERaTAjQ/YhLcBxj1S5Qn1GCUJl4coJrgSDiWkOnbaOz8mEjtp1ZbPjVrdk4zyb+wiO4coad2TTR0UVX4fUGOOUpoj/Uvw4f9FiRj1WY9ekclwKUsk/0SKQpqGDkWXMfcstWK7xtHkNdWwvLcZPNleieqz5tlvIEr0IXXIDQ+j/18NoSBo2plieeYuLLi4vGz+vFhAgbftZP+u6MNu147iU9dbLhJhy+FM4V8v7JOfnb6HZBzqL+43ucPmXbPnRIFfomdOjkRgUA3iU8SqZDSc15nuihRpR5tO8hNx3JfwIHf82Xxvg50ACu501Kq5CkFCmkooVaxHLW9u7dt6rqjuZHZAf40ofDswtaRFssa7IL8YEkZsm1ulYmFfRZR0lV/S14L8Pz4OJfExUTgIh6Mfe6ttExDzdZq3QFid2cUso7EUcKZ4QNjpqNc3jIuTJ3+15BJQrvNsJNI93wedP1kIkXVBuomO5HrJsgNVkT41nHfabPg9o5ePcsfWfHPLcrwbfkpYYfWQPaYF9MUdmJoYWKG3XXVtPko4yuteldfOvJSJWwRGV7+vysvynnKdwDj25JyIZ3mI5UBUJFg00q9iFc84XDJoImrcoIEymHhTtrEoxoZmyJXWz7BVoDb2DRPuKIR/vzKMO5rtqZMb5O2FGC6VikCU9QMzG9TfQ=="
}

print("=" * 100)
print("TESTING AIRPAY CALLBACK WITH REAL DATA")
print("=" * 100)
print()

# Test callback endpoint
callback_url = "http://localhost:5000/api/callback/airpay/payin"

print(f"Sending callback to: {callback_url}")
print(f"Callback data: {json.dumps(encrypted_callback, indent=2)}")
print()

try:
    response = requests.post(
        callback_url,
        json=encrypted_callback,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    print()
    
    if response.status_code == 200:
        print("✅ CALLBACK PROCESSED SUCCESSFULLY!")
        print()
        print("Expected outcomes:")
        print("  1. Transaction status updated to SUCCESS")
        print("  2. Merchant unsettled wallet credited")
        print("  3. Admin unsettled wallet credited")
        print("  4. Callback forwarded to: https://webhook.site/be77e8cb-44f8-45fb-83da-9cfd8b59a4ec")
    else:
        print("❌ CALLBACK PROCESSING FAILED")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 100)
print("Check backend logs for detailed processing information:")
print("  sudo journalctl -u moneyone-backend -f")
print("=" * 100)
