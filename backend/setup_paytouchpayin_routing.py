"""
Setup Paytouchpayin Service Routing
Adds Paytouchpayin as a payin option in service routing
"""

import sys
from database_pooled import get_db_connection

def setup_paytouchpayin_routing():
    """Add Paytouchpayin to service routing for testing"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔧 Setting up Paytouchpayin service routing...")
        
        # Check if Paytouchpayin routing already exists
        cursor.execute("""
            SELECT id, merchant_id, pg_partner, routing_type, priority, is_active
            FROM service_routing
            WHERE pg_partner = 'Paytouchpayin' AND service_type = 'PAYIN'
        """)
        
        existing = cursor.fetchall()
        
        if existing:
            print(f"\n✓ Found {len(existing)} existing Paytouchpayin routing(s):")
            for route in existing:
                route_id, merchant_id, pg_partner, routing_type, priority, is_active = route
                merchant = merchant_id or 'ALL_USERS'
                status = '✓ Active' if is_active else '✗ Inactive'
                print(f"  - ID: {route_id}, Merchant: {merchant}, Type: {routing_type}, Priority: {priority}, Status: {status}")
        else:
            print("\n⚠️ No Paytouchpayin routing found")
        
        # Ask if user wants to add a new routing
        print("\n" + "="*60)
        print("Add Paytouchpayin Routing Options:")
        print("="*60)
        print("1. Add for ALL_USERS (default routing for all merchants)")
        print("2. Add for SINGLE_USER (specific merchant)")
        print("3. Skip (configure manually in admin panel)")
        print("="*60)
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            # Add ALL_USERS routing
            priority = input("Enter priority (default: 10): ").strip() or "10"
            
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id, service_type, pg_partner, routing_type, 
                    priority, is_active, created_at
                ) VALUES (
                    NULL, 'PAYIN', 'Paytouchpayin', 'ALL_USERS',
                    %s, TRUE, NOW()
                )
            """, (priority,))
            
            conn.commit()
            print(f"\n✅ Added Paytouchpayin routing for ALL_USERS with priority {priority}")
            
        elif choice == '2':
            # Add SINGLE_USER routing
            merchant_id = input("Enter merchant_id: ").strip()
            priority = input("Enter priority (default: 10): ").strip() or "10"
            
            # Verify merchant exists
            cursor.execute("SELECT merchant_id, name FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"\n❌ Merchant {merchant_id} not found")
                cursor.close()
                conn.close()
                return
            
            merchant_id_val, merchant_name = merchant
            
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id, service_type, pg_partner, routing_type, 
                    priority, is_active, created_at
                ) VALUES (
                    %s, 'PAYIN', 'Paytouchpayin', 'SINGLE_USER',
                    %s, TRUE, NOW()
                )
            """, (merchant_id, priority))
            
            conn.commit()
            print(f"\n✅ Added Paytouchpayin routing for merchant {merchant_id} ({merchant_name}) with priority {priority}")
            
        else:
            print("\n⏭️ Skipping automatic routing setup")
            print("   Configure routing manually in admin panel: Service Routing")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Paytouchpayin Routing Setup Complete!")
        print("="*60)
        print("\n📋 Next Steps:")
        print("   1. Configure callback URL with Paytouchpayin:")
        print("      https://your-domain.com/api/paytouchpayin/callback")
        print("   2. Test order creation with a merchant account")
        print("   3. Monitor callbacks and transactions")
        print("")
        
    except Exception as e:
        print(f"\n❌ Error setting up routing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    setup_paytouchpayin_routing()
