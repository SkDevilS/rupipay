#!/usr/bin/env python3
"""
Add Paytouch2_Grosmart back to Payout2 Service Routing List
This script adds Paytouch2_Grosmart as an available payout gateway for admin personal payout
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def add_paytouch2_to_payout_list():
    """Add Paytouch2_Grosmart to the admin payout gateways list"""
    
    print("=" * 70)
    print("ADD PAYTOUCH2_GROSMART TO PAYOUT2 SERVICE ROUTING")
    print("=" * 70)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if Paytouch2_Grosmart routing exists
            print("\n1. Checking existing Paytouch2_Grosmart routing...")
            cursor.execute("""
                SELECT id, pg_partner, service_type, routing_type, is_active, priority
                FROM service_routing
                WHERE pg_partner IN ('PAYTOUCH2', 'PAYTOUCH_GROSMART', 'Paytouch2_Grosmart')
                AND service_type = 'PAYOUT'
            """)
            existing_routes = cursor.fetchall()
            
            if existing_routes:
                print(f"   ✓ Found {len(existing_routes)} existing Paytouch2 payout route(s):")
                for route in existing_routes:
                    print(f"     - ID: {route['id']}, Partner: {route['pg_partner']}, "
                          f"Type: {route['routing_type']}, Active: {route['is_active']}, "
                          f"Priority: {route['priority']}")
            else:
                print("   ℹ No existing Paytouch2 payout routes found")
            
            # Add or update Paytouch2_Grosmart for ALL_USERS payout routing
            print("\n2. Adding/Updating Paytouch2_Grosmart to payout routing...")
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
                    'ALL_USERS',
                    'PAYTOUCH2',
                    2,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON DUPLICATE KEY UPDATE
                    is_active = TRUE,
                    priority = 2,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            affected_rows = cursor.rowcount
            conn.commit()
            
            if affected_rows > 0:
                print(f"   ✓ Successfully added/updated Paytouch2_Grosmart payout routing")
            else:
                print("   ℹ No changes made (route already exists)")
            
            # Verify the change
            print("\n3. Verifying Paytouch2_Grosmart is now in payout routing...")
            cursor.execute("""
                SELECT id, pg_partner, service_type, routing_type, is_active, priority
                FROM service_routing
                WHERE service_type = 'PAYOUT'
                AND routing_type = 'ALL_USERS'
                ORDER BY priority ASC
            """)
            payout_routes = cursor.fetchall()
            
            print(f"\n   Current PAYOUT routing configuration (ALL_USERS):")
            for route in payout_routes:
                status = "✓ ACTIVE" if route['is_active'] else "✗ INACTIVE"
                print(f"     {status} - Priority {route['priority']}: {route['pg_partner']}")
            
            # Check if Paytouch2 is in the list
            paytouch2_found = any(
                route['pg_partner'] in ['PAYTOUCH2', 'PAYTOUCH_GROSMART', 'Paytouch2_Grosmart'] 
                for route in payout_routes
            )
            
            if paytouch2_found:
                print("\n✅ SUCCESS: Paytouch2_Grosmart is now available in payout routing!")
                print("\n📍 Where to see this:")
                print("   1. Admin Panel → Service Routing")
                print("   2. Admin Panel → Personal Payout → Select Gateway dropdown")
                print("   3. API: GET /api/routing/services")
                return True
            else:
                print("\n⚠️ WARNING: Paytouch2_Grosmart was not found in payout routing")
                return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("\n🚀 Starting Paytouch2_Grosmart payout routing addition...\n")
    success = add_paytouch2_to_payout_list()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ PAYTOUCH2_GROSMART SUCCESSFULLY ADDED TO PAYOUT ROUTING")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Restart backend: sudo systemctl restart moneyone-backend")
        print("2. Test in admin panel: Personal Payout → Select Paytouch2_Grosmart")
        print("3. Verify API response: GET /api/routing/admin/payout-gateways")
    else:
        print("\n" + "=" * 70)
        print("❌ FAILED TO ADD PAYTOUCH2_GROSMART")
        print("=" * 70)
        sys.exit(1)
