#!/usr/bin/env python3
"""
Add admin payout gateway options to service_routing table
This creates the entries that the admin personal payout dropdown will fetch
"""

from database import get_db_connection

def add_admin_payout_gateways():
    """Add admin payout gateway options to service_routing table"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("🔧 Adding admin payout gateway options...")
            print("=" * 50)
            
            # List of admin payout gateways with new names
            gateways = [
                {'pg_partner': 'Mudrape', 'priority': 1},
                {'pg_partner': 'paytouch_truaxis', 'priority': 2},
                {'pg_partner': 'paytouch_grosmart', 'priority': 3},
                {'pg_partner': 'PayU', 'priority': 4}
            ]
            
            for gateway in gateways:
                # Check if gateway already exists
                cursor.execute("""
                    SELECT id, is_active FROM service_routing
                    WHERE routing_type = 'ADMIN'
                    AND service_type = 'PAYOUT'
                    AND pg_partner = %s
                """, (gateway['pg_partner'],))
                
                existing = cursor.fetchone()
                
                if existing:
                    if existing['is_active']:
                        print(f"✅ {gateway['pg_partner']} already exists and is active")
                    else:
                        # Activate existing route
                        cursor.execute("""
                            UPDATE service_routing
                            SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (existing['id'],))
                        print(f"✅ {gateway['pg_partner']} activated")
                else:
                    # Insert new routing
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
                            %s,
                            %s,
                            TRUE,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                    """, (gateway['pg_partner'], gateway['priority']))
                    print(f"✅ {gateway['pg_partner']} added successfully")
            
            conn.commit()
            
            # Show all admin payout routes
            print("\n📋 All ADMIN payout routes:")
            cursor.execute("""
                SELECT id, pg_partner, priority, is_active
                FROM service_routing
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYOUT'
                ORDER BY priority, pg_partner
            """)
            
            routes = cursor.fetchall()
            if routes:
                for route in routes:
                    status = "✓ Active" if route['is_active'] else "✗ Inactive"
                    print(f"   - {route['pg_partner']}: Priority {route['priority']} [{status}]")
            else:
                print("   No admin payout routes found")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("🔧 Adding Admin Payout Gateway Options\n")
    success = add_admin_payout_gateways()
    
    if success:
        print("\n✅ Configuration complete!")
        print("\n📝 Next steps:")
        print("   1. Restart the backend server")
        print("   2. Login to admin panel")
        print("   3. Go to Personal Payout page")
        print("   4. You should see 'paytouch_truaxis' and 'paytouch_grosmart' in the dropdown")
    else:
        print("\n❌ Configuration failed. Please check the error messages above.")