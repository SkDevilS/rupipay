"""
Test Advanced Search Endpoint
This script tests the advanced search endpoint to diagnose the issue
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json

def test_database_connection():
    """Test if database connection works"""
    print("=" * 50)
    print("Testing Database Connection")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed!")
            return False
        
        print("✅ Database connection successful")
        
        with conn.cursor() as cursor:
            # Test admin_users table
            cursor.execute("SELECT COUNT(*) as count FROM admin_users")
            result = cursor.fetchone()
            print(f"✅ admin_users table accessible ({result['count']} users)")
            
            # Test merchants table
            cursor.execute("SELECT COUNT(*) as count FROM merchants")
            result = cursor.fetchone()
            print(f"✅ merchants table accessible ({result['count']} merchants)")
            
            # Test payin_transactions table
            cursor.execute("SELECT COUNT(*) as count FROM payin_transactions")
            result = cursor.fetchone()
            print(f"✅ payin_transactions table accessible ({result['count']} transactions)")
            
            # Test payout_transactions table
            cursor.execute("SELECT COUNT(*) as count FROM payout_transactions")
            result = cursor.fetchone()
            print(f"✅ payout_transactions table accessible ({result['count']} transactions)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_single_day_query(merchant_id, date):
    """Test single day query"""
    print("\n" + "=" * 50)
    print(f"Testing Single Day Query")
    print(f"Merchant ID: {merchant_id}")
    print(f"Date: {date}")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed!")
            return
        
        with conn.cursor() as cursor:
            # Check if merchant exists
            cursor.execute("SELECT merchant_id, full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant {merchant_id} not found!")
                print("\nAvailable merchants (first 5):")
                cursor.execute("SELECT merchant_id, full_name FROM merchants LIMIT 5")
                merchants = cursor.fetchall()
                for m in merchants:
                    print(f"  - {m['merchant_id']}: {m['full_name']}")
                conn.close()
                return
            
            print(f"✅ Merchant found: {merchant['full_name']}")
            
            # Test payin query
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transactions,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(SUM(charge_amount), 0) as total_charges,
                    COALESCE(SUM(net_amount), 0) as net_amount
                FROM payin_transactions
                WHERE merchant_id = %s 
                AND DATE(created_at) = %s
                AND status = 'SUCCESS'
            """, (merchant_id, date))
            
            result = cursor.fetchone()
            
            print("\n📊 Payin Results:")
            print(f"  Total Transactions: {result['total_transactions']}")
            print(f"  Total Amount: ₹{float(result['total_amount']):,.2f}")
            print(f"  Total Charges: ₹{float(result['total_charges']):,.2f}")
            print(f"  Net Amount: ₹{float(result['net_amount']):,.2f}")
            
            # Test payout query
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transactions,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(SUM(charge_amount), 0) as total_charges,
                    COALESCE(SUM(net_amount), 0) as net_amount
                FROM payout_transactions
                WHERE merchant_id = %s 
                AND DATE(created_at) = %s
                AND status = 'SUCCESS'
            """, (merchant_id, date))
            
            result = cursor.fetchone()
            
            print("\n📊 Payout Results:")
            print(f"  Total Transactions: {result['total_transactions']}")
            print(f"  Total Amount: ₹{float(result['total_amount']):,.2f}")
            print(f"  Total Charges: ₹{float(result['total_charges']):,.2f}")
            print(f"  Net Amount: ₹{float(result['net_amount']):,.2f}")
            
            print("\n✅ Query executed successfully!")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Query error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_date_range_query(merchant_id, from_date, to_date):
    """Test date range query"""
    print("\n" + "=" * 50)
    print(f"Testing Date Range Query")
    print(f"Merchant ID: {merchant_id}")
    print(f"From: {from_date}, To: {to_date}")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed!")
            return
        
        with conn.cursor() as cursor:
            # Check if merchant exists
            cursor.execute("SELECT merchant_id, full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant {merchant_id} not found!")
                conn.close()
                return
            
            print(f"✅ Merchant found: {merchant['full_name']}")
            
            # Test payin query
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as total_transactions,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(SUM(charge_amount), 0) as total_charges,
                    COALESCE(SUM(net_amount), 0) as net_amount
                FROM payin_transactions
                WHERE merchant_id = %s 
                AND DATE(created_at) BETWEEN %s AND %s
                AND status = 'SUCCESS'
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at)
            """, (merchant_id, from_date, to_date))
            
            daily_data = cursor.fetchall()
            
            print(f"\n📊 Payin Results ({len(daily_data)} days):")
            
            if len(daily_data) == 0:
                print("  No transactions found for this date range")
            else:
                total_txn = sum(day['total_transactions'] for day in daily_data)
                total_amt = sum(float(day['total_amount']) for day in daily_data)
                total_chg = sum(float(day['total_charges']) for day in daily_data)
                total_net = sum(float(day['net_amount']) for day in daily_data)
                
                print(f"  Total Transactions: {total_txn}")
                print(f"  Total Amount: ₹{total_amt:,.2f}")
                print(f"  Total Charges: ₹{total_chg:,.2f}")
                print(f"  Net Amount: ₹{total_net:,.2f}")
                
                print("\n  Day-wise breakdown (first 5 days):")
                for day in daily_data[:5]:
                    print(f"    {day['date']}: {day['total_transactions']} txns, ₹{float(day['total_amount']):,.2f}")
            
            print("\n✅ Query executed successfully!")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Query error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🔍 Advanced Search Diagnostic Tool\n")
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Database connection failed. Please check your database configuration.")
        sys.exit(1)
    
    # Get merchant ID from user or use default
    print("\n" + "=" * 50)
    merchant_id = input("Enter merchant ID to test (or press Enter for 9540057291): ").strip()
    if not merchant_id:
        merchant_id = "9540057291"
    
    # Get date
    date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
    if not date:
        from datetime import date as dt
        date = str(dt.today())
    
    # Test single day query
    test_single_day_query(merchant_id, date)
    
    # Ask if user wants to test date range
    print("\n" + "=" * 50)
    test_range = input("Test date range query? (y/n): ").strip().lower()
    
    if test_range == 'y':
        from_date = input("Enter from date (YYYY-MM-DD): ").strip()
        to_date = input("Enter to date (YYYY-MM-DD): ").strip()
        
        if from_date and to_date:
            test_date_range_query(merchant_id, from_date, to_date)
    
    print("\n" + "=" * 50)
    print("✅ Diagnostic complete!")
    print("=" * 50)
