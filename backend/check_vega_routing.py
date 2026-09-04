"""
Check Vega routing configuration for a merchant
"""

from database import get_db_connection

def check_vega_routing():
    """Check if Vega routing is configured"""
    
    print("=" * 80)
    print("Checking Vega Routing Configuration")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check all merchants
            cursor.execute("""
                SELECT merchant_id, full_name, scheme_id, is_active
                FROM merchants
                ORDER BY merchant_id
            """)
            
            merchants = cursor.fetchall()
            
            print(f"\nTotal Merchants: {len(merchants)}")
            print("-" * 80)
            
            for merchant in merchants:
                print(f"\nMerchant: {merchant['full_name']} ({merchant['merchant_id']})")
                print(f"  Scheme ID: {merchant['scheme_id']}")
                print(f"  Active: {merchant['is_active']}")
                
                # Check scheme details
                if merchant['scheme_id']:
                    cursor.execute("""
                        SELECT * FROM schemes
                        WHERE scheme_id = %s AND service_type = 'PAYIN'
                    """, (merchant['scheme_id'],))
                    
                    scheme = cursor.fetchone()
                    if scheme:
                        print(f"  Payin Scheme: {scheme['charge_type']} - {scheme['charge_value']}")
                    else:
                        print(f"  ⚠ No PAYIN scheme found for scheme_id: {merchant['scheme_id']}")
                else:
                    print(f"  ⚠ No scheme assigned")
                
                # Check service routing
                cursor.execute("""
                    SELECT * FROM service_routing
                    WHERE merchant_id = %s AND service_type = 'PAYIN' AND is_active = TRUE
                """, (merchant['merchant_id'],))
                
                routing = cursor.fetchone()
                if routing:
                    print(f"  Routing: {routing['pg_partner']} (Priority: {routing['priority']})")
                else:
                    print(f"  No specific routing (will use default)")
            
            # Check ALL_USERS routing
            print("\n" + "=" * 80)
            print("ALL_USERS Routing Configuration")
            print("=" * 80)
            
            cursor.execute("""
                SELECT * FROM service_routing
                WHERE merchant_id IS NULL AND service_type = 'PAYIN' AND is_active = TRUE
                ORDER BY priority
            """)
            
            all_users_routing = cursor.fetchall()
            if all_users_routing:
                for route in all_users_routing:
                    print(f"  {route['pg_partner']} (Priority: {route['priority']})")
            else:
                print("  No ALL_USERS routing configured")
            
            print("\n" + "=" * 80)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    check_vega_routing()
