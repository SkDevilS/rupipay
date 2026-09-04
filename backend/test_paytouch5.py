import sys
import os
import time

# Ensure we can import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from paytouch5_coco_service import paytouch5_service
from config import Config

def run_test():
    print(f"Testing Paytouch5_Coco Service...")
    print(f"Using Base URL: {Config.PAYTOUCH5_COCO_BASE_URL}")
    print(f"Token present: {'Yes' if Config.PAYTOUCH5_COCO_TOKEN and Config.PAYTOUCH5_COCO_TOKEN != 'COCO_TOKEN_FROM_PAYTOUCH_DASHBOARD' else 'No (Using default/placeholder)'}")
    print("-" * 50)
    
    # Generate a unique reference ID for testing
    timestamp = str(int(time.time()))
    test_ref_id = f"TEST_{timestamp}"
    
    # Dummy payout data
    payout_data = {
        'reference_id': test_ref_id,
        'amount': 100.00,  # ₹1.00 test amount
        'bene_name': 'Test User',
        'bene_account': '003521711678324',
        'bene_ifsc': 'JIOP0000001',
        'bank_name': 'Test Bank',
        'payment_mode': 'IMPS',
        'narration': 'Test Payout'
    }
    
    print(f"Initiating payout with reference ID: {test_ref_id}")
    
    # Testing as an admin payout to bypass merchant wallet deductions
    # Change 'admin@paysetu.shop' to a valid admin ID from your database if needed
    admin_id = 'admin@paysetu.shop'
    
    try:
        # Call the initiate_payout method directly
        result = paytouch5_service.initiate_payout(
            merchant_id=None,
            payout_data=payout_data,
            admin_id=admin_id
        )
        
        print("\n=== Result ===")
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        
        if result.get('success'):
            print(f"Transaction ID: {result.get('txn_id')}")
            print(f"Gateway Txn ID: {result.get('paytouch5_txn_id')}")
            print(f"Status: {result.get('status')}")
            
            print("\nNow testing status check...")
            # Wait a few seconds before checking status
            time.sleep(2)
            
            status_result = paytouch5_service.check_payout_status(
                transaction_id=result.get('paytouch5_txn_id'),
                external_ref=test_ref_id
            )
            
            print("\n=== Status Check Result ===")
            print(f"Success: {status_result.get('success')}")
            print(f"Status: {status_result.get('status')}")
            print(f"Message: {status_result.get('message')}")
            if status_result.get('utr'):
                print(f"UTR: {status_result.get('utr')}")
                
        else:
            print("\n⚠️ Payout Initiation Failed.")
            print("Please check your .env credentials (PAYTOUCH5_COCO_BASE_URL, PAYTOUCH5_COCO_TOKEN)")
            print("and ensure they are correctly set.")
            
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")

if __name__ == "__main__":
    # Ensure you are running this from the backend directory
    # Run with: python test_paytouch5.py
    run_test()
