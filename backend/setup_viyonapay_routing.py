"""
Setup VIYONAPAY in Service Routing
Adds VIYONAPAY as a payin service option
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def setup_viyonapay_routing():
    """Add VIYONAPAY to service routing options"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            print("🔍 Checking if VIYONAPAY routing already exists...")
            
            # Check if VIYONAPAY routing exists
            cursor.execute("""
                SELECT COUNT(*) as count FROM service_routing
                WHERE pg_partner = 'VIYONAPAY' AND service_type = 'PAYIN'
            """)
            
            result = cursor.fetchone()
            
            if result['count'] > 0:
                print(f"⚠️  VIYONAPAY routing already exists ({result['count']} entries)")
                print("   No changes needed.")
                return True
            
            print("📝 Adding VIYONAPAY to service routing...")
            
            # Add VIYONAPAY as an available option (inactive by default)
            # Admin can activate it from the admin panel
            cursor.execute("""
                INSERT INTO service_routing (
                    merchant_id,
                    service_type,
                    pg_partner,
                    routing_type,
                    priority,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (
                    NULL,
                    'PAYIN',
                    'VIYONAPAY',
                    'ALL_USERS',
                    999,
                    FALSE,
                    NOW(),
                    NOW()
                )
            """)
            
            conn.commit()
            
            print("✅ VIYONAPAY added to service routing successfully!")
            print("")
            print("📋 Next Steps:")
            print("  1. Go to Admin Panel → Service Routing")
            print("  2. Find VIYONAPAY entry")
            print("  3. Set priority and activate when ready")
            print("")
            
            return True
            
    except Exception as e:
        print(f"❌ Error setting up VIYONAPAY routing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("="*60)
    print("VIYONAPAY Service Routing Setup")
    print("="*60)
    print("")
    
    success = setup_viyonapay_routing()
    
    if success:
        print("")
        print("="*60)
        print("✅ Setup Complete!")
        print("="*60)
    else:
        print("")
        print("="*60)
        print("❌ Setup Failed!")
        print("="*60)
        sys.exit(1)
