#!/usr/bin/env python3
"""
Import Database Schema from SQL File
Reads moneyone_db.sql and creates all missing tables
Skips INSERT statements - only creates table structures
"""

import pymysql
import re
from config import Config

def parse_sql_file(sql_file_path):
    """Parse SQL file and extract CREATE TABLE statements"""
    print(f"Reading {sql_file_path}...")
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments
    content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Split by semicolons to get individual statements
    statements = content.split(';')
    
    create_tables = []
    for stmt in statements:
        stmt = stmt.strip()
        if stmt.upper().startswith('CREATE TABLE'):
            # Add IF NOT EXISTS to make it idempotent
            if 'IF NOT EXISTS' not in stmt.upper():
                stmt = stmt.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS', 1)
            create_tables.append(stmt + ';')
    
    return create_tables

def import_database_schema():
    """Import database schema from SQL file"""
    try:
        print("=" * 80)
        print("MoneyOne Database Schema Import")
        print("=" * 80)
        print()
        
        # Parse SQL file
        sql_file = 'moneyone_db.sql'
        create_statements = parse_sql_file(sql_file)
        print(f"✅ Found {len(create_statements)} CREATE TABLE statements")
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
        
        print("✅ Connected successfully")
        print()
        
        # Get existing tables
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            existing_tables = {list(row.values())[0] for row in cursor.fetchall()}
            print(f"Existing tables: {len(existing_tables)}")
            print()
        
        # Execute CREATE TABLE statements
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        print("Creating tables...")
        print("-" * 80)
        
        with connection.cursor() as cursor:
            for i, stmt in enumerate(create_statements, 1):
                # Extract table name
                match = re.search(r'CREATE TABLE (?:IF NOT EXISTS )?`?(\w+)`?', stmt, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
                    
                    try:
                        # Disable foreign key checks temporarily
                        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                        
                        # Execute CREATE TABLE
                        cursor.execute(stmt)
                        connection.commit()
                        
                        # Re-enable foreign key checks
                        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                        
                        if table_name in existing_tables:
                            print(f"{i:2d}. ⏭️  {table_name:40s} (already exists)")
                            skipped_count += 1
                        else:
                            print(f"{i:2d}. ✅ {table_name:40s} (created)")
                            created_count += 1
                            
                    except Exception as e:
                        error_msg = str(e)
                        if 'already exists' in error_msg.lower():
                            print(f"{i:2d}. ⏭️  {table_name:40s} (already exists)")
                            skipped_count += 1
                        else:
                            print(f"{i:2d}. ❌ {table_name:40s} (error: {error_msg[:50]}...)")
                            error_count += 1
        
        connection.close()
        
        print("-" * 80)
        print()
        print("=" * 80)
        print("✅ DATABASE SCHEMA IMPORT COMPLETE!")
        print("=" * 80)
        print()
        print(f"Summary:")
        print(f"  Tables created:  {created_count}")
        print(f"  Tables skipped:  {skipped_count}")
        print(f"  Errors:          {error_count}")
        print(f"  Total processed: {len(create_statements)}")
        print()
        
        if error_count > 0:
            print("⚠️  Some tables had errors. Check the output above for details.")
            print()
        
        return error_count == 0
        
    except FileNotFoundError:
        print(f"\n❌ SQL file not found: {sql_file}")
        print("Make sure moneyone_db.sql is in the backend directory")
        return False
    except Exception as e:
        print(f"\n❌ Database import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = import_database_schema()
    exit(0 if success else 1)
