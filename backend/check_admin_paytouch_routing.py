#!/usr/bin/env python3
"""
Check if PayTouch admin routing exists and is active
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_admin_paytouch_routing():
    """Check PayTouch admin routing configuration"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("🔍 Checking admin payout routing configuration...")
            print()
            
            # Check all admin payout routes
            cursor.execute("""
                SELECT id, pg_partner, priority, is_active, created_at
                FROM service_routing
                WHERE routing_type = 'ADMIN'
                AND service_type = 'PAYOUT'
                ORDER BY priority, pg_partner
            """)
            
            routes = cursor.fetchall()
            
            if routes:
                print("📋 Current ADMIN payout routes:")
                paytouch_found = False
                for route in routes:
                    status = "✓ Active" if route['is_active'] else "✗ Inactive"
                    print(f"   - {route['pg_partner']}: Priority {route['priority']} [{status}] (ID: {route['id']})")
                    if route['pg_partner'] == 'PayTouch':
                        paytouch_found = True
                        if route['is_active']:
                            print("     ✅ PayTouch is configured and active")
                        else:
                            print("     ⚠️  PayTouch is configured but INACTIVE")
                
                if not paytouch_found:
                    print("   ❌ PayTouch routing NOT FOUND")
                    print()
                    print("💡 SOLUTION: Run the following command to add PayTouch:")
                    print("   python3 add_paytouch_admin_routing.py")
                    return False
                else:
                    return True
            else:
                print("❌ No admin payout routes found at all")
                print()
                print("💡 SOLUTION: Run the following command to add PayTouch:")
                print("   python3 add_paytouch_admin_routing.py")
                return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()

def check_frontend_api_endpoint():
    """Check if there's a specific API endpoint for admin gateways"""
    print("\n🔍 Checking API endpoints...")
    print()
    print("The frontend likely calls one of these endpoints to get payment gateways:")
    print("   1. GET /api/service-routing/pg-partners")
    print("   2. GET /api/admin/payment-gateways (if exists)")
    print("   3. GET /api/admin/payout-gateways (if exists)")
    print()
    print("💡 If PayTouch routing exists but still not showing, check:")
    print("   1. Frontend code filtering logic")
    print("   2. API endpoint used by admin personal payout page")
    print("   3. Browser cache/refresh")

if __name__ == '__main__':
    print("🔍 PayTouch Admin Routing Check")
    print("=" * 40)
    print()
    
    routing_ok = check_admin_paytouch_routing()
    check_frontend_api_endpoint()
    
    if not routing_ok:
        print("\n" + "=" * 40)
        print("❌ PayTouch is NOT configured for admin personal payouts")
        print("   Run: python3 add_paytouch_admin_routing.py")
    else:
        print("\n" + "=" * 40)
        print("✅ PayTouch routing is configured correctly")
        print("   If still not showing, check frontend/API issues")