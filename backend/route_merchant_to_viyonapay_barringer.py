"""
Route merchant to Viyonapay Barringer configuration
"""
import sys
from database import get_db_connection

def route_merchant_to_viyonapay_barringer(merchant_id):
    """Route a merchant to use Viyonapay Barringer for payin"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if routing already exists
        cursor.execute("""
            SELECT id, pg_partner, is_active 
            FROM service_routing 
            WHERE merchant_id = %s AND service_type = 'PAYIN' AND routing_type = 'SINGLE_USER'
        """, (merchant_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing routing
            cursor.execute("""
                UPDATE service_routing 
                SET pg_partner = 'VIYONAPAY_BARRINGER', 
                    is_active = TRUE,
                    updated_at = NOW()
                WHERE merchant_id = %s AND service_type = 'PAYIN' AND routing_type = 'SINGLE_USER'
            """, (merchant_id,))
            print(f"✓ Updated merchant {merchant_id} routing to VIYONAPAY_BARRINGER")
            print(f"  Previous: {existing['pg_partner']}")
        else:
            # Create new routing
            cursor.execute("""
                INSERT INTO service_routing 
                (merchant_id, service_type, pg_partner, routing_type, is_active, created_at, updated_at)
                VALUES (%s, 'PAYIN', 'VIYONAPAY_BARRINGER', 'SINGLE_USER', TRUE, NOW(), NOW())
            """, (merchant_id,))
            print(f"✓ Created new routing for merchant {merchant_id} to VIYONAPAY_BARRINGER")
        
        conn.commit()
        
        # Verify the routing
        cursor.execute("""
            SELECT merchant_id, service_type, pg_partner, routing_type, is_active
            FROM service_routing
            WHERE merchant_id = %s AND service_type = 'PAYIN'
        """, (merchant_id,))
        
        routing = cursor.fetchone()
        print(f"\n✓ Current routing for merchant {merchant_id}:")
        print(f"  Service Type: {routing['service_type']}")
        print(f"  PG Partner: {routing['pg_partner']}")
        print(f"  Routing Type: {routing['routing_type']}")
        print(f"  Active: {routing['is_active']}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def route_merchant_to_viyonapay_truaxis(merchant_id):
    """Route a merchant back to Viyonapay Truaxis (original) for payin"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update routing to VIYONAPAY (Truaxis)
        cursor.execute("""
            UPDATE service_routing 
            SET pg_partner = 'VIYONAPAY', 
                is_active = TRUE,
                updated_at = NOW()
            WHERE merchant_id = %s AND service_type = 'PAYIN' AND routing_type = 'SINGLE_USER'
        """, (merchant_id,))
        
        if cursor.rowcount > 0:
            print(f"✓ Updated merchant {merchant_id} routing to VIYONAPAY (Truaxis)")
            conn.commit()
            
            # Verify the routing
            cursor.execute("""
                SELECT merchant_id, service_type, pg_partner, routing_type, is_active
                FROM service_routing
                WHERE merchant_id = %s AND service_type = 'PAYIN'
            """, (merchant_id,))
            
            routing = cursor.fetchone()
            print(f"\n✓ Current routing for merchant {merchant_id}:")
            print(f"  Service Type: {routing['service_type']}")
            print(f"  PG Partner: {routing['pg_partner']}")
            print(f"  Routing Type: {routing['routing_type']}")
            print(f"  Active: {routing['is_active']}")
        else:
            print(f"❌ No routing found for merchant {merchant_id}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Route to Barringer:  python route_merchant_to_viyonapay_barringer.py <merchant_id> barringer")
        print("  Route to Truaxis:    python route_merchant_to_viyonapay_barringer.py <merchant_id> truaxis")
        print("\nExample:")
        print("  python route_merchant_to_viyonapay_barringer.py 9876543210 barringer")
        print("  python route_merchant_to_viyonapay_barringer.py 9876543210 truaxis")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    config_type = sys.argv[2].lower() if len(sys.argv) > 2 else 'barringer'
    
    if config_type == 'truaxis':
        route_merchant_to_viyonapay_truaxis(merchant_id)
    else:
        route_merchant_to_viyonapay_barringer(merchant_id)
