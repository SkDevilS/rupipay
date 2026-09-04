"""
Reset Activity Logs
Clears all activity logs from the admin_activity_logs table
"""

from database import get_db_connection
from datetime import datetime

def reset_activity_logs():
    """Clear all activity logs"""
    try:
        print("=" * 80)
        print("Reset Activity Logs")
        print("=" * 80)
        
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Check current count
                cursor.execute("SELECT COUNT(*) as count FROM admin_activity_logs")
                current_count = cursor.fetchone()['count']
                
                print(f"\nCurrent activity logs count: {current_count}")
                
                if current_count == 0:
                    print("No activity logs to delete.")
                    return True
                
                # Confirm deletion
                print(f"\n⚠️  WARNING: This will delete ALL {current_count} activity logs!")
                confirm = input("Are you sure you want to continue? (yes/no): ")
                
                if confirm.lower() != 'yes':
                    print("Operation cancelled.")
                    return False
                
                # Delete all activity logs
                print("\nDeleting activity logs...")
                cursor.execute("DELETE FROM admin_activity_logs")
                conn.commit()
                
                # Verify deletion
                cursor.execute("SELECT COUNT(*) as count FROM admin_activity_logs")
                new_count = cursor.fetchone()['count']
                
                print(f"✓ Activity logs deleted successfully")
                print(f"  Before: {current_count} logs")
                print(f"  After: {new_count} logs")
                
                # Reset auto-increment
                print("\nResetting auto-increment counter...")
                cursor.execute("ALTER TABLE admin_activity_logs AUTO_INCREMENT = 1")
                conn.commit()
                print("✓ Auto-increment reset to 1")
                
                return True
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def reset_specific_admin_logs(admin_id):
    """Clear activity logs for a specific admin"""
    try:
        print("=" * 80)
        print(f"Reset Activity Logs for Admin: {admin_id}")
        print("=" * 80)
        
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Check current count for this admin
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM admin_activity_logs 
                    WHERE admin_id = %s
                """, (admin_id,))
                current_count = cursor.fetchone()['count']
                
                print(f"\nCurrent activity logs for {admin_id}: {current_count}")
                
                if current_count == 0:
                    print(f"No activity logs found for admin: {admin_id}")
                    return True
                
                # Confirm deletion
                print(f"\n⚠️  WARNING: This will delete {current_count} activity logs for {admin_id}!")
                confirm = input("Are you sure you want to continue? (yes/no): ")
                
                if confirm.lower() != 'yes':
                    print("Operation cancelled.")
                    return False
                
                # Delete activity logs for this admin
                print(f"\nDeleting activity logs for {admin_id}...")
                cursor.execute("""
                    DELETE FROM admin_activity_logs 
                    WHERE admin_id = %s
                """, (admin_id,))
                conn.commit()
                
                # Verify deletion
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM admin_activity_logs 
                    WHERE admin_id = %s
                """, (admin_id,))
                new_count = cursor.fetchone()['count']
                
                print(f"✓ Activity logs deleted successfully for {admin_id}")
                print(f"  Before: {current_count} logs")
                print(f"  After: {new_count} logs")
                
                return True
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def reset_old_logs(days=30):
    """Delete activity logs older than specified days"""
    try:
        print("=" * 80)
        print(f"Reset Activity Logs Older Than {days} Days")
        print("=" * 80)
        
        conn = get_db_connection()
        if not conn:
            print("ERROR: Database connection failed")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Check current count of old logs
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM admin_activity_logs 
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days,))
                current_count = cursor.fetchone()['count']
                
                print(f"\nActivity logs older than {days} days: {current_count}")
                
                if current_count == 0:
                    print(f"No activity logs older than {days} days.")
                    return True
                
                # Confirm deletion
                print(f"\n⚠️  WARNING: This will delete {current_count} old activity logs!")
                confirm = input("Are you sure you want to continue? (yes/no): ")
                
                if confirm.lower() != 'yes':
                    print("Operation cancelled.")
                    return False
                
                # Delete old activity logs
                print(f"\nDeleting activity logs older than {days} days...")
                cursor.execute("""
                    DELETE FROM admin_activity_logs 
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days,))
                conn.commit()
                
                # Verify deletion
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM admin_activity_logs 
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days,))
                new_count = cursor.fetchone()['count']
                
                print(f"✓ Old activity logs deleted successfully")
                print(f"  Before: {current_count} logs")
                print(f"  After: {new_count} logs")
                
                return True
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    
    print("\nActivity Logs Reset Tool")
    print("=" * 80)
    print("Options:")
    print("1. Reset ALL activity logs")
    print("2. Reset logs for specific admin")
    print("3. Reset logs older than X days")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        option = sys.argv[1]
        
        if option == '1' or option == 'all':
            reset_activity_logs()
        elif option == '2' or option == 'admin':
            if len(sys.argv) > 2:
                admin_id = sys.argv[2]
                reset_specific_admin_logs(admin_id)
            else:
                admin_id = input("Enter admin ID: ")
                reset_specific_admin_logs(admin_id)
        elif option == '3' or option == 'old':
            if len(sys.argv) > 2:
                days = int(sys.argv[2])
                reset_old_logs(days)
            else:
                days = int(input("Enter number of days: "))
                reset_old_logs(days)
        else:
            print("Invalid option")
    else:
        choice = input("\nEnter option (1/2/3): ")
        
        if choice == '1':
            reset_activity_logs()
        elif choice == '2':
            admin_id = input("Enter admin ID: ")
            reset_specific_admin_logs(admin_id)
        elif choice == '3':
            days = int(input("Enter number of days: "))
            reset_old_logs(days)
        else:
            print("Invalid choice")
    
    print("\n" + "=" * 80)
    print("Done!")
    print("=" * 80)
