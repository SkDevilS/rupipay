"""
Setup PayTouch3_Trendora Routing Configuration
This script configures service routing for PayTouch3_Trendora payout gateway
"""

import sys
from database import get_db_connection

def setup_paytouch3_routing():
    """
    Setup PayTouch3_Trendora routing in service_routing table
    """
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            print("=" * 80)
            print("SETTING UP PAYTOUCH3_TRENDORA ROUTING")
            print("=" * 80)
            
            # Check if PayTouch3_Trendora routing already exists
            cursor.execute("""
                SELECT * FROM service_routing 
                WHERE pg_partner = 'Paytouch3_Trendora' AND service_type = 'PAYOUT'
            """)
            
            existing = cursor.fetchall()
            
            if existing:
                print(f"\n✓ Found {len(existing)} existing PayTouch3_Trendora routing entries")
                for entry in existing:
                    print(f"  - ID: {entry['id']}, Type: {entry['routing_type']}, Active: {entry['is_active']}")
            else:
                print("\n⚠️  No existing PayTouch3_Trendora routing found")
            
            # Insert default routing configurations
            print("\n📝 Creating PayTouch3_Trendora routing configurations...")
            
            # 1. ALL_USERS routing (disabled by default)
            cursor.execute("""
                INSERT INTO service_routing 
                (pg_partner, service_type, routing_type, is_active, priority, created_at)
                VALUES ('Paytouch3_Trendora', 'PAYOUT', 'ALL_USERS', FALSE, 1, NOW())
                ON DUPLICATE KEY UPDATE 
                pg_partner = 'Paytouch3_Trendora',
                service_type = 'PAYOUT',
                routing_type = 'ALL_USERS',
                priority = 1
            """)
            
            print("  ✓ Created ALL_USERS routing (disabled by default)")
            
            # 2. SPECIFIC_MERCHANT routing template
            cursor.execute("""
                INSERT INTO service_routing 
                (pg_partner, service_type, routing_type, merchant_id, is_active, priority, created_at)
                VALUES ('Paytouch3_Trendora', 'PAYOUT', 'SPECIFIC_MERCHANT', NULL, FALSE, 2, NOW())
                ON DUPLICATE KEY UPDATE 
                pg_partner = 'Paytouch3_Trendora',
                service_type = 'PAYOUT',
                routing_type = 'SPECIFIC_MERCHANT',
                priority = 2
            """)
            
            print("  ✓ Created SPECIFIC_MERCHANT routing template")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("✅ PAYTOUCH3_TRENDORA ROUTING SETUP COMPLETE")
            print("=" * 80)
            
            print("\n📋 NEXT STEPS:")
            print("\n1. Update credentials in backend/.env:")
            print("   PAYTOUCH3_BASE_URL=https://dashboard.shreefintechsolutions.com")
            print("   PAYTOUCH3_TOKEN=<your_trendora_token_here>")
            
            print("\n2. Restart backend server:")
            print("   docker-compose restart backend")
            
            print("\n3. Route a merchant to PayTouch3_Trendora:")
            print("   - Go to Admin Panel > Service Routing")
            print("   - Select merchant and set Payout Gateway to 'Paytouch3_Trendora'")
            
            print("\n4. Or use SQL to route a specific merchant:")
            print("   UPDATE service_routing")
            print("   SET merchant_id = '<merchant_id>', is_active = TRUE")
            print("   WHERE pg_partner = 'Paytouch3_Trendora' AND routing_type = 'SPECIFIC_MERCHANT';")
            
            print("\n5. Callback URL to provide to PayTouch3_Trendora team:")
            print("   https://your-domain.com/api/callback/paytouch3/payout")
            
            print("\n6. Transaction ID Format:")
            print("   PT3_TREN_TXN_<merchant_id>_<reference_id>_<timestamp>")
            
            print("\n" + "=" * 80)
            
            conn.close()
            return True
            
    except Exception as e:
        print(f"\n❌ Error setting up PayTouch3_Trendora routing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_paytouch3_routing()
    sys.exit(0 if success else 1)
