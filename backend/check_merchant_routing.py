#!/usr/bin/env python3
"""
Check which payment gateway a merchant is using
"""

from database import get_db_connection
import sys

def check_merchant_routing(merchant_id):
    """Check which PG partner is configured for a merchant"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get merchant info
            cursor.execute("""
                SELECT merchant_id, full_name, email, merchant_type
                FROM merchants WHERE merchant_id = %s
            """, (merchant_id,))
            
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant '{merchant_id}' not found")
                return
            
            print("\n" + "=" * 80)
            print(f"MERCHANT: {merchant['full_name']} ({merchant_id})")
            print("=" * 80)
            
            # Check SINGLE_USER routing
            cursor.execute("""
                SELECT * FROM service_routing
                WHERE merchant_id = %s 
                AND service_type = 'PAYIN'
                ORDER BY is_active DESC, priority ASC
            """, (merchant_id,))
            
            single_routes = cursor.fetchall()
            
            if single_routes:
                print("\n📋 SINGLE_USER Routing (Merchant-Specific):")
                for route in single_routes:
                    status = "✅ ACTIVE" if route['is_active'] else "❌ INACTIVE"
                    print(f"  {status} - {route['pg_partner']} (Priority: {route['priority']})")
            else:
                print("\n📋 SINGLE_USER Routing: None configured")
            
            # Check ALL_USERS routing
            cursor.execute("""
                SELECT * FROM service_routing
                WHERE merchant_id IS NULL 
                AND service_type = 'PAYIN'
                AND routing_type = 'ALL_USERS'
                ORDER BY is_active DESC, priority ASC
            """)
            
            all_routes = cursor.fetchall()
            
            if all_routes:
                print("\n📋 ALL_USERS Routing (Default for all merchants):")
                for route in all_routes:
                    status = "✅ ACTIVE" if route['is_active'] else "❌ INACTIVE"
                    print(f"  {status} - {route['pg_partner']} (Priority: {route['priority']})")
            else:
                print("\n📋 ALL_USERS Routing: None configured")
            
            # Determine which gateway will be used
            print("\n" + "=" * 80)
            print("RESULT:")
            print("=" * 80)
            
            active_single = [r for r in single_routes if r['is_active']]
            active_all = [r for r in all_routes if r['is_active']]
            
            if active_single:
                gateway = active_single[0]['pg_partner']
                print(f"✅ This merchant will use: {gateway} (SINGLE_USER routing)")
            elif active_all:
                gateway = active_all[0]['pg_partner']
                print(f"✅ This merchant will use: {gateway} (ALL_USERS routing)")
            else:
                print("⚠️  No active routing found - will default to PayU")
            
            print("\n" + "=" * 80)
            
            # Show how to fix
            if not active_single or (active_single and active_single[0]['pg_partner'] != 'Tourquest'):
                print("\n💡 TO USE TOURQUEST FOR THIS MERCHANT:")
                print(f"   python setup_tourquest_routing.py {merchant_id}")
                print("\n💡 OR USE SQL:")
                print(f"""
   UPDATE service_routing SET is_active = FALSE 
   WHERE merchant_id = '{merchant_id}' AND service_type = 'PAYIN';
   
   INSERT INTO service_routing 
   (merchant_id, service_type, routing_type, pg_partner, priority, is_active, created_by)
   VALUES ('{merchant_id}', 'PAYIN', 'SINGLE_USER', 'Tourquest', 1, TRUE, 'admin')
   ON DUPLICATE KEY UPDATE is_active = TRUE;
                """)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python check_merchant_routing.py <merchant_id>")
        print("Example: python check_merchant_routing.py MERCH001")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    check_merchant_routing(merchant_id)
