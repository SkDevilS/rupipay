#!/usr/bin/env python3
"""
Check service_routing table for admin payout configuration
"""
import sys
sys.path.append('/home/ubuntu/backend')

from database import get_db_connection

def check_admin_payout_routing():
    """Check what's configured for admin payout"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("CHECKING ADMIN PAYOUT ROUTING CONFIGURATION")
            print("=" * 80)
            
            # Check all ADMIN routing entries
            print("\n1. All ADMIN routing entries:")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    route_id,
                    merchant_id,
                    routing_type,
                    service_type,
                    pg_partner,
                    priority,
                    is_active
                FROM service_routing
                WHERE routing_type = 'ADMIN'
                ORDER BY service_type, priority, pg_partner
            """)
            
            admin_routes = cursor.fetchall()
            
            if not admin_routes:
                print("❌ No ADMIN routing entries found!")
            else:
                print(f"Found {len(admin_routes)} ADMIN routing entries:\n")
                for route in admin_routes:
                    print(f"  Route ID: {route['route_id']}")
                    print(f"  Merchant ID: {route['merchant_id']}")
                    print(f"  Routing Type: {route['routing_type']}")
                    print(f"  Service Type: {route['service_type']}")
                    print(f"  PG Partner: {route['pg_partner']}")
                    print(f"  Priority: {route['priority']}")
                    print(f"  Active: {route['is_active']}")
                    print()
            
            # Check specifically for ADMIN + PAYOUT
            print("\n2. ADMIN PAYOUT entries (what API returns):")
            print("-" * 80)
            cursor.execute("""
                SELECT pg_partner, priority, is_active
                FROM service_routing
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYOUT'
                AND is_active = TRUE
                ORDER BY priority, pg_partner
            """)
            
            payout_routes = cursor.fetchall()
            
            if not payout_routes:
                print("❌ No ADMIN PAYOUT entries found!")
                print("\n💡 This is the problem - no payout services configured for admin!")
            else:
                print(f"Found {len(payout_routes)} ADMIN PAYOUT entries:\n")
                for route in payout_routes:
                    print(f"  ✓ {route['pg_partner']} (Priority: {route['priority']})")
            
            # Check for ADMIN + PAYIN (should NOT appear in personal payout)
            print("\n3. ADMIN PAYIN entries (should NOT appear in personal payout):")
            print("-" * 80)
            cursor.execute("""
                SELECT pg_partner, priority, is_active
                FROM service_routing
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYIN'
                AND is_active = TRUE
                ORDER BY priority, pg_partner
            """)
            
            payin_routes = cursor.fetchall()
            
            if payin_routes:
                print(f"⚠️  Found {len(payin_routes)} ADMIN PAYIN entries:\n")
                for route in payin_routes:
                    print(f"  ⚠️  {route['pg_partner']} (Priority: {route['priority']})")
                print("\n❌ These should NOT have routing_type = 'ADMIN'!")
            else:
                print("✓ No ADMIN PAYIN entries (correct)")
            
            # Check all service_routing entries
            print("\n4. All service_routing entries:")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    routing_type,
                    service_type,
                    pg_partner,
                    COUNT(*) as count
                FROM service_routing
                GROUP BY routing_type, service_type, pg_partner
                ORDER BY routing_type, service_type, pg_partner
            """)
            
            all_routes = cursor.fetchall()
            
            print(f"Total unique configurations: {len(all_routes)}\n")
            for route in all_routes:
                print(f"  {route['routing_type']:15} | {route['service_type']:10} | {route['pg_partner']:20} | Count: {route['count']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("🔍 Checking Admin Payout Routing Configuration\n")
    check_admin_payout_routing()
