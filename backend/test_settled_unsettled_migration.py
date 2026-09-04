"""
Test Script for Settled/Unsettled Wallet Migration
Verifies that the migration was successful and the feature works correctly
"""

import pymysql
from config import Config
from wallet_service import wallet_service

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def test_migration():
    """Test if migration was successful"""
    print("=" * 80)
    print("TESTING SETTLED/UNSETTLED WALLET MIGRATION")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        return False
    
    all_tests_passed = True
    
    try:
        with conn.cursor() as cursor:
            # Test 1: Check if columns exist
            print("Test 1: Checking if columns exist...")
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'merchant_wallet'
                AND COLUMN_NAME IN ('settled_balance', 'unsettled_balance')
            """, (Config.DB_NAME,))
            columns = cursor.fetchall()
            
            if len(columns) == 2:
                print("✓ Both columns exist (settled_balance, unsettled_balance)")
            else:
                print(f"✗ Missing columns. Found: {[c['COLUMN_NAME'] for c in columns]}")
                all_tests_passed = False
            print()
            
            # Test 2: Check if settlement_transactions table exists
            print("Test 2: Checking if settlement_transactions table exists...")
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'settlement_transactions'
            """, (Config.DB_NAME,))
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print("✓ settlement_transactions table exists")
            else:
                print("✗ settlement_transactions table not found")
                all_tests_passed = False
            print()
            
            # Test 3: Check if data was migrated
            print("Test 3: Checking if existing balance was migrated...")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN balance > 0 AND settled_balance = 0 THEN 1 END) as unmigrated
                FROM merchant_wallet
                WHERE balance > 0
            """)
            migration_check = cursor.fetchone()
            
            if migration_check['unmigrated'] == 0:
                print(f"✓ All {migration_check['total']} wallets with balance have been migrated")
            else:
                print(f"✗ {migration_check['unmigrated']} wallets not migrated properly")
                all_tests_passed = False
            print()
            
            # Test 4: Test wallet service methods
            print("Test 4: Testing wallet service methods...")
            
            # Get a test merchant
            cursor.execute("SELECT merchant_id FROM merchants LIMIT 1")
            merchant = cursor.fetchone()
            
            if merchant:
                merchant_id = merchant['merchant_id']
                print(f"  Using test merchant: {merchant_id}")
                
                # Test get wallet
                wallet = wallet_service.get_merchant_wallet(merchant_id)
                if wallet:
                    print(f"  ✓ get_merchant_wallet() works")
                    print(f"    Balance: ₹{wallet.get('balance', 0):.2f}")
                    print(f"    Settled: ₹{wallet.get('settled_balance', 0):.2f}")
                    print(f"    Unsettled: ₹{wallet.get('unsettled_balance', 0):.2f}")
                else:
                    print("  ✗ get_merchant_wallet() failed")
                    all_tests_passed = False
                
                # Test get_all_merchants_wallet_summary
                summary = wallet_service.get_all_merchants_wallet_summary()
                if summary:
                    print(f"  ✓ get_all_merchants_wallet_summary() works")
                    print(f"    Total Settled: ₹{summary.get('total_settled', 0):.2f}")
                    print(f"    Total Unsettled: ₹{summary.get('total_unsettled', 0):.2f}")
                else:
                    print("  ✗ get_all_merchants_wallet_summary() failed")
                    all_tests_passed = False
            else:
                print("  ⚠ No merchants found to test with")
            print()
            
            # Test 5: Check foreign key constraints
            print("Test 5: Checking foreign key constraints...")
            cursor.execute("""
                SELECT 
                    CONSTRAINT_NAME,
                    REFERENCED_TABLE_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'settlement_transactions'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (Config.DB_NAME,))
            constraints = cursor.fetchall()
            
            expected_refs = {'merchants', 'admin_users'}
            found_refs = {c['REFERENCED_TABLE_NAME'] for c in constraints}
            
            if expected_refs.issubset(found_refs):
                print(f"✓ All foreign key constraints exist: {', '.join(found_refs)}")
            else:
                missing = expected_refs - found_refs
                print(f"✗ Missing foreign key constraints: {', '.join(missing)}")
                all_tests_passed = False
            print()
            
            # Test 6: Check indexes
            print("Test 6: Checking indexes on settlement_transactions...")
            cursor.execute("""
                SELECT DISTINCT INDEX_NAME
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'settlement_transactions'
                AND INDEX_NAME != 'PRIMARY'
            """, (Config.DB_NAME,))
            indexes = cursor.fetchall()
            
            if len(indexes) >= 2:
                print(f"✓ Indexes exist: {', '.join([i['INDEX_NAME'] for i in indexes])}")
            else:
                print(f"⚠ Expected at least 2 indexes, found {len(indexes)}")
            print()
            
        conn.close()
        
        # Final result
        print("=" * 80)
        if all_tests_passed:
            print("✅ ALL TESTS PASSED - Migration successful!")
        else:
            print("⚠ SOME TESTS FAILED - Please review the errors above")
        print("=" * 80)
        print()
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False

