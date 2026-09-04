"""
Database Schema Export Script
Exports complete database schema without data including:
- Tables with all columns and data types
- Primary keys and foreign keys
- Indexes (all types)
- Constraints (unique, check, default)
- Views
- Triggers
- Stored procedures
"""

import pymysql
import json
from datetime import datetime
from database import get_db_connection

def get_value(result, key_or_index):
    """Helper to get value from dict or tuple result"""
    if isinstance(result, dict):
        return result.get(key_or_index) or list(result.values())[0] if isinstance(key_or_index, int) else result.get(key_or_index)
    return result[key_or_index]

def export_complete_schema():
    """Export complete database schema to SQL file"""
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Get database name
    cursor.execute("SELECT DATABASE()")
    result = cursor.fetchone()
    db_name = get_value(result, 0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"database_schema_{db_name}_{timestamp}.sql"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"-- Database Schema Export\n")
        f.write(f"-- Database: {db_name}\n")
        f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- NO DATA INCLUDED - SCHEMA ONLY\n")
        f.write(f"\n")
        f.write(f"SET FOREIGN_KEY_CHECKS=0;\n")
        f.write(f"SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n\n")
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables_result = cursor.fetchall()
        tables = [get_value(row, 0) for row in tables_result]
        
        print(f"Found {len(tables)} tables in database '{db_name}'")
        f.write(f"-- Total Tables: {len(tables)}\n\n")
        
        # Export each table
        for table_name in sorted(tables):
            print(f"Exporting table: {table_name}")
            
            f.write(f"\n-- ============================================\n")
            f.write(f"-- Table: {table_name}\n")
            f.write(f"-- ============================================\n\n")
            
            # Get CREATE TABLE statement
            cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
            create_result = cursor.fetchone()
            create_table = get_value(create_result, 1)
            
            f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
            f.write(f"{create_table};\n\n")
            
            # Get table statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as row_count,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
                FROM information_schema.TABLES 
                WHERE table_schema = '{db_name}' 
                AND table_name = '{table_name}'
            """)
            stats = cursor.fetchone()
            row_count = get_value(stats, 0)
            size_mb = get_value(stats, 1)
            f.write(f"-- Rows: {row_count}, Size: {size_mb} MB\n\n")
        
        # Export Views
        f.write(f"\n-- ============================================\n")
        f.write(f"-- VIEWS\n")
        f.write(f"-- ============================================\n\n")
        
        cursor.execute(f"""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = '{db_name}'
        """)
        views = cursor.fetchall()
        
        if views:
            print(f"\nFound {len(views)} views")
            for view in views:
                view_name = get_value(view, 0)
                print(f"Exporting view: {view_name}")
                
                cursor.execute(f"SHOW CREATE VIEW `{view_name}`")
                create_result = cursor.fetchone()
                create_view = get_value(create_result, 1)
                
                f.write(f"DROP VIEW IF EXISTS `{view_name}`;\n")
                f.write(f"{create_view};\n\n")
        else:
            f.write(f"-- No views found\n\n")
        
        # Export Triggers
        f.write(f"\n-- ============================================\n")
        f.write(f"-- TRIGGERS\n")
        f.write(f"-- ============================================\n\n")
        
        cursor.execute(f"""
            SELECT trigger_name, event_object_table 
            FROM information_schema.triggers 
            WHERE trigger_schema = '{db_name}'
        """)
        triggers = cursor.fetchall()
        
        if triggers:
            print(f"\nFound {len(triggers)} triggers")
            for trigger in triggers:
                trigger_name = get_value(trigger, 0)
                print(f"Exporting trigger: {trigger_name}")
                
                cursor.execute(f"SHOW CREATE TRIGGER `{trigger_name}`")
                create_result = cursor.fetchone()
                create_trigger = get_value(create_result, 2)
                
                f.write(f"DROP TRIGGER IF EXISTS `{trigger_name}`;\n")
                f.write(f"DELIMITER ;;\n{create_trigger};;\nDELIMITER ;\n\n")
        else:
            f.write(f"-- No triggers found\n\n")
        
        # Export Stored Procedures
        f.write(f"\n-- ============================================\n")
        f.write(f"-- STORED PROCEDURES\n")
        f.write(f"-- ============================================\n\n")
        
        cursor.execute(f"""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = '{db_name}' 
            AND routine_type = 'PROCEDURE'
        """)
        procedures = cursor.fetchall()
        
        if procedures:
            print(f"\nFound {len(procedures)} stored procedures")
            for proc in procedures:
                proc_name = get_value(proc, 0)
                print(f"Exporting procedure: {proc_name}")
                
                cursor.execute(f"SHOW CREATE PROCEDURE `{proc_name}`")
                create_result = cursor.fetchone()
                create_proc = get_value(create_result, 2)
                
                f.write(f"DROP PROCEDURE IF EXISTS `{proc_name}`;\n")
                f.write(f"DELIMITER ;;\n{create_proc};;\nDELIMITER ;\n\n")
        else:
            f.write(f"-- No stored procedures found\n\n")
        
        # Export Functions
        f.write(f"\n-- ============================================\n")
        f.write(f"-- FUNCTIONS\n")
        f.write(f"-- ============================================\n\n")
        
        cursor.execute(f"""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = '{db_name}' 
            AND routine_type = 'FUNCTION'
        """)
        functions = cursor.fetchall()
        
        if functions:
            print(f"\nFound {len(functions)} functions")
            for func in functions:
                func_name = get_value(func, 0)
                print(f"Exporting function: {func_name}")
                
                cursor.execute(f"SHOW CREATE FUNCTION `{func_name}`")
                create_result = cursor.fetchone()
                create_func = get_value(create_result, 2)
                
                f.write(f"DROP FUNCTION IF EXISTS `{func_name}`;\n")
                f.write(f"DELIMITER ;;\n{create_func};;\nDELIMITER ;\n\n")
        else:
            f.write(f"-- No functions found\n\n")
        
        # Footer
        f.write(f"\nSET FOREIGN_KEY_CHECKS=1;\n")
        f.write(f"\n-- Schema export completed successfully\n")
    
    cursor.close()
    connection.close()
    
    print(f"\n✅ Schema exported successfully to: {output_file}")
    return output_file


def export_schema_documentation():
    """Export detailed schema documentation in JSON format"""
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT DATABASE()")
    result = cursor.fetchone()
    db_name = get_value(result, 0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"database_schema_docs_{db_name}_{timestamp}.json"
    
    schema_docs = {
        "database": db_name,
        "exported_at": datetime.now().isoformat(),
        "tables": {}
    }
    
    # Get all tables
    cursor.execute("SHOW TABLES")
    tables_result = cursor.fetchall()
    tables = [get_value(row, 0) for row in tables_result]
    
    for table_name in sorted(tables):
        print(f"Documenting table: {table_name}")
        
        table_info = {
            "columns": [],
            "indexes": [],
            "foreign_keys": [],
            "constraints": []
        }
        
        # Get columns
        cursor.execute(f"""
            SELECT 
                COLUMN_NAME,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                COLUMN_DEFAULT,
                EXTRA,
                COLUMN_COMMENT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = '{db_name}'
            AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """)
        
        for col in cursor.fetchall():
            table_info["columns"].append({
                "name": get_value(col, 0),
                "type": get_value(col, 1),
                "nullable": get_value(col, 2) == 'YES',
                "key": get_value(col, 3),
                "default": str(get_value(col, 4)) if get_value(col, 4) is not None else None,
                "extra": get_value(col, 5),
                "comment": get_value(col, 6)
            })
        
        # Get indexes
        cursor.execute(f"SHOW INDEX FROM `{table_name}`")
        indexes = {}
        for idx in cursor.fetchall():
            idx_name = get_value(idx, 2)
            if idx_name not in indexes:
                indexes[idx_name] = {
                    "name": idx_name,
                    "unique": not get_value(idx, 1),
                    "type": get_value(idx, 10),
                    "columns": []
                }
            indexes[idx_name]["columns"].append(get_value(idx, 4))
        
        table_info["indexes"] = list(indexes.values())
        
        # Get foreign keys
        cursor.execute(f"""
            SELECT 
                CONSTRAINT_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = '{db_name}'
            AND TABLE_NAME = '{table_name}'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        
        for fk in cursor.fetchall():
            table_info["foreign_keys"].append({
                "constraint_name": get_value(fk, 0),
                "column": get_value(fk, 1),
                "referenced_table": get_value(fk, 2),
                "referenced_column": get_value(fk, 3)
            })
        
        # Get table comment and stats
        cursor.execute(f"""
            SELECT 
                TABLE_COMMENT,
                TABLE_ROWS,
                ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS size_mb,
                ENGINE,
                TABLE_COLLATION
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = '{db_name}'
            AND TABLE_NAME = '{table_name}'
        """)
        
        stats = cursor.fetchone()
        table_info["comment"] = get_value(stats, 0)
        table_info["row_count"] = get_value(stats, 1)
        # Handle size_mb - ensure it's numeric
        size_val = get_value(stats, 2)
        try:
            table_info["size_mb"] = float(size_val) if size_val else 0.0
        except (ValueError, TypeError):
            table_info["size_mb"] = 0.0
        table_info["engine"] = get_value(stats, 3)
        table_info["collation"] = get_value(stats, 4)
        
        schema_docs["tables"][table_name] = table_info
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema_docs, f, indent=2, ensure_ascii=False)
    
    cursor.close()
    connection.close()
    
    print(f"\n✅ Schema documentation exported to: {output_file}")
    return output_file


