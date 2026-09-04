"""
Test TourQuest Status Check API
Tests the status check functionality for TourQuest payments
"""

import requests
import json
from config import Config

def test_tourquest_status_check(clientrefno):
    """
    Test TourQuest status check API
    
    Args:
        clientrefno: The client reference number to check
    """
    print("=" * 80)
    print("Testing TourQuest Status Check API")
    print("=" * 80)
    
    # Prepare request
    api_payload = {
        "secret_key": Config.TOURQUEST_SECRET_KEY,
        "salt_key": Config.TOURQUEST_SALT_KEY,
        "clientrefno": clientrefno,
        "txntype": "status"
    }
    
    print(f"\nRequest URL: {Config.TOURQUEST_BASE_URL}/api/version/upi/apicall")
    print(f"Request Payload:")
    print(json.dumps(api_payload, indent=2))
    
    try:
        # Make API call
        response = requests.post(
            f"{Config.TOURQUEST_BASE_URL}/api/version/upi/apicall",
            json=api_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nResponse Body:")
        
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
            
            # Parse response
            if response_json.get('statuscode') == 200:
                data = response_json.get('data', {})
                print("\n" + "=" * 80)
                print("Status Check Result:")
                print("=" * 80)
                print(f"Status: {data.get('status', 'UNKNOWN')}")
                print(f"Transaction ID: {data.get('txnid', 'N/A')}")
                print(f"UTR: {data.get('utr', 'N/A')}")
                print(f"Amount: {data.get('amount', 'N/A')}")
                print(f"Message: {response_json.get('message', 'N/A')}")
                print("=" * 80)
            else:
                print("\n" + "=" * 80)
                print("Status Check Failed")
                print("=" * 80)
                print(f"Status Code: {response_json.get('statuscode')}")
                print(f"Message: {response_json.get('message', 'Unknown error')}")
                print("=" * 80)
                
        except json.JSONDecodeError:
            print(response.text)
            print("\nERROR: Response is not valid JSON")
            
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: API request failed")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def test_from_database():
    """Test status check for recent TourQuest transactions from database"""
    from database import get_db_connection
    
    print("\n" + "=" * 80)
    print("Testing Status Check for Recent TourQuest Transactions")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get recent TourQuest transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    pg_txn_id as clientrefno,
                    amount,
                    status,
                    created_at
                FROM payin_transactions
                WHERE pg_partner = 'Tourquest'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\nNo TourQuest transactions found in database")
                return
            
            print(f"\nFound {len(transactions)} recent TourQuest transactions:")
            print("-" * 80)
            
            for txn in transactions:
                print(f"\nTransaction ID: {txn['txn_id']}")
                print(f"Order ID: {txn['order_id']}")
                print(f"Client Ref No: {txn['clientrefno']}")
                print(f"Amount: {txn['amount']}")
                print(f"Current Status: {txn['status']}")
                print(f"Created: {txn['created_at']}")
                print("-" * 80)
            
            # Test status check for the most recent transaction
            if transactions:
                latest_txn = transactions[0]
                print(f"\nTesting status check for latest transaction:")
                print(f"Client Ref No: {latest_txn['clientrefno']}")
                print("")
                test_tourquest_status_check(latest_txn['clientrefno'])
                
    finally:
        conn.close()


if __name__ == '__main__':
    import sys
    
    print("\nTourQuest Status Check Test")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        # Test with provided clientrefno
        clientrefno = sys.argv[1]
        print(f"Testing with provided clientrefno: {clientrefno}")
        test_tourquest_status_check(clientrefno)
    else:
        # Test with recent transactions from database
        print("No clientrefno provided, testing with recent transactions from database")
        test_from_database()
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)
