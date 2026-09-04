"""
Setup Vega routing for a merchant
"""

from database import get_db_connection
import sys

def setup_vega_routing(merchant_id):
    """Setup Vega routing for a specific merchant"""
    
    print("=" * 80)
    print(f"Setting up Vega Routing for Merchant: {merchant_id}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if merchant exists
            cursor.execute("""
                SELECT merchant_id, full_name, scheme_id, is_active
                FROM merchants
                WHERE merchant_id = %s
            """, (merchant_id,))
            
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"ERROR: Merchant {merchant_id} not found")
                return False
            
            print(f"\nMerchant: {merchant['full_name']}")
            print(f"Scheme ID: {merchant['scheme_id']}")
            print(f"Active: {merchant['is_active']}")
            
            # Check if scheme exists
            if not merchant['scheme_id']:
                print("\n⚠ WARNING: Merchant has no scheme assigned!")
                print("Please assign a scheme first using admin dashboard")
                return False
            
            # Verify PAYIN scheme exists
            cursor.execute("""
                SELECT * FROM schemes
                WHERE scheme_id = %s AND service_type = 'PAYIN'
            """, (merchant['scheme_id'],))
            
            scheme = cursor.fetchone()
            if not scheme:
                print(f"\n⚠ WARNING: No PAYIN scheme found for scheme_id: {merchant['scheme_id']}")
                print("Please configure a PAYIN scheme first")
                return False
            
            print(f"\nPAYIN Scheme: {scheme['charge_type']} - {scheme['charge_value']}")
            
            # Check existing routing
            cursor.execute("""
                SELECT * FROM service_routing
                WHERE merchant_id = %s AND service_type = 'PAYIN'
            """, (merchant_id,))
            
            existing_routes = cursor.fetchall()
            
            if existing_routes:
                print(f"\nExisting routing found:")
                for route in existing_routes:
                    print(f"  - {route['pg_partner']} (Active: {route['is_active']}, Priority: {route['priority']})")
                
                # Deactivate all existing PAYIN routes
                cursor.execute("""
                    UPDATE service_routing
                    SET is_active = FALSE
                    WHERE merchant_id = %s AND service_type = 'PAYIN'
                """, (merchant_id,))
                print("\n✓ Deactivated all existing PAYIN routes")
            
            # Check if Vega route exists
            cursor.execute("""
                SELECT * FROM service_routing
                WHERE merchant_id = %s AND service_type = 'PAYIN' AND pg_partner = 'Vega'
            """, (merchant_id,))
            
            vega_route = cursor.fetchone()
            
            if vega_route:
                # Activate existing Vega route
                cursor.execute("""
                    UPDATE service_routing
                    SET is_active = TRUE, priority = 1
                    WHERE id = %s
                """, (vega_route['id'],))
                print("\n✓ Activated existing Vega route")
            else:
                # Create new Vega route
                cursor.execute("""
                    INSERT INTO service_routing (merchant_id, service_type, routing_type, pg_partner, priority, is_active)
                    VALUES (%s, 'PAYIN', 'SINGLE_USER', 'Vega', 1, TRUE)
                """, (merchant_id,))
                print("\n✓ Created new Vega route")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("SUCCESS - Vega routing configured!")
            print("=" * 80)
            print(f"\nMerchant {merchant_id} will now use Vega for PAYIN transactions")
            
            return True
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python setup_vega_routing.py <merchant_id>")
        print("Example: python setup_vega_routing.py 9000000001")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    setup_vega_routing(merchant_id)
