#!/usr/bin/env python3
"""
Sync Database Tables from SQL File
Reads moneyone_db.sql and creates any missing tables
NO DATA - only table structures
"""

import pymysql
import re
from config import Config

def extract_create_statements(sql_file_path):
    """Extract CREATE TABLE statements from SQL file"""
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all CREATE TABLE statements
    # Pattern: CREATE TABLE `table_name` ( ... ) ENGINE=...;
    pattern = r'CREATE TABLE `([^`]+)`\s*\((.*?)\)\s*ENGINE[^;]+;'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
    
    tables = {}
    for table_name, table_def in matches:
        # Reconstruct the full CREATE TABLE statement
        create_stmt = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({table_def}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci"
        tables[table_name] = create_stmt
    
    return tables

def sync_database_tables():
    """Create all missing tables from SQL file"""
    try:
        print("=" * 80)
        print("MoneyOne Database Table Sync")
        print("=" * 80)
        print()
        
        # Extract CREATE TABLE statements from SQL file
        print("Reading moneyone_db.sql...")
        sql_file = 'moneyone_db.sql'
        tables = extract_create_statements(sql_file)
        print(f"✅ Found {len(tables)} table definitions")
        print()
        
        # Connect to database
        print(f"Connecting to database: {Config.DB_NAME}...")
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Get existing tables
            cursor.execute("SHOW TABLES")
            existing_tables = {list(row.values())[0] for row in cursor.fetchall()}
            print(f"✅ Found {len(existing_tables)} existing tables")
            print()
            
            # Create missing tables
            created_count = 0
            skipped_count = 0
            
            print("Syncing tables...")
            for table_name, create_stmt in sorted(tables.items()):
                if table_name in existing_tables:
                    print(f"  ⏭️  {table_name} (already exists)")
                    skipped_count += 1
                else:
                    try:
                        cursor.execute(create_stmt)
                        connection.commit()
                        print(f"  ✅ {table_name} (created)")
                        created_count += 1
                    except Exception as e:
                        print(f"  ❌ {table_name} (error: {str(e)[:50]}...)")
            
            print()
            print("=" * 80)
            print("✅ DATABASE SYNC COMPLETE!")
            print("=" * 80)
            print()
            print(f"Tables created: {created_count}")
            print(f"Tables skipped: {skipped_count}")
            print(f"Total tables: {len(tables)}")
            print()
        
        connection.close()
        return True
        
    except FileNotFoundError:
        print(f"\n❌ SQL file not found: {sql_file}")
        print("Make sure moneyone_db.sql is in the same directory as this script")
        return False
    except Exception as e:
        print(f"\n❌ Database sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = sync_database_tables()
    exit(0 if success else 1)
