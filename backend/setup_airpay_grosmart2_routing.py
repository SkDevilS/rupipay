#!/usr/bin/env python3
"""
Setup Airpay Grosmart2 Routing for Merchant
Routes a specific merchant to use Airpay_Grosmart2 for payin
"""

import sys
from database import get_db_connection

def setup_airpay_grosmart2_routing(merchant_id):
    """Route merchant to Airpay_Grosmart2"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check if merchant exists
            cursor.execute("SELECT merchant_id, full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant {merchant_id} not found")
                return False
            
            print(f"✓ Found merchant: {merchant['full_name']} ({merchant_id})")
            
            # Check if Airpay_Grosmart2 service exists in service_routing
            cursor.execute("""
                SELECT id FROM service_routing 
                WHERE pg_partner = 'Airpay_Grosmart2' AND service_type = 'PAYIN'
            """)
            
            service = cursor.fetchone()
            
            if not service:
                print("⚠ Airpay_Grosmart2 not found in service_routing, adding it...")
                
                # Add Airpay_Grosmart2 to service_routing
                cursor.execute("""
                    INSERT INTO service_routing (
                        pg_partner, display_name, service_type, routing_type, is_active
                    ) VALUES (
                        'Airpay_Grosmart2', 'Airpay_Grosmart2', 'PAYIN', 'MERCHANT', 1
                    )
                """)
                
                print("✓ Added Airpay_Grosmart2 to service_routing")
            else:
                print("✓ Airpay_Grosmart2 service exists")
            
            # Check if merchant already has routing
            cursor.execute("""
                SELECT id, pg_partner FROM service_routing 
                WHERE merchant_id = %s AND service_type = 'PAYIN'
            """, (merchant_id,))
            
            existing_routing = cursor.fetchone()
            
            if existing_routing:
                print(f"⚠ Merchant currently routed to: {existing_routing['pg_partner']}")
                print(f"  Updating to Airpay_Grosmart2...")
                
                # Update existing routing
                cursor.execute("""
                    UPDATE service_routing 
                    SET pg_partner = 'Airpay_Grosmart2',
                        display_name = 'Airpay_Grosmart2',
                        is_active = 1,
                        updated_at = NOW()
                    WHERE merchant_id = %s AND service_type = 'PAYIN'
                """, (merchant_id,))
                
                print("✓ Updated merchant routing to Airpay_Grosmart2")
            else:
                print("  Creating new routing for merchant...")
                
                # Create new routing
                cursor.execute("""
                    INSERT INTO service_routing (
                        merchant_id, pg_partner, display_name, 
                        service_type, routing_type, is_active
                    ) VALUES (
                        %s, 'Airpay_Grosmart2', 'Airpay_Grosmart2', 
                        'PAYIN', 'MERCHANT', 1
                    )
                """, (merchant_id,))
                
                print("✓ Created new routing for merchant")
            
            conn.commit()
            
            # Verify routing
            cursor.execute("""
                SELECT merchant_id, pg_partner, service_type, is_active
                FROM service_routing
                WHERE merchant_id = %s AND service_type = 'PAYIN'
            """, (merchant_id,))
            
            routing = cursor.fetchone()
            
            print("\n" + "=" * 60)
            print("Routing Configuration:")
            print("=" * 60)
            print(f"Merchant ID: {routing['merchant_id']}")
            print(f"PG Partner: {routing['pg_partner']}")
            print(f"Service Type: {routing['service_type']}")
            print(f"Status: {'Active' if routing['is_active'] else 'Inactive'}")
            print("=" * 60)
            print("\n✅ Merchant successfully routed to Airpay_Grosmart2!")
            print("\nTransaction ID Prefix: AR_GROS2_")
            print("Callback URL: https://api.moneyone.co.in/api/callback/airpay_grosmart2/payin")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

def check_merchant_routing(merchant_id):
    """Check current routing for merchant"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    sr.merchant_id,
                    m.full_name,
                    sr.pg_partner,
                    sr.service_type,
                    sr.is_active
                FROM service_routing sr
                LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
                WHERE sr.merchant_id = %s
            """, (merchant_id,))
            
            routings = cursor.fetchall()
            
            if not routings:
                print(f"⚠ No routing found for merchant {merchant_id}")
                return
            
            print("\n" + "=" * 60)
            print(f"Current Routing for Merchant {merchant_id}")
            print("=" * 60)
            
            for routing in routings:
                print(f"\nMerchant: {routing['full_name']}")
                print(f"Service Type: {routing['service_type']}")
                print(f"PG Partner: {routing['pg_partner']}")
                print(f"Status: {'Active' if routing['is_active'] else 'Inactive'}")
            
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Setup routing:  python setup_airpay_grosmart2_routing.py <merchant_id>")
        print("  Check routing:  python setup_airpay_grosmart2_routing.py check <merchant_id>")
        print("\nExample:")
        print("  python setup_airpay_grosmart2_routing.py 9876543210")
        print("  python setup_airpay_grosmart2_routing.py check 9876543210")
        sys.exit(1)
    
    if sys.argv[1] == "check":
        if len(sys.argv) < 3:
            print("❌ Please provide merchant_id")
            sys.exit(1)
        merchant_id = sys.argv[2]
        check_merchant_routing(merchant_id)
    else:
        merchant_id = sys.argv[1]
        success = setup_airpay_grosmart2_routing(merchant_id)
        sys.exit(0 if success else 1)
