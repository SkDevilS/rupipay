#!/usr/bin/env python3
"""
Check the specific ViyonaPay transaction details
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json

def check_viyona_transaction():
    """Check the ViyonaPay transaction details"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("\n" + "="*80)
            print("  VIYONAPAY TRANSACTION DETAILS")
            print("="*80)
            
            # Get the ViyonaPay transaction
            cursor.execute("""
                SELECT *
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            txn = cursor.fetchone()
            
            if not txn:
                print("\n❌ No ViyonaPay transaction found")
                return
            
            print(f"\n✅ Found ViyonaPay Transaction:\n")
            for key, value in txn.items():
                print(f"  {key:20} : {value}")
            
            print("\n" + "="*80)
            print("  CALLBACK ENDPOINT INFORMATION")
            print("="*80)
            print("\nViyonaPay should send callback to:")
            print("  POST https://your-domain.com/api/callback/viyonapay/payin")
            print("\nWith headers:")
            print("  X-SIGNATURE: <signature>")
            print("  X-TIMESTAMP: <timestamp>")
            print("  X-Request-Id: <request_id>")
            print("  Content-Type: application/json")
            
            print("\n" + "="*80)
            print("  NEXT STEPS")
            print("="*80)
            print("\n1. Check Docker logs for callback:")
            print("   docker logs moneyone-backend-1 --tail 200 | grep -i viyona")
            print("\n2. Check if callback endpoint is accessible:")
            print("   curl -X POST https://your-domain.com/api/callback/viyonapay/payin \\")
            print("        -H 'Content-Type: application/json' \\")
            print("        -d '{\"test\": \"data\"}'")
            print("\n3. Contact ViyonaPay support to:")
            print("   - Verify callback URL is registered")
            print("   - Check if they're sending callbacks")
            print("   - Get sample callback payload")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_viyona_transaction()
    print("\n" + "="*80)
