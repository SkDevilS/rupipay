#!/usr/bin/env python3
"""
Mudrape Payin Callback Diagnostic Script
Checks the complete callback flow configuration
"""

import sys
from database import get_db_connection
import json

def check_callback_configuration():
    """Check all aspects of callback configuration"""
    
    print("=" * 80)
    print("MUDRAPE PAYIN CALLBACK DIAGNOSTIC")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed!")
        return False
    
    try:
        with conn.cursor() as cursor:
            # 1. Check payin_transactions table structure
            print("1. Checking payin_transactions table structure...")
            cursor.execute("""
                SHOW COLUMNS FROM payin_transactions LIKE 'callback_url'
            """)
            callback_column = cursor.fetchone()
            
            if callback_column:
                print("   ✓ callback_url column exists in payin_transactions")
            else:
                print("   ❌ callback_url column MISSING in payin_transactions")
                print("   → This column is needed to store merchant callback URLs")
            print()
            
            # 2. Check merchant_callbacks table
            print("2. Checking merchant_callbacks table...")
            cursor.execute("""
                SHOW TABLES LIKE 'merchant_callbacks'
            """)
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("   ✓ merchant_callbacks table exists")
                
                # Check structure
                cursor.execute("""
                    SHOW COLUMNS FROM merchant_callbacks
                """)
                columns = cursor.fetchall()
                column_names = [col['Field'] for col in columns]
                
                if 'payin_callback_url' in column_names:
                    print("   ✓ payin_callback_url column exists")
                else:
                    print("   ❌ payin_callback_url column MISSING")
                
                # Check if any merchants have callback URLs configured
                # First check if is_active column exists
                cursor.execute("""
                    SHOW COLUMNS FROM merchant_callbacks LIKE 'is_active'
                """)
                has_is_active = cursor.fetchone()
                
                if has_is_active:
                    cursor.execute("""
                        SELECT merchant_id, payin_callback_url, is_active
                        FROM merchant_callbacks
                        WHERE payin_callback_url IS NOT NULL AND payin_callback_url != ''
                    """)
                    merchants_with_callbacks = cursor.fetchall()
                    
                    if merchants_with_callbacks:
                        print(f"   ✓ {len(merchants_with_callbacks)} merchant(s) have payin callback URLs configured:")
                        for m in merchants_with_callbacks:
                            status = "ACTIVE" if m.get('is_active') else "INACTIVE"
                            print(f"     - {m['merchant_id']}: {m['payin_callback_url']} [{status}]")
                    else:
                        print("   ⚠ No merchants have payin callback URLs configured")
                else:
                    cursor.execute("""
                        SELECT merchant_id, payin_callback_url
                        FROM merchant_callbacks
                        WHERE payin_callback_url IS NOT NULL AND payin_callback_url != ''
                    """)
                    merchants_with_callbacks = cursor.fetchall()
                    
                    if merchants_with_callbacks:
                        print(f"   ✓ {len(merchants_with_callbacks)} merchant(s) have payin callback URLs configured:")
                        for m in merchants_with_callbacks:
                            print(f"     - {m['merchant_id']}: {m['payin_callback_url']}")
                    else:
                        print("   ⚠ No merchants have payin callback URLs configured")
            else:
                print("   ❌ merchant_callbacks table does NOT exist")
            print()
            
            # 3. Check recent payin transactions
            print("3. Checking recent Mudrape payin transactions...")
            cursor.execute("""
                SELECT txn_id, merchant_id, order_id, amount, status, 
                       callback_url, pg_txn_id, bank_ref_no, created_at
                FROM payin_transactions
                WHERE pg_partner = 'Mudrape'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            recent_txns = cursor.fetchall()
            
            if recent_txns:
                print(f"   Found {len(recent_txns)} recent Mudrape transactions:")
                for txn in recent_txns:
                    print(f"\n   Transaction: {txn['txn_id']}")
                    print(f"   - Merchant: {txn['merchant_id']}")
                    print(f"   - Order ID: {txn['order_id']}")
                    print(f"   - Amount: {txn['amount']}")
                    print(f"   - Status: {txn['status']}")
                    print(f"   - Callback URL: {txn.get('callback_url') or 'NOT SET ❌'}")
                    print(f"   - PG TXN ID: {txn.get('pg_txn_id') or 'N/A'}")
                    print(f"   - UTR: {txn.get('bank_ref_no') or 'N/A'}")
                    print(f"   - Created: {txn['created_at']}")
            else:
                print("   ⚠ No Mudrape payin transactions found")
            print()
            
            # 4. Check callback_logs table
            print("4. Checking callback_logs table...")
            cursor.execute("""
                SHOW TABLES LIKE 'callback_logs'
            """)
            logs_table = cursor.fetchone()
            
            if logs_table:
                print("   ✓ callback_logs table exists")
                
                # Check recent callback attempts
                cursor.execute("""
                    SELECT cl.*, pt.order_id, pt.pg_partner
                    FROM callback_logs cl
                    LEFT JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
                    WHERE pt.pg_partner = 'Mudrape'
                    ORDER BY cl.created_at DESC
                    LIMIT 5
                """)
                recent_logs = cursor.fetchall()
                
                if recent_logs:
                    print(f"   Found {len(recent_logs)} recent Mudrape callback attempts:")
                    for log in recent_logs:
                        print(f"\n   Callback Log ID: {log['id']}")
                        print(f"   - TXN ID: {log['txn_id']}")
                        print(f"   - Order ID: {log.get('order_id', 'N/A')}")
                        print(f"   - Callback URL: {log['callback_url']}")
                        print(f"   - Response Code: {log['response_code']}")
                        print(f"   - Created: {log['created_at']}")
                        if log['response_code'] != 200:
                            print(f"   - Response: {log.get('response_data', '')[:200]}")
                else:
                    print("   ⚠ No Mudrape callback logs found")
            else:
                print("   ❌ callback_logs table does NOT exist")
            print()
            
            # 5. Check Flask app configuration
            print("5. Checking Flask app configuration...")
            print("   Expected callback endpoint: /api/callback/mudrape/payin")
            print("   → Mudrape should POST to: https://your-domain.com/api/callback/mudrape/payin")
            print()
            
            # 6. Summary and recommendations
            print("=" * 80)
            print("SUMMARY & RECOMMENDATIONS")
            print("=" * 80)
            
            issues = []
            
            if not callback_column:
                issues.append("❌ callback_url column missing in payin_transactions table")
            
            if not table_exists:
                issues.append("❌ merchant_callbacks table missing")
            elif not merchants_with_callbacks:
                issues.append("⚠ No merchants have callback URLs configured")
            
            if not recent_txns:
                issues.append("⚠ No Mudrape transactions to test with")
            elif recent_txns:
                txns_without_callback = [t for t in recent_txns if not t.get('callback_url')]
                if txns_without_callback:
                    issues.append(f"❌ {len(txns_without_callback)}/{len(recent_txns)} recent transactions have NO callback_url stored")
            
            if not recent_logs:
                issues.append("⚠ No callback attempts logged (callbacks may not be triggering)")
            
            if issues:
                print("\nIssues Found:")
                for issue in issues:
                    print(f"  {issue}")
                print("\nRecommended Actions:")
                print("  1. Ensure callback_url is passed when creating payin orders")
                print("  2. Configure merchant callback URLs in merchant_callbacks table")
                print("  3. Verify Mudrape is configured to send callbacks to your endpoint")
                print("  4. Check server logs for incoming callback requests")
                print("  5. Test callback manually using test_merchant_callback.py")
            else:
                print("\n✓ All checks passed! Configuration looks good.")
            
            print()
            return len(issues) == 0
            
    finally:
        conn.close()


if __name__ == '__main__':
    success = check_callback_configuration()
    sys.exit(0 if success else 1)
