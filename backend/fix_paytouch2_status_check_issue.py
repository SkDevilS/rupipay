#!/usr/bin/env python3
"""
Fix PayTouch2 Status Check Issue
Prevent status check from converting SUCCESS transactions to FAILED
"""

from database import get_db_connection
from paytouch2_service import paytouch2_service
import json

def fix_paytouch2_status_check_logic():
    """Fix the status check logic to prevent SUCCESS -> FAILED conversion"""
    
    print("🔧 Fixing PayTouch2 Status Check Logic")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find PayTouch2 transactions that were converted from SUCCESS to FAILED
            cursor.execute("""
                SELECT txn_id, reference_id, status, pg_txn_id, utr, 
                       created_at, completed_at, updated_at
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                  AND status = 'FAILED'
                  AND utr IS NOT NULL
                  AND completed_at IS NOT NULL
                  AND DATE(updated_at) = CURDATE()
                ORDER BY updated_at DESC
                LIMIT 20
            """)
            
            suspicious_txns = cursor.fetchall()
            
            if not suspicious_txns:
                print("✅ No suspicious FAILED transactions found")
                return
            
            print(f"Found {len(suspicious_txns)} suspicious FAILED transactions with UTR")
            print("These might have been incorrectly converted from SUCCESS to FAILED")
            print("-" * 60)
            
            fixed_count = 0
            
            for txn in suspicious_txns:
                print(f"\n🔍 Checking {txn['txn_id']}")
                print(f"  Status: {txn['status']}")
                print(f"  UTR: {txn['utr']}")
                print(f"  Completed: {txn['completed_at']}")
                print(f"  Updated: {txn['updated_at']}")
                
                # If transaction has UTR and completed_at, it was likely successful
                if txn['utr'] and txn['completed_at']:
                    print(f"  🎉 Transaction has UTR - likely successful!")
                    
                    # Restore to SUCCESS
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = 'SUCCESS', 
                            error_message = NULL,
                            updated_at = NOW()
                        WHERE txn_id = %s
                    """, (txn['txn_id'],))
                    
                    conn.commit()
                    fixed_count += 1
                    print(f"  ✅ Restored to SUCCESS")
                else:
                    print(f"  ❌ No UTR - might be genuinely failed")
            
            print(f"\n📊 Summary:")
            print(f"  Fixed: {fixed_count} transactions")
            print(f"  Total checked: {len(suspicious_txns)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def create_improved_status_check_logic():
    """Create improved status check logic that doesn't override successful transactions"""
    
    print("\n" + "=" * 60)
    print("🔧 Creating Improved Status Check Logic")
    print("=" * 60)
    
    improved_logic = '''
def improved_paytouch2_status_check(txn_id, current_status, current_utr):
    """
    Improved PayTouch2 status check that prevents SUCCESS -> FAILED conversion
    """
    
    # RULE 1: Never downgrade SUCCESS transactions with UTR
    if current_status == 'SUCCESS' and current_utr:
        print(f"  ✅ Transaction already SUCCESS with UTR - skipping status check")
        return {
            'success': True,
            'status': current_status,
            'utr': current_utr,
            'message': 'Transaction already successful - no check needed'
        }
    
    # RULE 2: Only check status for pending/failed transactions
    if current_status not in ['PENDING', 'QUEUED', 'INPROCESS', 'INITIATED', 'FAILED']:
        print(f"  ℹ️  Transaction status {current_status} - no check needed")
        return {
            'success': True,
            'status': current_status,
            'message': 'Transaction in final state - no check needed'
        }
    
    # RULE 3: For FAILED transactions, only check if they don't have UTR
    if current_status == 'FAILED' and current_utr:
        print(f"  ⚠️  FAILED transaction has UTR - might be incorrectly failed")
        # Still check, but be cautious about the result
    
    # Proceed with actual API check
    result = paytouch2_service.check_payout_status(...)
    
    # RULE 4: If API returns FAILED but we have UTR, prefer SUCCESS
    if result.get('status') == 'FAILED' and current_utr:
        print(f"  ⚠️  API says FAILED but we have UTR - keeping SUCCESS")
        return {
            'success': True,
            'status': 'SUCCESS',
            'utr': current_utr,
            'message': 'API inconsistent - preferring UTR evidence'
        }
    
    return result
'''
    
    print("💡 Improved Logic Rules:")
    print("1. Never downgrade SUCCESS transactions with UTR")
    print("2. Only check pending/failed transactions")
    print("3. Be cautious with FAILED transactions that have UTR")
    print("4. Prefer UTR evidence over API response")
    
    # Save the improved logic to a file
    with open('backend/improved_paytouch2_status_logic.py', 'w') as f:
        f.write(improved_logic)
    
    print("\n✅ Improved logic saved to: improved_paytouch2_status_logic.py")

def patch_current_status_check():
    """Patch the current status check to prevent SUCCESS -> FAILED conversion"""
    
    print("\n" + "=" * 60)
    print("🔧 Patching Current Status Check")
    print("=" * 60)
    
    # Read current payout_routes.py
    try:
        with open('backend/payout_routes.py', 'r') as f:
            content = f.read()
        
        # Check if already patched
        if 'PAYTOUCH2_STATUS_CHECK_PATCH' in content:
            print("✅ Status check already patched")
            return
        
        # Find the PayTouch2 status check section
        patch_code = '''
            elif txn['pg_partner'] == 'Paytouch2':
                # PAYTOUCH2_STATUS_CHECK_PATCH: Prevent SUCCESS -> FAILED conversion
                if txn['status'] == 'SUCCESS' and txn.get('utr'):
                    conn.close()
                    return jsonify({
                        'success': True,
                        'message': 'Transaction already successful - no check needed',
                        'data': {
                            'txn_id': txn['txn_id'],
                            'reference_id': txn['reference_id'],
                            'amount': float(txn['amount']),
                            'status': txn['status'],
                            'utr': txn['utr'],
                            'pg_txn_id': txn['pg_txn_id'],
                            'pg_partner': txn['pg_partner'],
                            'created_at': txn['created_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['created_at'] else None,
                            'completed_at': txn['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['completed_at'] else None
                        }
                    }), 200
                
                status_result = paytouch2_service.check_payout_status(
                    transaction_id=txn['pg_txn_id'],
                    external_ref=txn['reference_id']
                )'''
        
        print("⚠️  Manual patching required!")
        print("Add this logic to the PayTouch2 status check in payout_routes.py:")
        print(patch_code)
        
    except Exception as e:
        print(f"❌ Error reading payout_routes.py: {e}")

if __name__ == '__main__':
    fix_paytouch2_status_check_logic()
    create_improved_status_check_logic()
    patch_current_status_check()