def test_settlement_flow():
    """Test the complete settlement flow"""
    print("=" * 80)
    print("TESTING SETTLEMENT FLOW")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get a test merchant
            cursor.execute("SELECT merchant_id FROM merchants LIMIT 1")
            merchant = cursor.fetchone()
            
            if not merchant:
                print("⚠ No merchants found to test with")
                return False
            
            merchant_id = merchant['merchant_id']
            print(f"Testing with merchant: {merchant_id}")
            print()
            
            # Get initial wallet state
            cursor.execute("""
                SELECT settled_balance, unsettled_balance
                FROM merchant_wallet
                WHERE merchant_id = %s
            """, (merchant_id,))
            initial_wallet = cursor.fetchone()
            
            if not initial_wallet:
                # Create wallet if doesn't exist
                cursor.execute("""
                    INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                    VALUES (%s, 0.00, 0.00, 0.00)
                """, (merchant_id,))
                conn.commit()
                initial_wallet = {'settled_balance': 0.00, 'unsettled_balance': 0.00}
            
            print("Initial wallet state:")
            print(f"  Settled: ₹{float(initial_wallet['settled_balance']):.2f}")
            print(f"  Unsettled: ₹{float(initial_wallet['unsettled_balance']):.2f}")
            print()
            
            # Test 1: Credit unsettled wallet
            print("Test 1: Crediting unsettled wallet with ₹100.00...")
            result = wallet_service.credit_unsettled_wallet(
                merchant_id, 
                100.00, 
                "Test payin credit",
                "TEST_TXN_001"
            )
            
            if result['success']:
                print(f"✓ Unsettled wallet credited")
                print(f"  Before: ₹{result['unsettled_before']:.2f}")
                print(f"  After: ₹{result['unsettled_after']:.2f}")
            else:
                print(f"✗ Failed to credit unsettled wallet: {result.get('message')}")
                return False
            print()
            
            # Test 2: Settle wallet
            print("Test 2: Settling ₹50.00 from unsettled to settled...")
            result = wallet_service.settle_wallet(
                merchant_id,
                50.00,
                'admin',
                'Test settlement'
            )
            
            if result['success']:
                print(f"✓ Wallet settled")
                print(f"  Settlement ID: {result['settlement_id']}")
                print(f"  Settled Balance: ₹{result['settled_balance']:.2f}")
                print(f"  Unsettled Balance: ₹{result['unsettled_balance']:.2f}")
            else:
                print(f"✗ Failed to settle wallet: {result.get('message')}")
                return False
            print()
            
            # Test 3: Verify final state
            print("Test 3: Verifying final wallet state...")
            cursor.execute("""
                SELECT settled_balance, unsettled_balance
                FROM merchant_wallet
                WHERE merchant_id = %s
            """, (merchant_id,))
            final_wallet = cursor.fetchone()
            
            expected_settled = float(initial_wallet['settled_balance']) + 50.00
            expected_unsettled = float(initial_wallet['unsettled_balance']) + 100.00 - 50.00
            
            actual_settled = float(final_wallet['settled_balance'])
            actual_unsettled = float(final_wallet['unsettled_balance'])
            
            print(f"Expected - Settled: ₹{expected_settled:.2f}, Unsettled: ₹{expected_unsettled:.2f}")
            print(f"Actual   - Settled: ₹{actual_settled:.2f}, Unsettled: ₹{actual_unsettled:.2f}")
            
            if abs(actual_settled - expected_settled) < 0.01 and abs(actual_unsettled - expected_unsettled) < 0.01:
                print("✓ Wallet balances match expected values")
            else:
                print("✗ Wallet balances don't match expected values")
                return False
            print()
            
            # Test 4: Check settlement transaction was recorded
            print("Test 4: Checking settlement transaction record...")
            cursor.execute("""
                SELECT * FROM settlement_transactions
                WHERE merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (merchant_id,))
            settlement = cursor.fetchone()
            
            if settlement:
                print(f"✓ Settlement transaction recorded")
                print(f"  Settlement ID: {settlement['settlement_id']}")
                print(f"  Amount: ₹{float(settlement['amount']):.2f}")
                print(f"  Settled By: {settlement['settled_by']}")
                print(f"  Remarks: {settlement['remarks']}")
            else:
                print("✗ Settlement transaction not found")
                return False
            print()
            
        conn.close()
        
        print("=" * 80)
        print("✅ SETTLEMENT FLOW TEST PASSED!")
        print("=" * 80)
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Settlement flow test failed: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "flow":
        # Test settlement flow
        success = test_settlement_flow()
    else:
        # Test migration
        success = test_migration()
    
    sys.exit(0 if success else 1)
