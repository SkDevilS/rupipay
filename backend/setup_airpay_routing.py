#!/usr/bin/env python3
"""
Setup Airpay Service Routing
Configures Airpay as a payment gateway option in the service routing system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def setup_airpay_routing():
    """Setup Airpay in service routing system"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            print("🔧 Setting up Airpay service routing...")
            
            # Check if Airpay routing already exists for ALL_USERS
            cursor.execute("""
                SELECT id FROM service_routing 
                WHERE pg_partner = 'Airpay' AND routing_type = 'ALL_USERS' AND service_type = 'PAYIN'
            """)
            
            existing = cursor.fetchone()
            
            if existing:
                print("✓ Airpay routing already exists")
                
                # Update to ensure it's active
                cursor.execute("""
                    UPDATE service_routing 
                    SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (existing['id'],))
                
                print("✓ Updated Airpay routing to active")
            else:
                # Insert new Airpay routing for ALL_USERS
                cursor.execute("""
                    INSERT INTO service_routing (
                        merchant_id, service_type, routing_type, pg_partner, priority, is_active
                    ) VALUES (
                        NULL, 'PAYIN', 'ALL_USERS', 'Airpay', 3, FALSE
                    )
                """)
                
                print("✓ Added Airpay routing configuration (inactive by default)")
            
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
            print("Gateway    | Active | Priority")
            print("-----------|--------|----------")
            for route in routes:
                status = "✓" if route['is_active'] else "✗"
                print(f"{route['pg_partner']:<10} | {status:<6} | {route['priority']}")
            
            print("\n💡 To activate Airpay for all users:")
            print("   1. Go to Admin Dashboard > Service Routing")
            print("   2. Activate Airpay and deactivate other gateways")
            print("   3. Or use the API to update routing configuration")
            
            print("\n🔗 Airpay callback URL to configure in Airpay dashboard:")
            print("   https://your-domain.com/api/callback/airpay/payin")
            
            return True
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

def test_airpay_service():
    """Test Airpay service configuration"""
    try:
        print("\n🧪 Testing Airpay service configuration...")
        
        from airpay_service import airpay_service
        
        # Check if configuration is loaded
        print(f"✓ Base URL: {airpay_service.base_url}")
        print(f"✓ Client ID: {airpay_service.client_id[:10]}..." if airpay_service.client_id else "❌ Client ID not configured")
        print(f"✓ Merchant ID: {airpay_service.merchant_id}" if airpay_service.merchant_id else "❌ Merchant ID not configured")
        print(f"✓ Encryption Key: {'Configured' if airpay_service.encryption_key else 'Not configured'}")
        
        if not all([airpay_service.client_id, airpay_service.client_secret, 
                   airpay_service.merchant_id, airpay_service.encryption_key]):
            print("\n⚠️  Airpay configuration incomplete. Please set these environment variables:")
            print("   - AIRPAY_CLIENT_ID")
            print("   - AIRPAY_CLIENT_SECRET") 
            print("   - AIRPAY_MERCHANT_ID")
            print("   - AIRPAY_USERNAME")
            print("   - AIRPAY_PASSWORD")
            print("   - AIRPAY_ENCRYPTION_KEY")
            return False
        
        print("✓ Airpay service configuration looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Airpay service test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Airpay Integration Setup")
    print("=" * 50)
    
    # Setup routing
    if setup_airpay_routing():
        print("\n✅ Airpay routing setup completed!")
    else:
        print("\n❌ Airpay routing setup failed!")
        sys.exit(1)
    
    # Test service
    if test_airpay_service():
        print("\n✅ Airpay service test passed!")
    else:
        print("\n⚠️  Airpay service needs configuration!")
    
    print("\n🎉 Airpay integration setup complete!")
    print("\nNext steps:")
    print("1. Configure Airpay credentials in .env file")
    print("2. Set up callback URL in Airpay dashboard")
    print("3. Test with a small transaction")
    print("4. Activate Airpay routing in admin panel")