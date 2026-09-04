#!/usr/bin/env python3
"""
Setup Paytouchpayin Service Routing
Configures Paytouchpayin as a payment gateway option in the service routing system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def setup_paytouchpayin_routing():
    """Setup Paytouchpayin in service routing system"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            print("🔧 Setting up Paytouchpayin service routing...")
            
            # Check if Paytouchpayin routing already exists for ALL_USERS
            cursor.execute("""
                SELECT id FROM service_routing 
                WHERE pg_partner = 'Paytouchpayin' AND routing_type = 'ALL_USERS' AND service_type = 'PAYIN'
            """)
            
            existing = cursor.fetchone()
            
            if existing:
                print("✓ Paytouchpayin routing already exists")
                
                # Update to ensure it's active
                cursor.execute("""
                    UPDATE service_routing 
                    SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (existing['id'],))
                
                print("✓ Updated Paytouchpayin routing to active")
            else:
                # Insert new Paytouchpayin routing for ALL_USERS
                cursor.execute("""
                    INSERT INTO service_routing (
                        merchant_id, service_type, routing_type, pg_partner, priority, is_active
                    ) VALUES (
                        NULL, 'PAYIN', 'ALL_USERS', 'Paytouchpayin', 4, FALSE
                    )
                """)
                
                print("✓ Added Paytouchpayin routing configuration (inactive by default)")
            
            conn.commit()
            
            # Show current routing status
            cursor.execute("""
                SELECT pg_partner, routing_type, is_active, priority
                FROM service_routing 
                WHERE service_type = 'PAYIN' AND routing_type = 'ALL_USERS'
                ORDER BY priority ASC
            """)
            
            routes = cursor.fetchall()
            
            print("\n📋 Current PAYIN routing configuration (ALL_USERS):")
            print("Gateway         | Active | Priority")
            print("----------------|--------|----------")
            for route in routes:
                status = "✓" if route['is_active'] else "✗"
                print(f"{route['pg_partner']:<15} | {status:<6} | {route['priority']}")
            
            print("\n💡 To activate Paytouchpayin for all users:")
            print("   1. Go to Admin Dashboard > Service Routing")
            print("   2. Activate Paytouchpayin and deactivate other gateways")
            print("   3. Or use the API to update routing configuration")
            
            print("\n🔗 Paytouchpayin callback URL to configure in dashboard:")
            print("   https://api.moneyone.co.in/api/paytouchpayin/callback")
            
            return True
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

def setup_merchant_routing(merchant_id):
    """Setup Paytouchpayin routing for a specific merchant"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            print(f"🔧 Setting up Paytouchpayin routing for merchant {merchant_id}...")
            
            # Check if merchant exists
            cursor.execute("SELECT merchant_id, name FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant {merchant_id} not found")
                return False
            
            print(f"✓ Found merchant: {merchant['name']}")
            
            # Check if routing already exists
            cursor.execute("""
                SELECT id, is_active FROM service_routing 
                WHERE merchant_id = %s AND pg_partner = 'Paytouchpayin' AND service_type = 'PAYIN'
            """, (merchant_id,))
            
            existing = cursor.fetchone()
            
            if existing:
                print("✓ Paytouchpayin routing already exists for this merchant")
                
                if not existing['is_active']:
                    cursor.execute("""
                        UPDATE service_routing 
                        SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (existing['id'],))
                    print("✓ Activated Paytouchpayin routing")
                else:
                    print("✓ Routing is already active")
            else:
                # Insert new routing for this merchant
                cursor.execute("""
                    INSERT INTO service_routing (
                        merchant_id, service_type, routing_type, pg_partner, priority, is_active
                    ) VALUES (
                        %s, 'PAYIN', 'SINGLE_USER', 'Paytouchpayin', 1, TRUE
                    )
                """, (merchant_id,))
                
                print("✓ Added Paytouchpayin routing for merchant (active)")
            
            conn.commit()
            
            # Show merchant's routing
            cursor.execute("""
                SELECT pg_partner, routing_type, is_active, priority
                FROM service_routing 
                WHERE merchant_id = %s AND service_type = 'PAYIN'
                ORDER BY priority ASC
            """, (merchant_id,))
            
            routes = cursor.fetchall()
            
            print(f"\n📋 PAYIN routing for merchant {merchant_id}:")
            print("Gateway         | Type        | Active | Priority")
            print("----------------|-------------|--------|----------")
            for route in routes:
                status = "✓" if route['is_active'] else "✗"
                print(f"{route['pg_partner']:<15} | {route['routing_type']:<11} | {status:<6} | {route['priority']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

def test_paytouchpayin_service():
    """Test Paytouchpayin service configuration"""
    try:
        print("\n🧪 Testing Paytouchpayin service configuration...")
        
        from paytouchpayin_service import paytouchpayin_service
        
        # Check if configuration is loaded
        print(f"✓ Base URL: {paytouchpayin_service.base_url}")
        print(f"✓ Token: {paytouchpayin_service.token[:10]}..." if paytouchpayin_service.token else "❌ Token not configured")
        
        if not paytouchpayin_service.token:
            print("\n⚠️  Paytouchpayin configuration incomplete. Please set this environment variable:")
            print("   - PAYTOUCHPAYIN_TOKEN")
            return False
        
        print("✓ Paytouchpayin service configuration looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Paytouchpayin service test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Paytouchpayin Integration Setup")
    print("=" * 50)
    
    # Check if merchant ID is provided
    if len(sys.argv) > 1:
        merchant_id = sys.argv[1]
        print(f"\n📌 Setting up for merchant: {merchant_id}")
        
        if setup_merchant_routing(merchant_id):
            print(f"\n✅ Paytouchpayin routing setup completed for merchant {merchant_id}!")
        else:
            print(f"\n❌ Paytouchpayin routing setup failed for merchant {merchant_id}!")
            sys.exit(1)
    else:
        # Setup ALL_USERS routing
        if setup_paytouchpayin_routing():
            print("\n✅ Paytouchpayin routing setup completed!")
        else:
            print("\n❌ Paytouchpayin routing setup failed!")
            sys.exit(1)
    
    # Test service
    if test_paytouchpayin_service():
        print("\n✅ Paytouchpayin service test passed!")
    else:
        print("\n⚠️  Paytouchpayin service needs configuration!")
    
    print("\n🎉 Paytouchpayin integration setup complete!")
    print("\nNext steps:")
    print("1. Configure Paytouchpayin token in .env file")
    print("2. Set up callback URL in Paytouchpayin dashboard:")
    print("   https://api.moneyone.co.in/api/paytouchpayin/callback")
    print("3. Restart backend: sudo systemctl restart moneyone-backend")
    print("4. Test with merchant API")
