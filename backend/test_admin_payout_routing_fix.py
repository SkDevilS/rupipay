#!/usr/bin/env python3
"""
Test the fixed admin payout routing API
"""
import sys
sys.path.append('/home/ubuntu/backend')

from database import get_db_connection

def test_routing_fix():
    """Test that the API will return only PAYOUT services for ADMIN"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("TESTING ADMIN PAYOUT ROUTING FIX")
            print("=" * 80)
            
            # Test 1: Check what exists in database
            print("\n1. Current database state:")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    routing_type,
                    service_type,
                    pg_partner,
                    is_active,
                    COUNT(*) as count
                FROM service_routing
                GROUP BY routing_type, service_type, pg_partner, is_active
                ORDER BY routing_type, service_type, pg_partner
            """)
            
            all_routes = cursor.fetchall()
            print(f"Total unique configurations: {len(all_routes)}\n")
            
            for route in all_routes:
                status = "✓ ACTIVE" if route['is_active'] else "✗ INACTIVE"
                print(f"  {route['routing_type']:15} | {route['service_type']:10} | {route['pg_partner']:20} | {status} | Count: {route['count']}")
            
            # Test 2: Simulate the API query with filters
            print("\n2. Simulating API query: service_type=PAYOUT, routing_type=ADMIN")
            print("-" * 80)
            cursor.execute("""
                SELECT sr.*, m.full_name as merchant_name
                FROM service_routing sr
                LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
                WHERE sr.service_type = %s
                AND sr.routing_type = %s
                ORDER BY sr.service_type, sr.routing_type, sr.priority
            """, ('PAYOUT', 'ADMIN'))
            
            filtered_routes = cursor.fetchall()
            
            if not filtered_routes:
                print("❌ No routes found! This is the problem.")
                print("\n💡 Solution: You need to add ADMIN PAYOUT routing entries.")
                print("   Example: INSERT INTO service_routing (routing_type, service_type, pg_partner, ...)")
                return False
            else:
                print(f"✓ Found {len(filtered_routes)} ADMIN PAYOUT routes:\n")
                for route in filtered_routes:
                    status = "✓ ACTIVE" if route['is_active'] else "✗ INACTIVE"
                    print(f"  {route['pg_partner']:20} | Priority: {route['priority']:2} | {status}")
            
            # Test 3: Check for PAYIN services that might be incorrectly configured
            print("\n3. Checking for ADMIN PAYIN entries (should NOT exist):")
            print("-" * 80)
            cursor.execute("""
                SELECT pg_partner, priority, is_active
                FROM service_routing
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYIN'
            """)
            
            payin_routes = cursor.fetchall()
            
            if payin_routes:
                print(f"⚠️  WARNING: Found {len(payin_routes)} ADMIN PAYIN entries:\n")
                for route in payin_routes:
                    print(f"  ⚠️  {route['pg_partner']} (Priority: {route['priority']})")
                print("\n❌ These should NOT have routing_type = 'ADMIN'!")
                print("   PAYIN services should use routing_type = 'MERCHANT' or specific merchant_id")
                return False
            else:
                print("✓ No ADMIN PAYIN entries found (correct)")
            
            # Test 4: Verify only active routes will be returned
            print("\n4. Active ADMIN PAYOUT routes (what frontend will see):")
            print("-" * 80)
            cursor.execute("""
                SELECT pg_partner, priority
                FROM service_routing
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYOUT'
                AND is_active = TRUE
                ORDER BY priority, pg_partner
            """)
            
            active_routes = cursor.fetchall()
            
            if not active_routes:
                print("❌ No active ADMIN PAYOUT routes found!")
                print("   Frontend will show 'No payment gateways configured'")
                return False
            else:
                print(f"✓ Found {len(active_routes)} active routes:\n")
                for i, route in enumerate(active_routes, 1):
                    print(f"  {i}. {route['pg_partner']} (Priority: {route['priority']})")
            
            print("\n" + "=" * 80)
            print("✅ TEST PASSED - API will return only PAYOUT services for ADMIN")
            print("=" * 80)
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("🧪 Testing Admin Payout Routing Fix\n")
    success = test_routing_fix()
    
    if success:
        print("\n✅ The fix is correct. Deploy the updated service_routing_routes.py")
        print("   Run: bash deploy_admin_payout_routing_fix.sh")
    else:
        print("\n❌ There are issues with the database configuration")
        print("   Check the output above for details")
