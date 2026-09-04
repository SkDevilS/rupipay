"""
Route merchant 7679022140 to Paytouchpayin
"""

from database_pooled import get_db_connection

def route_merchant():
    merchant_id = '7679022140'
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"Routing merchant {merchant_id} to Paytouchpayin...")
        
        # Check if routing already exists
        cursor.execute("""
            SELECT id, is_active, priority 
            FROM service_routing 
            WHERE merchant_id = %s AND pg_partner = 'Paytouchpayin' AND service_type = 'PAYIN'
        """, (merchant_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            route_id, is_active, priority = existing
            print(f"✓ Routing already exists (ID: {route_id}, Active: {is_active}, Priority: {priority})")
            
            if not is_active:
                cursor.execute("""
                    UPDATE service_routing 
                    SET is_active = TRUE 
                    WHERE id = %s
                """, (route_id,))
                conn.commit()
                print("✓ Activated existing routing")
        else:
            # Insert new routing
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id, service_type, pg_partner, routing_type, 
                    priority, is_active, created_at
                ) VALUES (
                    %s, 'PAYIN', 'Paytouchpayin', 'SINGLE_USER',
                    1, TRUE, NOW()
                )
            """, (merchant_id,))
            conn.commit()
            print(f"✅ Created new routing for merchant {merchant_id}")
        
        # Verify routing
        cursor.execute("""
            SELECT id, merchant_id, pg_partner, routing_type, priority, is_active
            FROM service_routing
            WHERE merchant_id = %s AND service_type = 'PAYIN'
            ORDER BY priority
        """, (merchant_id,))
        
        routes = cursor.fetchall()
        print(f"\n📋 All PAYIN routes for merchant {merchant_id}:")
        for route in routes:
            route_id, mid, pg, rtype, prio, active = route
            status = "✓ ACTIVE" if active else "✗ INACTIVE"
            print(f"  - {pg}: Priority {prio}, {status}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Routing setup complete!")
        print("\n📝 Next steps:")
        print("   1. Restart backend: sudo systemctl restart moneyone-backend")
        print("   2. Test API with merchant JWT token")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    route_merchant()
