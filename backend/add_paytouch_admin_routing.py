#!/usr/bin/env python3
"""
Add PayTouch as a payout option for ADMIN personal payouts
This allows PayTouch to appear in the admin personal payout dropdown
"""

from database import get_db_connection

def add_paytouch_admin_routing():
    """Add PayTouch routing for admin personal payouts"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if PayTouch admin routing already exists
            cursor.execute("""
                SELECT id, is_active FROM service_routing
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYOUT'
                AND pg_partner = 'PayTouch'
            """)
            
            existing = cursor.fetchone()
            
            if existing:
                if existing['is_active']:
                    print("✅ PayTouch admin routing already exists and is active")
                    print(f"   Route ID: {existing['id']}")
                else:
                    # Activate existing route
                    cursor.execute("""
                        UPDATE service_routing
                        SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (existing['id'],))
                    conn.commit()
                    print("✅ PayTouch admin routing activated")
                    print(f"   Route ID: {existing['id']}")
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
                        'PayTouch',
                        1,
                        TRUE,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("✅ PayTouch admin routing created successfully")
                print(f"   Route ID: {cursor.lastrowid}")
            
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
    print("🔧 Adding PayTouch to Admin Personal Payout Options\n")
    success = add_paytouch_admin_routing()
    
    if success:
        print("\n✅ Configuration complete!")
        print("\n📝 Next steps:")
        print("   1. Restart the backend server")
        print("   2. Login to admin panel")
        print("   3. Go to Personal Payout page")
        print("   4. PayTouch should now appear in the Payment Gateway dropdown")
    else:
        print("\n❌ Configuration failed. Please check the error messages above.")
