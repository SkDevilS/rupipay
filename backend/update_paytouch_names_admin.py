#!/usr/bin/env python3
"""
Update PayTouch service names in admin personal payout
Changes:
- PayTouch → paytouch_truaxis
- Paytouch2 → paytouch_grosmart
"""

from database import get_db_connection

def update_paytouch_names():
    """Update PayTouch service names in service_routing table"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("🔧 Updating PayTouch service names for admin personal payout...")
            print("=" * 60)
            
            # Show current admin payout routes
            print("\n📋 Current ADMIN payout routes:")
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
            
            # Update PayTouch to paytouch_truaxis
            print("\n🔄 Updating PayTouch → paytouch_truaxis...")
            cursor.execute("""
                UPDATE service_routing
                SET pg_partner = 'paytouch_truaxis', updated_at = CURRENT_TIMESTAMP
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYOUT'
                AND pg_partner = 'PayTouch'
            """)
            paytouch_updated = cursor.rowcount
            
            # Update Paytouch2 to paytouch_grosmart
            print("🔄 Updating Paytouch2 → paytouch_grosmart...")
            cursor.execute("""
                UPDATE service_routing
                SET pg_partner = 'paytouch_grosmart', updated_at = CURRENT_TIMESTAMP
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYOUT'
                AND pg_partner = 'Paytouch2'
            """)
            paytouch2_updated = cursor.rowcount
            
            conn.commit()
            
            print(f"✅ PayTouch updated: {paytouch_updated} records")
            print(f"✅ Paytouch2 updated: {paytouch2_updated} records")
            
            # Show updated admin payout routes
            print("\n📋 Updated ADMIN payout routes:")
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
    print("🔧 Updating PayTouch Service Names for Admin Personal Payout\n")
    success = update_paytouch_names()
    
    if success:
        print("\n✅ Update complete!")
        print("\n📝 Changes made:")
        print("   • PayTouch → paytouch_truaxis")
        print("   • Paytouch2 → paytouch_grosmart")
        print("\n📍 Where to see the changes:")
        print("   1. Login to admin panel")
        print("   2. Go to Personal Payout page")
        print("   3. Check the Payment Gateway dropdown")
        print("   4. You should see 'paytouch_truaxis' and 'paytouch_grosmart'")
    else:
        print("\n❌ Update failed. Please check the error messages above.")