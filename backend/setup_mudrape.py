"""
Setup script for Mudrape integration
Verifies database schema and adds initial routing configuration
"""

from database import get_db_connection

def setup_mudrape():
    """Setup Mudrape integration"""
    print("Setting up Mudrape integration...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Verify service_routing table exists
            cursor.execute("""
                SHOW TABLES LIKE 'service_routing'
            """)
            
            if not cursor.fetchone():
                print("❌ service_routing table not found. Please run database initialization first.")
                return False
            
            print("✅ service_routing table exists")
            
            # Verify payin_transactions table supports Mudrape
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'payin_transactions' 
                AND COLUMN_NAME = 'pg_partner'
            """)
            
            pg_partner_col = cursor.fetchone()
            if not pg_partner_col:
                print("❌ pg_partner column not found in payin_transactions")
                return False
            
            print("✅ payin_transactions table supports multiple gateways")
            
            # Check if Mudrape routing already exists
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM service_routing 
                WHERE pg_partner = 'Mudrape'
            """)
            
            result = cursor.fetchone()
            if result['count'] > 0:
                print(f"ℹ️  Found {result['count']} existing Mudrape routing configuration(s)")
            else:
                print("ℹ️  No Mudrape routing configured yet")
                print("   Use Admin Dashboard → Service Routing to configure")
            
            # Verify config values
            from config import Config
            
            print("\n📋 Configuration Check:")
            print(f"   Base URL: {Config.MUDRAPE_BASE_URL}")
            print(f"   API Key: {Config.MUDRAPE_API_KEY[:20]}...")
            print(f"   User ID: {Config.MUDRAPE_USER_ID}")
            
            if not Config.MUDRAPE_MERCHANT_MID or Config.MUDRAPE_MERCHANT_MID == 'YOUR_MERCHANT_MID':
                print("   ⚠️  MUDRAPE_MERCHANT_MID not configured")
            else:
                print(f"   Merchant MID: {Config.MUDRAPE_MERCHANT_MID}")
            
            if not Config.MUDRAPE_MERCHANT_EMAIL or Config.MUDRAPE_MERCHANT_EMAIL == 'YOUR_MERCHANT_EMAIL':
                print("   ⚠️  MUDRAPE_MERCHANT_EMAIL not configured")
            else:
                print(f"   Merchant Email: {Config.MUDRAPE_MERCHANT_EMAIL}")
            
            if not Config.MUDRAPE_MERCHANT_SECRET or Config.MUDRAPE_MERCHANT_SECRET == 'YOUR_MERCHANT_SECRET':
                print("   ⚠️  MUDRAPE_MERCHANT_SECRET not configured")
            else:
                print(f"   Merchant Secret: {'*' * 20}")
            
            print("\n✅ Mudrape integration setup complete!")
            print("\n📝 Next Steps:")
            print("   1. Update MUDRAPE_MERCHANT_MID, EMAIL, and SECRET in backend/.env")
            print("   2. Restart the backend server")
            print("   3. Login to Admin Dashboard")
            print("   4. Go to User Management → Service Routing")
            print("   5. Configure Mudrape routing for merchants")
            print("   6. Test payment generation in Merchant Dashboard")
            
            return True
            
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    setup_mudrape()
