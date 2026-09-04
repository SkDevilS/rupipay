#!/usr/bin/env python3
"""
Check PayTouch2 Wallet Deduction System
Verifies that wallet deductions work correctly with PayTouch2 callbacks
"""

from database import get_db_connection
from datetime import datetime, timedelta
import json

def check_paytouch2_transactions():
    """Check PayTouch2 transaction status and wallet deductions"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("🔍 Checking PayTouch2 Transaction & Wallet System")
            print("=" * 60)
            
            # 1. Get all PayTouch2 transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    admin_id,
                    reference_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    pg_txn_id,
                    utr,
                    created_at,
                    completed_at,
                    error_message
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("ℹ️  No PayTouch2 transactions found")
                return True
            
            print(f"\n📊 PayTouch2 Transactions ({len(transactions)}):")
            print("-" * 120)
            print(f"{'TXN ID':<15} {'Type':<8} {'Amount':<8} {'Charges':<8} {'Status':<10} {'PG TXN ID':<15} {'UTR':<15} {'Created'}")
            print("-" * 120)
            
            admin_count = 0
            merchant_count = 0
            status_counts = {}
            
            for txn in transactions:
                # Determine transaction type
                if txn['admin_id']:
                    txn_type = "ADMIN"
                    admin_count += 1
                elif txn['merchant_id']:
                    txn_type = "MERCHANT"
                    merchant_count += 1
                else:
                    txn_type = "UNKNOWN"
                
                # Count statuses
                status = txn['status']
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Format display
                created_display = txn['created_at'].strftime('%m-%d %H:%M') if txn['created_at'] else 'N/A'
                pg_txn_display = (txn['pg_txn_id'][:15] if txn['pg_txn_id'] else 'N/A')
                utr_display = (txn['utr'][:15] if txn['utr'] else 'N/A')
                
                print(f"{txn['txn_id']:<15} {txn_type:<8} ₹{txn['amount']:<7} ₹{txn['charge_amount']:<7} {status:<10} {pg_txn_display:<15} {utr_display:<15} {created_display}")
            
            # Summary
            print(f"\n📈 Transaction Summary:")
            print(f"   - Admin Payouts: {admin_count}")
            print(f"   - Merchant Payouts: {merchant_count}")
            print(f"   - Status Distribution:")
            for status, count in status_counts.items():
                print(f"     • {status}: {count}")
            
            # 2. Check wallet deductions for merchant transactions
            print(f"\n💰 Wallet Deduction Analysis:")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.charge_amount,
                    pt.status,
                    pt.completed_at,
                    COUNT(mwt.id) as wallet_deduction_count,
                    SUM(CASE WHEN mwt.txn_type = 'DEBIT' THEN mwt.amount ELSE 0 END) as total_debited
                FROM payout_transactions pt
                LEFT JOIN merchant_wallet_transactions mwt ON mwt.reference_id = pt.txn_id
                WHERE pt.pg_partner = 'Paytouch2'
                AND pt.merchant_id IS NOT NULL
                GROUP BY pt.txn_id
                ORDER BY pt.created_at DESC
                LIMIT 10
            """)
            
            merchant_txns = cursor.fetchall()
            
            if merchant_txns:
                print(f"{'TXN ID':<15} {'Merchant':<12} {'Amount':<8} {'Charges':<8} {'Status':<10} {'Wallet Debits':<12} {'Debit Amount':<12} {'Match'}")
                print("-" * 120)
                
                correct_deductions = 0
                missing_deductions = 0
                incorrect_amounts = 0
                
                for txn in merchant_txns:
                    expected_debit = float(txn['amount']) + float(txn['charge_amount'])
                    actual_debit = float(txn['total_debited']) if txn['total_debited'] else 0.0
                    
                    # Check if deduction is correct
                    if txn['status'] == 'SUCCESS':
                        if txn['wallet_deduction_count'] == 0:
                            match_status = "❌ MISSING"
                            missing_deductions += 1
                        elif abs(actual_debit - expected_debit) < 0.01:  # Allow for floating point precision
                            match_status = "✅ CORRECT"
                            correct_deductions += 1
                        else:
                            match_status = f"⚠️  WRONG (₹{actual_debit:.2f})"
                            incorrect_amounts += 1
                    elif txn['status'] in ['FAILED', 'PENDING', 'QUEUED', 'INPROCESS']:
                        if txn['wallet_deduction_count'] == 0:
                            match_status = "✅ CORRECT (No debit)"
                            correct_deductions += 1
                        else:
                            match_status = f"❌ WRONG (₹{actual_debit:.2f} debited)"
                            incorrect_amounts += 1
                    else:
                        match_status = "❓ UNKNOWN"
                    
                    print(f"{txn['txn_id']:<15} {txn['merchant_id']:<12} ₹{txn['amount']:<7} ₹{txn['charge_amount']:<7} {txn['status']:<10} {txn['wallet_deduction_count']:<12} ₹{actual_debit:<11.2f} {match_status}")
                
                print(f"\n📊 Wallet Deduction Summary:")
                print(f"   - Correct Deductions: {correct_deductions}")
                print(f"   - Missing Deductions: {missing_deductions}")
                print(f"   - Incorrect Amounts: {incorrect_amounts}")
                
                if missing_deductions > 0 or incorrect_amounts > 0:
                    print(f"   ⚠️  Issues found! Please investigate.")
                else:
                    print(f"   ✅ All wallet deductions are correct!")
            
            else:
                print("ℹ️  No merchant PayTouch2 transactions found")
            
            # 3. Check callback logs
            print(f"\n📞 Callback Analysis:")
            print("-" * 60)
            
            cursor.execute("""
                SELECT 
                    cl.id,
                    cl.merchant_id,
                    cl.txn_id,
                    cl.response_code,
                    cl.created_at,
                    pt.status as txn_status,
                    pt.pg_partner
                FROM callback_logs cl
                LEFT JOIN payout_transactions pt ON cl.txn_id = pt.txn_id
                WHERE pt.pg_partner = 'Paytouch2'
                ORDER BY cl.created_at DESC
                LIMIT 10
            """)
            
            callbacks = cursor.fetchall()
            
            if callbacks:
                print(f"{'Callback ID':<12} {'TXN ID':<15} {'Merchant':<12} {'Response':<8} {'TXN Status':<10} {'Time'}")
                print("-" * 80)
                
                for cb in callbacks:
                    time_display = cb['created_at'].strftime('%m-%d %H:%M') if cb['created_at'] else 'N/A'
                    merchant_display = cb['merchant_id'] or 'ADMIN'
                    
                    print(f"{cb['id']:<12} {cb['txn_id']:<15} {merchant_display:<12} {cb['response_code']:<8} {cb['txn_status']:<10} {time_display}")
            else:
                print("ℹ️  No PayTouch2 callback logs found")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def test_paytouch2_callback_flow():
    """Test PayTouch2 callback flow simulation"""
    
    print("\n🧪 Testing PayTouch2 Callback Flow")
    print("=" * 50)
    
    # This would simulate a callback - for testing purposes only
    print("ℹ️  To test callback flow:")
    print("1. Create a test payout transaction")
    print("2. Send a test callback to: /api/callback/paytouch2/payout")
    print("3. Verify wallet deduction occurs")
    print("4. Check transaction status update")
    
    test_callback_data = {
        "transaction_id": "PT2_TEST_123456",
        "external_ref": "TEST_REF_123",
        "status": "SUCCESS",
        "utr": "UTR123456789",
        "amount": 100.00,
        "message": "Test payout success"
    }
    
    print(f"\nExample callback data:")
    print(json.dumps(test_callback_data, indent=2))
    
    print(f"\nTest command:")
    print(f"curl -X POST https://api.moneyone.co.in/api/callback/paytouch2/payout \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(test_callback_data)}'")

