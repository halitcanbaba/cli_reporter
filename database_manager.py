#!/usr/bin/env python3
"""
Database Manager
Handles database connections and data retrieval
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import List, Dict, Optional


# Database connection parameters
DB_CONFIGS = {
    'mt5gn_live': {
        'host': '91.214.47.70',
        'user': 'admin',
        'password': 'fuCoo8fi!',
        'database': 'mt5gn_live'
    },
    'mt5lc_live': {
        'host': '91.214.47.70',
        'user': 'admin',
        'password': 'fuCoo8fi!',
        'database': 'mt5lc_live'
    },
    'mt5w2_live': {
        'host': '91.214.47.70',
        'user': 'admin',
        'password': 'fuCoo8fi!',
        'database': 'mt5w2_live'
    },
    'mt5ex_live': {
        'host': '91.214.47.70',
        'user': 'admin',
        'password': 'fuCoo8fi!',
        'database': 'mt5ex_live'
    }
}


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.db_config = None
    
    def connect_to_database(self, db_name: str = None) -> bool:
        """Connect to MySQL database"""
        if db_name and db_name in DB_CONFIGS:
            self.db_config = DB_CONFIGS[db_name]
        elif not self.db_config:
            # Default to mt5gn_live if no database specified
            self.db_config = DB_CONFIGS['mt5gn_live']
        
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                print(f"✓ Connected to MySQL database '{self.db_config['database']}' at {self.db_config['host']}")
                return True
        except Error as e:
            print(f"❌ Error connecting to MySQL: {e}")
            return False
    
    def close_connection(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✓ Database connection closed.")
    
    def get_available_groups(self) -> List[str]:
        """Get list of available login groups for the current year"""
        try:
            cursor = self.connection.cursor()
            
            # Get current year
            current_year = datetime.now().year
            
            # Try to get groups from daily table for current year
            daily_table = f"mt5_daily_{current_year}"
            
            query = f"""
            SELECT DISTINCT `Group` 
            FROM {daily_table}
            WHERE `Group` IS NOT NULL 
            AND `Group` != ''
            AND Login > 9999
            ORDER BY `Group`
            LIMIT 100
            """
            
            cursor.execute(query)
            groups = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            return groups
            
        except Error as e:
            print(f"❌ Error getting groups: {e}")
            return []
    
    def get_login_range(self, groups: List[str] = None) -> Dict:
        """Get min/max login values for optional groups"""
        try:
            cursor = self.connection.cursor()
            
            # Get current year
            current_year = datetime.now().year
            daily_table = f"mt5_daily_{current_year}"
            
            where_clause = "WHERE Login > 9999"
            query_params = []
            
            if groups:
                # Build IN clause for groups
                group_placeholders = ','.join(['%s'] * len(groups))
                where_clause += f" AND `Group` IN ({group_placeholders})"
                query_params.extend(groups)
            
            query = f"""
            SELECT 
                MIN(Login) as min_login,
                MAX(Login) as max_login,
                COUNT(DISTINCT Login) as total_logins
            FROM {daily_table}
            {where_clause}
            """
            
            cursor.execute(query, query_params)
            result = cursor.fetchone()
            
            cursor.close()
            
            if result:
                return {
                    'min_login': result[0] or 10000,
                    'max_login': result[1] or 99999,
                    'total_logins': result[2] or 0
                }
            else:
                return {
                    'min_login': 10000,
                    'max_login': 99999,
                    'total_logins': 0
                }
                
        except Error as e:
            print(f"❌ Error getting login range: {e}")
            return {
                'min_login': 10000,
                'max_login': 99999,
                'total_logins': 0
            }
    
    def get_available_schemas(self) -> List[str]:
        """Get available data schemas (years)"""
        try:
            cursor = self.connection.cursor()
            
            # Get table names that match the pattern mt5_daily_YYYY
            query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME LIKE 'mt5_daily_%'
            ORDER BY TABLE_NAME DESC
            """
            
            cursor.execute(query, (self.db_config['database'],))
            tables = cursor.fetchall()
            
            # Extract years from table names
            schemas = []
            for table in tables:
                table_name = table[0]
                # Extract year from table name (mt5_daily_2024 -> 2024)
                if table_name.startswith('mt5_daily_'):
                    year = table_name.replace('mt5_daily_', '')
                    if year.isdigit():
                        schemas.append(year)
            
            cursor.close()
            return schemas
            
        except Error as e:
            print(f"❌ Error getting schemas: {e}")
            return [str(datetime.now().year)]  # Default to current year
    
    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            if not self.connection or not self.connection.is_connected():
                return False
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            
            return result is not None
            
        except Error as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    def get_database_info(self) -> Dict:
        """Get current database information"""
        if not self.db_config:
            return {}
        
        return {
            'host': self.db_config['host'],
            'database': self.db_config['database'],
            'connected': self.connection and self.connection.is_connected()
        }
