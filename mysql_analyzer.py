#!/usr/bin/env python3
"""
MySQL Database Schema Analyzer
Connects to MySQL database and analyzes the mt5gn_live schema
"""

import mysql.connector
from mysql.connector import Error
import sys

# Database connection parameters
DB_CONFIG = {
    'host': '91.214.47.70',
    'user': 'admin',
    'password': 'fuCoo8fi!',
    'database': 'mt5gn_live'
}

def connect_to_database():
    """Connect to MySQL database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print(f"Successfully connected to MySQL database at {DB_CONFIG['host']}")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_database_info(connection):
    """Get basic database information"""
    try:
        cursor = connection.cursor()
        
        # Get database version
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"\nMySQL Version: {version}")
        
        # Get current database
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()[0]
        print(f"Current Database: {current_db}")
        
        cursor.close()
    except Error as e:
        print(f"Error getting database info: {e}")

def get_tables_list(connection):
    """Get list of all tables in the database"""
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        print(f"\nFound {len(tables)} tables in the database:")
        for i, table in enumerate(tables, 1):
            print(f"{i:2d}. {table}")
        
        cursor.close()
        return tables
    except Error as e:
        print(f"Error getting tables list: {e}")
        return []

def analyze_table_structure(connection, table_name):
    """Analyze the structure of a specific table"""
    try:
        cursor = connection.cursor()
        
        # Get table structure
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        print(f"\n{'='*60}")
        print(f"TABLE: {table_name}")
        print(f"{'='*60}")
        
        # Display column information
        print(f"{'Column':<20} {'Type':<20} {'Null':<5} {'Key':<5} {'Default':<10} {'Extra'}")
        print("-" * 80)
        
        for col in columns:
            field, col_type, null, key, default, extra = col
            default_str = str(default) if default is not None else "NULL"
            extra_str = str(extra) if extra is not None else ""
            print(f"{field:<20} {str(col_type):<20} {null:<5} {key:<5} {default_str:<10} {extra_str}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        print(f"\nTotal rows: {row_count:,}")
        
        # Get sample data (first 3 rows)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        sample_data = cursor.fetchall()
        
        if sample_data:
            print(f"\nSample data (first 3 rows):")
            column_names = [desc[0] for desc in cursor.description]
            
            # Create a simple table display
            print("\n" + " | ".join(f"{col[:15]:<15}" for col in column_names))
            print("-" * (len(column_names) * 17))
            
            for row in sample_data:
                row_strs = []
                for val in row:
                    if val is None:
                        row_strs.append("NULL".ljust(15))
                    else:
                        row_strs.append(str(val)[:15].ljust(15))
                print(" | ".join(row_strs))
        
        cursor.close()
        
    except Error as e:
        print(f"Error analyzing table {table_name}: {e}")

def get_table_relationships(connection):
    """Get foreign key relationships between tables"""
    try:
        cursor = connection.cursor()
        
        query = """
        SELECT 
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE REFERENCED_TABLE_SCHEMA = %s
        AND REFERENCED_TABLE_NAME IS NOT NULL
        """
        
        cursor.execute(query, (DB_CONFIG['database'],))
        relationships = cursor.fetchall()
        
        if relationships:
            print(f"\n{'='*60}")
            print("FOREIGN KEY RELATIONSHIPS")
            print(f"{'='*60}")
            
            for rel in relationships:
                table, column, constraint, ref_table, ref_column = rel
                print(f"{table}.{column} -> {ref_table}.{ref_column}")
        else:
            print("\nNo foreign key relationships found.")
        
        cursor.close()
        
    except Error as e:
        print(f"Error getting table relationships: {e}")

def get_database_size(connection):
    """Get database size information"""
    try:
        cursor = connection.cursor()
        
        query = """
        SELECT 
            table_name,
            ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
        FROM information_schema.tables 
        WHERE table_schema = %s
        ORDER BY (data_length + index_length) DESC
        """
        
        cursor.execute(query, (DB_CONFIG['database'],))
        table_sizes = cursor.fetchall()
        
        print(f"\n{'='*60}")
        print("TABLE SIZES")
        print(f"{'='*60}")
        
        total_size = 0
        print(f"{'Table Name':<30} {'Size (MB)':<15}")
        print("-" * 45)
        
        for table_name, size in table_sizes:
            size_mb = size if size is not None else 0.0
            total_size += size_mb
            print(f"{table_name:<30} {size_mb:<15.2f}")
        
        print(f"\nTotal database size: {total_size:.2f} MB")
        
        cursor.close()
        
    except Error as e:
        print(f"Error getting database size: {e}")

def main():
    """Main function to analyze the database"""
    print("MySQL Database Schema Analyzer")
    print("=" * 50)
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        sys.exit(1)
    
    try:
        # Get basic database info
        get_database_info(connection)
        
        # Get list of tables
        tables = get_tables_list(connection)
        
        if not tables:
            print("No tables found in the database.")
            return
        
        # Analyze each table
        print(f"\n{'='*60}")
        print("DETAILED TABLE ANALYSIS")
        print(f"{'='*60}")
        
        for table in tables:
            analyze_table_structure(connection, table)
        
        # Get relationships
        get_table_relationships(connection)
        
        # Get database size
        get_database_size(connection)
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if connection and connection.is_connected():
            connection.close()
            print(f"\nDatabase connection closed.")

if __name__ == "__main__":
    main()
