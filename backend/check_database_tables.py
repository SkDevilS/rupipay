#!/usr/bin/env python3
"""
Check existing database tables to understand the schema
"""

from database import get_db_connection

def check_database_tables():
    """Check what tables exist in the database"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        cursor = conn.cursor()
        
        print("🔍 Checking existing database tables...")
        print("=" * 50)
        
        # Show all tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            print(f"  ✅ {table_name}")
            
            # Check if it's a transaction-related table
            if 'transaction' in table_name.lower() or 'payin' in table_name.lower():
                print(f"     🔍 Checking structure of {table_name}:")
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                for col in columns[:5]:  # Show first 5 columns
                    print(f"       - {col[0]} ({col[1]})")
                if len(columns) > 5:
                    print(f"       ... and {len(columns) - 5} more columns")
                print()
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        return False

def main():
    """Main function"""
    print("🗄️  Database Table Checker")
    print("=" * 30)
    
    check_database_tables()

if __name__ == "__main__":
    main()