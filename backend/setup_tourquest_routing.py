#!/usr/bin/env python3
"""
Setup Tourquest Service Routing
Configures Tourquest as the payment gateway for a merchant or all merchants
"""

from database import get_db_connection
import sys

def configure_tourquest_for_merchant(merchant_id):
    """Configure Tourquest for a specific merchant"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if merchant exists
            cursor.execute("SELECT merchant_id, full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant '{merchant_id}' not found")
                return False
            
            print(f"✓ Found merchant: {merchant['full_name']} ({merchant_id})")
            
            # Deactivate all other PAYIN gateways for this merchant
            cursor.execute("""
                UPDATE service_routing
                SET is_active = FALSE
                WHERE merchant_id = %s AND service_type = 'PAYIN'
            """, (merchant_id,))
            
            print(f"✓ Deactivated other PAYIN gateways for {merchant_id}")
            
            # Insert or update Tourquest routing
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id, service_type, routing_type, pg_partner, 
                    priority, is_active, created_by
                ) VALUES (
                    %s, 'PAYIN', 'SINGLE_USER', 'Tourquest', 1, TRUE, 'admin'
                )
                ON DUPLICATE KEY UPDATE
                    is_active = TRUE,
                    priority = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (merchant_id,))
            
            conn.commit()
            
            # Verify configuration
            cursor.execute("""
                SELECT * FROM service_routing
                WHERE merchant_id = %s AND service_type = 'PAYIN' AND is_active = TRUE
            """, (merchant_id,))
            
            routing = cursor.fetchone()
            
            if routing and routing['pg_partner'] == 'Tourquest':
                print(f"✅ Successfully configured Tourquest for merchant {merchant_id}")
                print(f"   Service Type: {routing['service_type']}")
                print(f"   Routing Type: {routing['routing_type']}")
                print(f"   PG Partner: {routing['pg_partner']}")
                print(f"   Priority: {routing['priority']}")
                print(f"   Status: {'Active' if routing['is_active'] else 'Inactive'}")
                return True
            else:
                print(f"❌ Failed to configure Tourquest for merchant {merchant_id}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()


def configure_tourquest_for_all():
    """Configure Tourquest as default for all merchants"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Deactivate all other ALL_USERS PAYIN gateways
            cursor.execute("""
                UPDATE service_routing
                SET is_active = FALSE
                WHERE merchant_id IS NULL 
                AND service_type = 'PAYIN'
                AND routing_type = 'ALL_USERS'
            """)
            
            print("✓ Deactivated other ALL_USERS PAYIN gateways")
            
            # Insert or update Tourquest routing
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id, service_type, routing_type, pg_partner, 
                    priority, is_active, created_by
                ) VALUES (
                    NULL, 'PAYIN', 'ALL_USERS', 'Tourquest', 1, TRUE, 'admin'
                )
                ON DUPLICATE KEY UPDATE
                    is_active = TRUE,
                    priority = 1,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            conn.commit()
            
            # Verify configuration
            cursor.execute("""
                SELECT * FROM service_routing
                WHERE merchant_id IS NULL 
                AND service_type = 'PAYIN' 
                AND routing_type = 'ALL_USERS'
                AND is_active = TRUE
            """)
            
            routing = cursor.fetchone()
            
            if routing and routing['pg_partner'] == 'Tourquest':
                print("✅ Successfully configured Tourquest as default for ALL merchants")
                print(f"   Service Type: {routing['service_type']}")
                print(f"   Routing Type: {routing['routing_type']}")
                print(f"   PG Partner: {routing['pg_partner']}")
                print(f"   Priority: {routing['priority']}")
                print(f"   Status: {'Active' if routing['is_active'] else 'Inactive'}")
                return True
            else:
                print("❌ Failed to configure Tourquest for all merchants")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()


def list_current_routing():
    """List current service routing configuration"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT sr.*, m.full_name as merchant_name
                FROM service_routing sr
                LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
                WHERE sr.service_type = 'PAYIN' AND sr.is_active = TRUE
                ORDER BY sr.routing_type, sr.merchant_id, sr.priority
            """)
            
            routes = cursor.fetchall()
            
            if not routes:
                print("No active PAYIN routing configured")
                return
            
            print("\n" + "=" * 80)
            print("CURRENT ACTIVE PAYIN ROUTING")
            print("=" * 80)
            
            for route in routes:
                merchant_info = route['merchant_name'] if route['merchant_name'] else "ALL MERCHANTS"
                merchant_id = route['merchant_id'] if route['merchant_id'] else "NULL"
                
                print(f"\nMerchant: {merchant_info} ({merchant_id})")
                print(f"  Routing Type: {route['routing_type']}")
                print(f"  PG Partner: {route['pg_partner']}")
                print(f"  Priority: {route['priority']}")
                print(f"  Status: {'Active' if route['is_active'] else 'Inactive'}")
            
            print("\n" + "=" * 80)
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()


def main():
    print("\n" + "=" * 80)
    print("TOURQUEST SERVICE ROUTING SETUP")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python setup_tourquest_routing.py <merchant_id>  - Configure for specific merchant")
        print("  python setup_tourquest_routing.py all            - Configure for all merchants")
        print("  python setup_tourquest_routing.py list           - List current routing")
        print("\nExample:")
        print("  python setup_tourquest_routing.py MERCH001")
        print("  python setup_tourquest_routing.py all")
        print("  python setup_tourquest_routing.py list")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_current_routing()
    elif command == "all":
        configure_tourquest_for_all()
    else:
        # Assume it's a merchant ID
        configure_tourquest_for_merchant(command)


if __name__ == "__main__":
    main()
