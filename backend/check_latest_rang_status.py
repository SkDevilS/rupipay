#!/usr/bin/env python3
"""
Quick check of the latest Rang transaction status
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from rang_service import RangService
from datetime import datetime
import json

def get_latest_rang_transaction():
    """Get the most recent Rang transaction"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                txn_id, merchant_id, order_id, amount, status, 
                bank_ref_no, pg_txn_id, callback_url,
                created_at, completed_at
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        transaction = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return transaction
        
    except Exception as e:
        print(f"❌ Error getting transaction: {e}")
        return None

def main():
    print("LATEST RANG TRANSACTION STATUS CHECK")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get latest transaction
    transaction = get_latest_rang_transaction()
    
    if not transaction:
        print("❌ No Rang transactions found")
        return
    
    print("📋 TRANSACTION DETAILS:")
    print(f"  TXN ID: {transaction['txn_id']}")
    print(f"  Order ID: {transaction['order_id']}")
    print(f"  Merchant: {transaction['merchant_id']}")
    print(f"  Amount: ₹{transaction['amount']}")
    print(f"  Status: {transaction['status']}")
    print(f"  UTR: {transaction['bank_ref_no'] or 'None'}")
    print(f"  Created: {transaction['created_at']}")
    print(f"  Completed: {transaction['completed_at'] or 'None'}")
    
    # Check with Rang API
    print(f"\n🔍 CHECKING WITH RANG API...")
    print(f"RefID: {transaction['order_id']}")
    
    try:
        rang_service = RangService()
        result = rang_service.check_payment_status(transaction['order_id'])
        
        if result['success']:
            rang_data = result['data']
            print(f"\n✅ RANG API RESPONSE:")
            print(f"{json.dumps(rang_data, indent=2)}")
            
            # Extract key information
            if isinstance(rang_data, dict):
                rang_status = rang_data.get('status', 'Unknown')
                rang_message = rang_data.get('message', '')
                rang_utr = rang_data.get('utr', rang_data.get('UTR', ''))
                
                print(f"\n📊 COMPARISON:")
                print(f"  Database Status: {transaction['status']}")
                print(f"  Rang Status: {rang_status}")
                print(f"  Database UTR: {transaction['bank_ref_no'] or 'None'}")
                print(f"  Rang UTR: {rang_utr or 'None'}")
                
                if str(transaction['status']).upper() == str(rang_status).upper():
                    print(f"\n✅ Status matches!")
                else:
                    print(f"\n⚠️ STATUS MISMATCH!")
                    print(f"   Database: {transaction['status']}")
                    print(f"   Rang: {rang_status}")
                    
                    if str(rang_status).upper() in ['SUCCESS', 'COMPLETED', 'PAID']:
                        print(f"\n💡 NEXT STEPS:")
                        print(f"   1. Transaction is SUCCESS on Rang")
                        print(f"   2. Check if callback was received")
                        print(f"   3. Verify callback processing")
                        print(f"   4. Consider manual status update")
                    elif str(rang_status).upper() in ['FAILED', 'CANCELLED']:
                        print(f"\n💡 NEXT STEPS:")
                        print(f"   1. Transaction FAILED on Rang")
                        print(f"   2. Update database status to FAILED")
        else:
            print(f"\n❌ RANG API ERROR:")
            print(f"   {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 60)

if __name__ == "__main__":
    main()