def fix_missing_wallet_deductions():
    """Fix missing wallet deductions for SUCCESS PayTouch2 transactions"""
    
    print("\n🔧 Fixing Missing Wallet Deductions")
    print("=" * 50)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Find SUCCESS transactions without wallet deductions
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.charge_amount,
                    pt.reference_id
                FROM payout_transactions pt
                LEFT JOIN merchant_wallet_transactions mwt ON mwt.reference_id = pt.txn_id AND mwt.txn_type = 'DEBIT'
                WHERE pt.pg_partner = 'Paytouch2'
                AND pt.status = 'SUCCESS'
                AND pt.merchant_id IS NOT NULL
                AND mwt.id IS NULL
                ORDER BY pt.created_at DESC
            """)
            
            missing_deductions = cursor.fetchall()
            
            if not missing_deductions:
                print("✅ No missing wallet deductions found")
                return True
            
            print(f"⚠️  Found {len(missing_deductions)} SUCCESS transactions without wallet deductions:")
            
            for txn in missing_deductions:
                total_deduction = float(txn['amount']) + float(txn['charge_amount'])
                print(f"   - {txn['txn_id']}: Merchant {txn['merchant_id']}, Amount ₹{total_deduction:.2f}")
            
            # Ask for confirmation
            response = input(f"\nDo you want to fix these {len(missing_deductions)} transactions? (y/N): ")
            
            if response.lower() != 'y':
                print("❌ Operation cancelled")
                return False
            
            # Import wallet service
            try:
                from wallet_service import WalletService
                wallet_svc = WalletService()
            except ImportError:
                print("❌ Could not import WalletService")
                return False
            
            fixed_count = 0
            failed_count = 0
            
            for txn in missing_deductions:
                total_deduction = float(txn['amount']) + float(txn['charge_amount'])
                
                print(f"Processing {txn['txn_id']}...")
                
                # Debit merchant wallet
                debit_result = wallet_svc.debit_merchant_wallet(
                    merchant_id=txn['merchant_id'],
                    amount=total_deduction,
                    description=f"PayTouch2 Payout - {txn['reference_id']} (Manual Fix)",
                    reference_id=txn['txn_id']
                )
                
                if debit_result['success']:
                    print(f"   ✅ Wallet debited: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                    fixed_count += 1
                else:
                    print(f"   ❌ Failed: {debit_result['message']}")
                    failed_count += 1
            
            print(f"\n📊 Fix Summary:")
            print(f"   - Fixed: {fixed_count}")
            print(f"   - Failed: {failed_count}")
            
            return fixed_count > 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'fix':
            fix_missing_wallet_deductions()
        elif sys.argv[1] == 'test':
            test_paytouch2_callback_flow()
        else:
            print("Usage:")
            print("  python check_paytouch2_wallet_system.py        # Check system")
            print("  python check_paytouch2_wallet_system.py fix    # Fix missing deductions")
            print("  python check_paytouch2_wallet_system.py test   # Test callback flow")
    else:
        success = check_paytouch2_transactions()
        
        if success:
            print("\n✅ PayTouch2 wallet system check completed!")
        else:
            print("\n❌ PayTouch2 wallet system check failed!")

if __name__ == '__main__':
    main()