"""
Test API Ledger endpoint to diagnose the 500 error
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def test_get_apis():
    """Test the /apis endpoint logic"""
    try:
        service_type = 'PAYIN'
        
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        print("✅ Database connected")
        
        try:
            with conn.cursor() as cursor:
                # Get unique APIs from service routing
                query = """
                    SELECT DISTINCT pg_partner
                    FROM service_routing
                    WHERE service_type = %s
                    ORDER BY pg_partner
                """
                print(f"\n📋 Executing query: {query}")
                print(f"   Parameters: service_type={service_type}")
                
                cursor.execute(query, (service_type,))
                apis = cursor.fetchall()
                
                print(f"\n✅ Query executed successfully")
                print(f"   Found {len(apis)} APIs")
                
                # Format response
                api_list = []
                for api in apis:
                    pg_partner = api['pg_partner']
                    api_list.append({
                        'id': pg_partner,
                        'name': pg_partner
                    })
                    print(f"   - {pg_partner}")
                
                print(f"\n✅ Response formatted successfully")
                print(f"\nFinal API list:")
                for api in api_list:
                    print(f"   {api}")
                
        finally:
            conn.close()
            print("\n✅ Database connection closed")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing API Ledger /apis endpoint")
    print("=" * 60)
    test_get_apis()