def export_schema_markdown():
    """Export schema documentation in Markdown format"""
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT DATABASE()")
    result = cursor.fetchone()
    db_name = get_value(result, 0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"database_schema_docs_{db_name}_{timestamp}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Database Schema Documentation\n\n")
        f.write(f"**Database:** {db_name}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables_result = cursor.fetchall()
        tables = [get_value(row, 0) for row in tables_result]
        
        f.write(f"## Table of Contents\n\n")
        for table_name in sorted(tables):
            f.write(f"- [{table_name}](#{table_name.lower()})\n")
        f.write(f"\n---\n\n")
        
        # Document each table
        for table_name in sorted(tables):
            print(f"Documenting table: {table_name}")
            
            f.write(f"## {table_name}\n\n")
            
            # Get table stats
            cursor.execute(f"""
                SELECT 
                    TABLE_COMMENT,
                    TABLE_ROWS,
                    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS size_mb,
                    ENGINE
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = '{db_name}'
                AND TABLE_NAME = '{table_name}'
            """)
            stats = cursor.fetchone()
            
            comment = get_value(stats, 0)
            if comment:
                f.write(f"**Description:** {comment}\n\n")
            
            row_count = get_value(stats, 1)
            size_mb = get_value(stats, 2)
            engine = get_value(stats, 3)
            f.write(f"**Rows:** {row_count:,} | **Size:** {size_mb} MB | **Engine:** {engine}\n\n")
            
            # Columns
            f.write(f"### Columns\n\n")
            f.write(f"| Column | Type | Nullable | Key | Default | Extra |\n")
            f.write(f"|--------|------|----------|-----|---------|-------|\n")
            
            cursor.execute(f"""
                SELECT 
                    COLUMN_NAME,
                    COLUMN_TYPE,
                    IS_NULLABLE,
                    COLUMN_KEY,
                    COLUMN_DEFAULT,
                    EXTRA
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{db_name}'
                AND TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """)
            
            for col in cursor.fetchall():
                col_name = get_value(col, 0)
                col_type = get_value(col, 1)
                nullable = get_value(col, 2)
                key = get_value(col, 3) or '-'
                default = str(get_value(col, 4)) if get_value(col, 4) is not None else '-'
                extra = get_value(col, 5) or '-'
                f.write(f"| {col_name} | {col_type} | {nullable} | {key} | {default} | {extra} |\n")
            
            # Indexes
            f.write(f"\n### Indexes\n\n")
            cursor.execute(f"SHOW INDEX FROM `{table_name}`")
            indexes = {}
            for idx in cursor.fetchall():
                idx_name = get_value(idx, 2)
                if idx_name not in indexes:
                    indexes[idx_name] = {
                        "unique": not get_value(idx, 1),
                        "type": get_value(idx, 10),
                        "columns": []
                    }
                indexes[idx_name]["columns"].append(get_value(idx, 4))
            
            if indexes:
                f.write(f"| Index Name | Type | Unique | Columns |\n")
                f.write(f"|------------|------|--------|----------|\n")
                for idx_name, idx_info in indexes.items():
                    unique = "Yes" if idx_info["unique"] else "No"
                    cols = ", ".join(idx_info["columns"])
                    f.write(f"| {idx_name} | {idx_info['type']} | {unique} | {cols} |\n")
            else:
                f.write(f"*No indexes*\n")
            
            # Foreign Keys
            f.write(f"\n### Foreign Keys\n\n")
            cursor.execute(f"""
                SELECT 
                    CONSTRAINT_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = '{db_name}'
                AND TABLE_NAME = '{table_name}'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            
            fks = cursor.fetchall()
            if fks:
                f.write(f"| Constraint | Column | References |\n")
                f.write(f"|------------|--------|------------|\n")
                for fk in fks:
                    constraint = get_value(fk, 0)
                    column = get_value(fk, 1)
                    ref_table = get_value(fk, 2)
                    ref_column = get_value(fk, 3)
                    f.write(f"| {constraint} | {column} | {ref_table}.{ref_column} |\n")
            else:
                f.write(f"*No foreign keys*\n")
            
            f.write(f"\n---\n\n")
    
    cursor.close()
    connection.close()
    
    print(f"\n✅ Markdown documentation exported to: {output_file}")
    return output_file


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE SCHEMA EXPORT TOOL")
    print("=" * 60)
    print("\nThis script will export your complete database schema")
    print("WITHOUT any data in 3 formats:\n")
    print("1. SQL file (importable schema)")
    print("2. JSON file (structured documentation)")
    print("3. Markdown file (readable documentation)")
    print("\n" + "=" * 60 + "\n")
    
    try:
        # Export SQL schema
        print("\n📋 Exporting SQL schema...")
        sql_file = export_complete_schema()
        
        # Export JSON documentation
        print("\n📋 Exporting JSON documentation...")
        json_file = export_schema_documentation()
        
        # Export Markdown documentation
        print("\n📋 Exporting Markdown documentation...")
        md_file = export_schema_markdown()
        
        print("\n" + "=" * 60)
        print("✅ EXPORT COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nGenerated files:")
        print(f"  1. {sql_file} - SQL schema (importable)")
        print(f"  2. {json_file} - JSON documentation")
        print(f"  3. {md_file} - Markdown documentation")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
