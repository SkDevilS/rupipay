#!/usr/bin/env python3
"""
Check what merchants exist in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def check_merchants():
    """Check existing merchants"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT merchant_id, full_name, email, is_active
            FROM merchants 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        merchants = cursor.fetchall()
        
        print("Available merchants:")
        for merchant in merchants:
            print(f"  ID: {merchant['merchant_id']}")
            print(f"  Name: {merchant['full_name']}")
            print(f"  Email: {merchant['email']}")
            print(f"  Active: {merchant['is_active']}")
            print("-" * 40)
        
        cursor.close()
        conn.close()
        
        return merchants
        
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    check_merchants()