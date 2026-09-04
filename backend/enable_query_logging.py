#!/usr/bin/env python3
"""
Enable MySQL general query log to track all queries including DELETEs
"""

from database import get_db_connection

def enable_query_logging():
    """Enable MySQL general query log"""
    print("=" * 80)
    print("ENABLING MYSQL QUERY LOGGING")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check current logging status
            cursor.execute("SHOW VARIABLES LIKE 'general_log%'")
            current_settings = cursor.fetchall()
            
            print("\n📋 Current Query Log Settings:")
            for setting in current_settings:
                print(f"  {setting['Variable_name']}: {setting['Value']}")
            
            # Enable general log
            print("\n🔧 Enabling general query log...")
            cursor.execute("SET GLOBAL general_log = 'ON'")
            cursor.execute("SET GLOBAL general_log_file = '/var/log/mysql/general.log'")
            
            print("✅ Query logging enabled")
            print("\n📝 Log file location: /var/log/mysql/general.log")
            print("\nTo view the log:")
            print("  sudo tail -f /var/log/mysql/general.log")
            print("\nTo search for DELETE queries:")
            print("  sudo grep -i 'DELETE.*payout_transactions' /var/log/mysql/general.log")
            print("\nTo disable logging later:")
            print("  mysql -u root -p -e \"SET GLOBAL general_log = 'OFF';\"")
            
            print("\n⚠️  WARNING: General log can grow large quickly!")
            print("   Remember to disable it after debugging")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nYou may need to run this with root MySQL privileges:")
        print("  mysql -u root -p -e \"SET GLOBAL general_log = 'ON';\"")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    enable_query_logging()
