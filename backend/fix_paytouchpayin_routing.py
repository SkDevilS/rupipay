#!/usr/bin/env python3
"""
Fix Paytouchpayin Routing Configuration
Ensures Paytouchpayin is properly configured in service_routing table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def fix_paytouchpayin_routing():
    """Fix Paytouchpayin routing configuration"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            print("🔧 Checking Paytouchpayin routing configuration...")
            
            # Check if Paytouchpayin routing exists for merchant 7679022140
            cursor.execute("""
                SELECT id, is_active, priority FROM service_routing 
                WHERE merchant_id = '7679022140' 
                AND pg_partner = 'Paytouchpayin' 
                AND service_type = 'PAYIN'
            """)
            
            existing = cursor.fetchone()
            
            if existing:
                print(f"✓ Paytouchpayin routing exists for merchant 7679022140")
                print(f"  ID: {existing['id']}, Active: {existing['is_active']}, Priority: {existing['priority']}")
                
                if not existing['is_active']:
                    print("  Activating routing...")
                    cursor.execute("""
                        UPDATE service_routing 
                        SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (existing['id'],))
                    print("  ✓ Activated")
                
                # Deactivate other gateways for this merchant
                cursor.execute("""
                    UPDATE service_routing
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE merchant_id = '7679022140'
                    AND service_type = 'PAYIN'
                    AND pg_partner != 'Paytouchpayin'
                """)
                
                if cursor.rowcount > 0:
                    print(f"  ✓ Deactivated {cursor.rowcount} other gateway(s)")
                
            else:
                print("  Creating new Paytouchpayin routing...")
                
                # Deactivate all other gateways first
                cursor.execute("""
                    UPDATE service_routing
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE merchant_id = '7679022140'
                    AND service_type = 'PAYIN'
                """)
                
                # Insert new routing
                cursor.execute("""
                    INSERT INTO service_routing (
                        merchant_id, service_type, routing_type, pg_partner, priority, is_active
                    ) VALUES (
                        '7679022140', 'PAYIN', 'SINGLE_USER', 'Paytouchpayin', 1, TRUE
                    )
                """)
                
                print("  ✓ Created new routing")
            
            conn.commit()
            
            # Show final routing configuration
            cursor.execute("""
                SELECT pg_partner, routing_type, is_active, priority
                FROM service_routing 
                WHERE merchant_id = '7679022140' AND service_type = 'PAYIN'
                ORDER BY priority
            """)
            
            routes = cursor.fetchall()
            
            print(f"\n📋 PAYIN routing for merchant 7679022140:")
            print("Gateway         | Type        | Active | Priority")
            print("----------------|-------------|--------|----------")
            for route in routes:
                status = "✓" if route['is_active'] else "✗"
                print(f"{route['pg_partner']:<15} | {route['routing_type']:<11} | {status:<6} | {route['priority']}")
            
            print("\n✅ Paytouchpayin routing configuration fixed!")
            return True
            
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Paytouchpayin Routing Fix")
    print("=" * 50)
    
    if fix_paytouchpayin_routing():
        print("\n✅ Fix completed successfully!")
        print("\nNext steps:")
        print("1. Restart backend: sudo systemctl restart moneyone-backend")
        print("2. Test API with merchant JWT token")
        print("3. Verify QR generation works")
    else:
        print("\n❌ Fix failed!")
        sys.exit(1)
