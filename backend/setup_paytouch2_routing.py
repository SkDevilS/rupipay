#!/usr/bin/env python3
"""
Setup PayTouch2 Service Routing
Configures PayTouch2 as a payout gateway option for merchants
"""

from database import get_db_connection

def setup_paytouch2_routing():
    """Setup PayTouch2 routing configurations"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("🔧 Setting up PayTouch2 Service Routing")
            print("=" * 50)
            
            # 1. Add PayTouch2 for ADMIN personal payouts
            print("\n1. Adding PayTouch2 for ADMIN personal payouts...")
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id,
                    service_type,
                    routing_type,
                    pg_partner,
                    priority,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (
                    NULL,
                    'PAYOUT',
                    'ADMIN',
                    'Paytouch2',
                    2,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON DUPLICATE KEY UPDATE
                is_active = TRUE,
                priority = 2,
                updated_at = CURRENT_TIMESTAMP
            """)
            print("✅ PayTouch2 admin routing configured")
            
            # 2. Add PayTouch2 as ALL_USERS default (inactive by default)
            print("\n2. Adding PayTouch2 for ALL_USERS (inactive by default)...")
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id,
                    service_type,
                    routing_type,
                    pg_partner,
                    priority,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (
                    NULL,
                    'PAYOUT',
                    'ALL_USERS',
                    'Paytouch2',
                    3,
                    FALSE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON DUPLICATE KEY UPDATE
                priority = 3,
                updated_at = CURRENT_TIMESTAMP
            """)
            print("✅ PayTouch2 ALL_USERS routing configured (inactive)")
            
            conn.commit()
            
            # 3. Show current routing configuration
            print("\n3. Current PAYOUT routing configuration:")
            cursor.execute("""
                SELECT 
                    id,
                    merchant_id,
                    routing_type,
                    pg_partner,
                    priority,
                    is_active,
                    created_at
                FROM service_routing
                WHERE service_type = 'PAYOUT'
                ORDER BY routing_type, priority, pg_partner
            """)
            
            routes = cursor.fetchall()
            
            print("\n📋 PAYOUT Service Routing:")
            print("-" * 80)
            print(f"{'ID':<5} {'Merchant':<15} {'Type':<12} {'Gateway':<12} {'Priority':<8} {'Active':<8} {'Created'}")
            print("-" * 80)
            
            for route in routes:
                merchant_display = route['merchant_id'] or 'ALL'
                active_display = "✓" if route['is_active'] else "✗"
                created_display = route['created_at'].strftime('%Y-%m-%d') if route['created_at'] else 'N/A'
                
                print(f"{route['id']:<5} {merchant_display:<15} {route['routing_type']:<12} {route['pg_partner']:<12} {route['priority']:<8} {active_display:<8} {created_display}")
            
            # 4. Show example commands for merchant configuration
            print("\n4. Example commands to configure PayTouch2 for specific merchants:")
            print("-" * 60)
            print("# Configure PayTouch2 for a specific merchant:")
            print("INSERT INTO service_routing (merchant_id, service_type, routing_type, pg_partner, priority, is_active)")
            print("VALUES ('MERCHANT_ID', 'PAYOUT', 'SINGLE_USER', 'Paytouch2', 1, TRUE);")
            print("")
            print("# Enable PayTouch2 for ALL users:")
            print("UPDATE service_routing SET is_active = TRUE WHERE pg_partner = 'Paytouch2' AND routing_type = 'ALL_USERS';")
            print("")
            print("# Disable other gateways for a merchant:")
            print("UPDATE service_routing SET is_active = FALSE WHERE merchant_id = 'MERCHANT_ID' AND pg_partner != 'Paytouch2';")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def configure_merchant_paytouch2(merchant_id):
    """Configure PayTouch2 for a specific merchant"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Verify merchant exists
            cursor.execute("SELECT merchant_id, full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant {merchant_id} not found")
                return False
            
            print(f"🔧 Configuring PayTouch2 for merchant: {merchant['full_name']} ({merchant_id})")
            
            # Deactivate all other payout gateways for this merchant
            cursor.execute("""
                UPDATE service_routing
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE merchant_id = %s
                AND service_type = 'PAYOUT'
                AND routing_type = 'SINGLE_USER'
                AND pg_partner != 'Paytouch2'
            """, (merchant_id,))
            
            deactivated_count = cursor.rowcount
            if deactivated_count > 0:
                print(f"✅ Deactivated {deactivated_count} other payout gateways")
            
            # Add/activate PayTouch2 for this merchant
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id,
                    service_type,
                    routing_type,
                    pg_partner,
                    priority,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (%s, 'PAYOUT', 'SINGLE_USER', 'Paytouch2', 1, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE
                is_active = TRUE,
                priority = 1,
                updated_at = CURRENT_TIMESTAMP
            """, (merchant_id,))
            
            conn.commit()
            
            print(f"✅ PayTouch2 configured for merchant {merchant_id}")
            
            # Show current configuration for this merchant
            cursor.execute("""
                SELECT pg_partner, priority, is_active
                FROM service_routing
                WHERE merchant_id = %s AND service_type = 'PAYOUT'
                ORDER BY priority
            """, (merchant_id,))
            
            routes = cursor.fetchall()
            
            print(f"\n📋 Current PAYOUT configuration for {merchant_id}:")
            for route in routes:
                status = "✓ Active" if route['is_active'] else "✗ Inactive"
                print(f"   - {route['pg_partner']}: Priority {route['priority']} [{status}]")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def check_paytouch2_wallet_deduction():
    """Check PayTouch2 wallet deduction system"""
    
    print("\n🔧 Checking PayTouch2 Wallet Deduction System")
    print("=" * 50)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check recent PayTouch2 transactions
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    admin_id,
                    reference_id,
                    amount,
                    charge_amount,
                    status,
                    pg_txn_id,
                    utr,
                    created_at,
                    completed_at
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("ℹ️  No PayTouch2 transactions found")
                return True
            
            print(f"📊 Recent PayTouch2 transactions ({len(transactions)}):")
            print("-" * 100)
            print(f"{'TXN ID':<15} {'Merchant':<12} {'Amount':<8} {'Status':<10} {'UTR':<15} {'Created'}")
            print("-" * 100)
            
            for txn in transactions:
                merchant_display = txn['merchant_id'] or f"ADMIN_{txn['admin_id']}" if txn['admin_id'] else 'N/A'
                created_display = txn['created_at'].strftime('%m-%d %H:%M') if txn['created_at'] else 'N/A'
                utr_display = txn['utr'][:15] if txn['utr'] else 'N/A'
                
                print(f"{txn['txn_id']:<15} {merchant_display:<12} ₹{txn['amount']:<7} {txn['status']:<10} {utr_display:<15} {created_display}")
            
            # Check wallet deductions for SUCCESS transactions
            print("\n🔍 Checking wallet deductions for SUCCESS transactions:")
            
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.charge_amount,
                    pt.status,
                    COUNT(mwt.id) as wallet_deduction_count
                FROM payout_transactions pt
                LEFT JOIN merchant_wallet_transactions mwt ON mwt.reference_id = pt.txn_id AND mwt.txn_type = 'DEBIT'
                WHERE pt.pg_partner = 'Paytouch2'
                AND pt.status = 'SUCCESS'
                AND pt.merchant_id IS NOT NULL
                GROUP BY pt.txn_id
                ORDER BY pt.created_at DESC
                LIMIT 5
            """)
            
            success_txns = cursor.fetchall()
            
            if success_txns:
                print("-" * 80)
                print(f"{'TXN ID':<15} {'Merchant':<12} {'Amount':<8} {'Wallet Debits':<12} {'Status'}")
                print("-" * 80)
                
                for txn in success_txns:
                    debit_status = "✅ Debited" if txn['wallet_deduction_count'] > 0 else "❌ Missing"
                    print(f"{txn['txn_id']:<15} {txn['merchant_id']:<12} ₹{txn['amount']:<7} {txn['wallet_deduction_count']:<12} {debit_status}")
            else:
                print("ℹ️  No SUCCESS PayTouch2 transactions found")
            
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
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'merchant' and len(sys.argv) > 2:
            merchant_id = sys.argv[2]
            print(f"🚀 Configuring PayTouch2 for merchant: {merchant_id}")
            success = configure_merchant_paytouch2(merchant_id)
        elif sys.argv[1] == 'check':
            success = check_paytouch2_wallet_deduction()
        else:
            print("Usage:")
            print("  python setup_paytouch2_routing.py                    # Setup basic routing")
            print("  python setup_paytouch2_routing.py merchant <ID>      # Configure for merchant")
            print("  python setup_paytouch2_routing.py check              # Check wallet deductions")
            return
    else:
        print("🚀 Setting up PayTouch2 Service Routing")
        success = setup_paytouch2_routing()
        
        if success:
            check_paytouch2_wallet_deduction()
    
    if success:
        print("\n✅ PayTouch2 routing setup completed!")
        print("\n📝 Next steps:")
        print("1. Configure PayTouch2 callback URL in dashboard:")
        print("   https://api.moneyone.co.in/api/callback/paytouch2/payout")
        print("2. Update PAYTOUCH2_TOKEN in backend/.env")
        print("3. Test with admin personal payout")
        print("4. Configure for specific merchants using:")
        print("   python setup_paytouch2_routing.py merchant MERCHANT_ID")
    else:
        print("\n❌ PayTouch2 routing setup failed")

if __name__ == '__main__':
    main()