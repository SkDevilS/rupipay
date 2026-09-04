#!/usr/bin/env python3
"""
Setup Rang routing in the database
"""

from database import get_db_connection
import sys

def setup_rang_routing():
    """Setup Rang routing configuration"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        cursor = conn.cursor()
        
        # Check if service_routing table exists
        cursor.execute("""
            SHOW TABLES LIKE 'service_routing'
        """)
        
        if not cursor.fetchone():
            print("📋 Creating service_routing table...")
            cursor.execute("""
                CREATE TABLE service_routing (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    merchant_id VARCHAR(50) NULL,
                    service_type ENUM('PAYIN', 'PAYOUT') NOT NULL,
                    routing_type ENUM('SINGLE_USER', 'ALL_USERS') NOT NULL,
                    pg_partner VARCHAR(50) NOT NULL,
                    priority INT DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_routing (merchant_id, service_type, routing_type, pg_partner),
                    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE
                )
            """)
            print("✅ service_routing table created")
        else:
            print("✅ service_routing table already exists")
        
        # Add Rang as default payin gateway for all users (optional)
        print("🔧 Setting up Rang routing options...")
        
        # You can uncomment this to set Rang as default for all users
        # cursor.execute("""
        #     INSERT IGNORE INTO service_routing 
        #     (merchant_id, service_type, routing_type, pg_partner, priority, is_active)
        #     VALUES (NULL, 'PAYIN', 'ALL_USERS', 'Rang', 1, FALSE)
        # """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Rang routing setup completed successfully!")
        print("")
        print("📋 NEXT STEPS:")
        print("1. Go to Admin Panel > Service Routing")
        print("2. Create routing rules for merchants to use Rang")
        print("3. Set routing type:")
        print("   - SINGLE_USER: Route specific merchant to Rang")
        print("   - ALL_USERS: Route all merchants to Rang")
        print("4. Test payin orders with routed merchants")
        print("")
        print("🔍 AVAILABLE GATEWAYS:")
        print("- PayU (default)")
        print("- Mudrape")
        print("- Vega")
        print("- Airpay")
        print("- Tourquest")
        print("- SkrillPe")
        print("- Rang (newly added)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Rang routing: {str(e)}")
        return False

def test_rang_routing():
    """Test Rang routing configuration"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        cursor = conn.cursor(dictionary=True)
        
        print("🧪 Testing Rang routing configuration...")
        
        # Check if any Rang routing exists
        cursor.execute("""
            SELECT * FROM service_routing 
            WHERE pg_partner = 'Rang' AND service_type = 'PAYIN'
        """)
        
        rang_routes = cursor.fetchall()
        
        if rang_routes:
            print(f"✅ Found {len(rang_routes)} Rang routing configuration(s):")
            for route in rang_routes:
                merchant_info = route['merchant_id'] or 'ALL_USERS'
                status = 'ACTIVE' if route['is_active'] else 'INACTIVE'
                print(f"   - {merchant_info}: {route['routing_type']} ({status})")
        else:
            print("⚠️  No Rang routing configurations found")
            print("   Use Admin Panel to create routing rules")
        
        # Test gateway selection logic
        print("\n🔍 Testing gateway selection for sample merchant...")
        
        cursor.execute("""
            SELECT pg_partner FROM service_routing
            WHERE merchant_id IS NULL
            AND service_type = 'PAYIN' 
            AND routing_type = 'ALL_USERS'
            AND is_active = TRUE
            ORDER BY priority ASC
            LIMIT 1
        """)
        
        default_gateway = cursor.fetchone()
        
        if default_gateway:
            print(f"✅ Default gateway for all users: {default_gateway['pg_partner']}")
        else:
            print("✅ No default gateway set - will use PayU as fallback")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Rang routing: {str(e)}")
        return False

def main():
    """Main function"""
    print("🚀 Rang Routing Setup")
    print("=" * 30)
    
    # Setup routing
    if setup_rang_routing():
        # Test routing
        test_rang_routing()
        
        print("\n" + "=" * 30)
        print("✅ Rang routing setup complete!")
    else:
        print("\n❌ Rang routing setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()