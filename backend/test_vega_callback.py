"""
Test script for Vega callback functionality via Mudrape callback endpoint
Tests that Vega transactions are properly handled by the Mudrape callback system
"""

import requests
import json
from datetime import datetime

def test_vega_callback_via_mudrape():
    """Test Vega callback via Mudrape callback endpoint with actual Vega format"""
    
    print("=" * 80)
    print("Testing Vega Callback via Mudrape Endpoint (Vega Format)")
    print("=" * 80)
    
    # Test callback URL (same as configured with Vega team)
    callback_url = "http://localhost:5000/api/callback/mudrape/payin"
    
    # Sample callback data in Vega format (as provided by Vega team)
    test_callback_data = {
        "referenceId": "TRACK-1710000000000-ABCDEFG",  # This should match a Vega transaction order_id
        "orderId": "VEGA_ORDER_123456",
        "status": "SUCCESS",
        "amount": 1,
        "message": "Payment successful",
        "timestamp": "2026-03-10T09:25:44.418Z"
    }
    
    print(f"Callback URL: {callback_url}")
    print(f"Test Data (Vega Format): {json.dumps(test_callback_data, indent=2)}")
    print("\nNote: This tests Vega callbacks in the exact format Vega team will send")
    print("The system will detect it's a Vega format and process accordingly")
    
    try:
        # Send test callback
        response = requests.post(
            callback_url,
            json=test_callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Vega callback (Vega format) via Mudrape endpoint is working!")
        else:
            print(f"\n❌ Callback failed with status: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection failed - make sure the backend server is running")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def test_mudrape_callback_format():
    """Test that regular Mudrape callbacks still work"""
    
    print("\n" + "=" * 80)
    print("Testing Regular Mudrape Callback Format (Ensure No Regression)")
    print("=" * 80)
    
    callback_url = "http://localhost:5000/api/callback/mudrape/payin"
    
    # Sample Mudrape callback data (existing format)
    test_callback_data = {
        "ref_id": "MUDRAPE-REF-123456",
        "txn_id": "MUDRAPE_TXN_123456",
        "status": "SUCCESS",
        "amount": 100.00,
        "utr": "UTR123456789",
        "source": "Mudrape",
        "payeeVpa": "test@paytm",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"Test Data (Mudrape Format): {json.dumps(test_callback_data, indent=2)}")
    print("\nNote: This ensures existing Mudrape callbacks still work")
    
    try:
        response = requests.post(
            callback_url,
            json=test_callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Mudrape callback format still working!")
        else:
            print(f"\n❌ Mudrape callback failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

def test_vega_callback_with_form_data():
    """Test Vega callback with form data format via Mudrape endpoint"""
    
    print("\n" + "=" * 80)
    print("Testing Vega Callback with Form Data via Mudrape Endpoint")
    print("=" * 80)
    
    callback_url = "http://localhost:5000/api/callback/mudrape/payin"
    
    # Sample form data in Vega format
    form_data = {
        "referenceId": "TRACK-1710000000000-ABCDEFG",
        "orderId": "VEGA_ORDER_123456",
        "status": "SUCCESS",
        "amount": "1",
        "message": "Payment successful",
        "timestamp": "2026-03-10T09:25:44.418Z"
    }
    
    print(f"Form Data (Vega Format): {form_data}")
    
    try:
        response = requests.post(
            callback_url,
            data=form_data,
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Vega form data callback via Mudrape endpoint is working!")
        else:
            print(f"\n❌ Form data callback failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

def create_test_vega_transaction():
    """Create a test Vega transaction for callback testing"""
    
    print("\n" + "=" * 80)
    print("Creating Test Vega Transaction")
    print("=" * 80)
    
    try:
        from database import get_db_connection
        
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return None
            
        with conn.cursor() as cursor:
            # Create a test Vega transaction
            test_track_id = "TRACK-1710000000000-ABCDEFG"
            test_txn_id = f"VEGA_TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            cursor.execute("""
                INSERT INTO payin_transactions (
                    txn_id, merchant_id, order_id, amount, charge_amount, 
                    charge_type, net_amount, payee_name, payee_email, 
                    payee_mobile, product_info, status, pg_partner,
                    pg_txn_id, callback_url, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """, (
                test_txn_id, '9000000001', test_track_id, 100.00,
                2.00, 'FIXED', 98.00,
                'Test User', 'test@example.com', '9876543210',
                'Test Payment', 'INITIATED', 'Vega', 'VEGA_ORDER_123456',
                'https://merchant.example.com/callback'
            ))
            
            conn.commit()
            
            print(f"✅ Test Vega transaction created:")
            print(f"   TXN ID: {test_txn_id}")
            print(f"   Track ID: {test_track_id}")
            print(f"   PG Partner: Vega")
            print(f"   Status: INITIATED")
            
            return test_track_id
            
    except Exception as e:
        print(f"❌ Error creating test transaction: {e}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # First create a test transaction
    track_id = create_test_vega_transaction()
    
    if track_id:
        print(f"\nNow you can test callbacks using track_id: {track_id}")
        
        # Test the Vega callback format
        test_vega_callback_via_mudrape()
        test_vega_callback_with_form_data()
        
        # Test that Mudrape callbacks still work (regression test)
        test_mudrape_callback_format()
    else:
        print("❌ Could not create test transaction - skipping callback tests")