#!/usr/bin/env python3
"""
Check Recent Request IPs from Database
Shows IP addresses from activity logs
"""

import sys
sys.path.append('/var/www/moneyone/moneyone/backend')

from database import get_db_connection
from datetime import datetime, timedelta

def check_recent_ips(hours=24):
    """Check IPs from last N hours"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get unique IPs from last N hours
            cursor.execute("""
                SELECT 
                    ip_address,
                    COUNT(*) as request_count,
                    GROUP_CONCAT(DISTINCT admin_id) as admin_ids,
                    GROUP_CONCAT(DISTINCT action) as actions,
                    MIN(created_at) as first_seen,
                    MAX(created_at) as last_seen
                FROM admin_activity_logs
                WHERE created_at >= NOW() - INTERVAL %s HOUR
                GROUP BY ip_address
                ORDER BY request_count DESC
            """, (hours,))
            
            results = cursor.fetchall()
            
            print(f"\n🔍 IP Addresses from Last {hours} Hours")
            print("=" * 80)
            
            if not results:
                print("No activity found")
                return
            
            for row in results:
                print(f"\n📍 IP: {row['ip_address']}")
                print(f"   Requests: {row['request_count']}")
                print(f"   Admin IDs: {row['admin_ids']}")
                print(f"   Actions: {row['actions'][:100]}...")
                print(f"   First Seen: {row['first_seen']}")
                print(f"   Last Seen: {row['last_seen']}")
            
            # Get detailed logs for most active IP
            if results:
                top_ip = results[0]['ip_address']
                print(f"\n\n📊 Detailed Logs for Most Active IP: {top_ip}")
                print("=" * 80)
                
                cursor.execute("""
                    SELECT admin_id, action, status, user_agent, created_at
                    FROM admin_activity_logs
                    WHERE ip_address = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                """, (top_ip,))
                
                logs = cursor.fetchall()
                for log in logs:
                    print(f"{log['created_at']} | {log['admin_id']} | {log['action']} | {log['status']}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    check_recent_ips(hours)
