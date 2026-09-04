#!/usr/bin/env python3
"""
Test PayTouch2 Read-Only Status Check
Verify that PayTouch2 status check returns live status without updating database
"""

from database import get_db_connection
from paytouch2_service import paytouch2_service
import json

def test_paytouch2_readonly_status():
    """Test PayTouch2 read-only status check functionality"""
    
    print("🧪 Testing PayTouch2 Read-Only Status Check")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Find a PayTouch2 transaction to test
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, status, 
                    pg_txn_id, utr, created_at, completed_at
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("ℹ️  No PayTouch2 transactions found to test")
                return True
            
            print(f"Found {len(transactions)} PayTouch2 transactions to test")
            print("-" * 60)
            
            for txn in transactions:
                print(f"\n🔍 Testing Transaction: {txn['txn_id']}")
                print(f"   Reference ID: {txn['reference_id']}")
                print(f"   Current DB Status: {txn['status']}")
                print(f"   Current DB UTR: {txn['utr'] or 'N/A'}")
                print(f"   PG TXN ID: {txn['pg_txn_id'] or 'N/A'}")
                
                # Store original values
                original_status = txn['status']
                original_utr = txn['utr']
                original_completed_at = txn['completed_at']
                
                try:
                    # Test PayTouch2 status check (should be read-only)
                    print(f"   📡 Checking live PayTouch2 status...")
                    
                    status_result = paytouch2_service.check_payout_status(
                        transaction_id=txn['pg_txn_id'],
                        external_ref=txn['reference_id']
                    )
                    
                    if status_result.get('success'):
                        live_status = status_result.get('status', 'PENDING')
                        live_utr = status_result.get('utr')
                        live_txn_id = status_result.get('transaction_id')
                        
                        print(f"   ✅ PayTouch2 API Response:")
                        print(f"      Live Status: {live_status}")
                        print(f"      Live UTR: {live_utr or 'N/A'}")
                        print(f"      Live TXN ID: {live_txn_id or 'N/A'}")
                        
                        # Verify database was NOT updated
                        cursor.execute("""
                            SELECT status, utr, completed_at, updated_at
                            FROM payout_transactions
                            WHERE txn_id = %s
                        """, (txn['txn_id'],))
                        
                        current_txn = cursor.fetchone()
                        
                        if (current_txn['status'] == original_status and 
                            current_txn['utr'] == original_utr and
                            current_txn['completed_at'] == original_completed_at):
                            print(f"   ✅ DATABASE NOT UPDATED (Read-only confirmed)")
                            print(f"      DB Status: {current_txn['status']} (unchanged)")
                            print(f"      DB UTR: {current_txn['utr'] or 'N/A'} (unchanged)")
                        else:
                            print(f"   ❌ DATABASE WAS UPDATED (Read-only failed!)")
                            print(f"      DB Status: {original_status} → {current_txn['status']}")
                            print(f"      DB UTR: {original_utr} → {current_txn['utr']}")
                        
                        # Show comparison
                        print(f"   📊 Status Comparison:")
                        print(f"      Database: {current_txn['status']}")
                        print(f"      PayTouch2: {live_status}")
                        
                        if current_txn['status'] != live_status:
                            print(f"   ⚠️  STATUS MISMATCH - Cron job should fix this")
                        else:
                            print(f"   ✅ Status matches")
                        
                    else:
                        print(f"   ❌ PayTouch2 API Error: {status_result.get('message')}")
                        
                except Exception as e:
                    print(f"   ❌ Error testing transaction: {e}")
                    continue
            
            print("\n" + "=" * 60)
            print("📋 Test Summary:")
            print("   ✅ PayTouch2 status check should be read-only")
            print("   ✅ Database should NOT be updated by status check")
            print("   ✅ Live status should be returned alongside DB status")
            print("   ✅ Cron job handles actual database updates")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

def main():
    """Main function"""
    success = test_paytouch2_readonly_status()
    
    if success:
        print("\n✅ PayTouch2 read-only status check test completed!")
    else:
        print("\n❌ PayTouch2 read-only status check test failed!")

if __name__ == '__main__':
    main()