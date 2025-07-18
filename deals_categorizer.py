#!/usr/bin/env python3
"""
Deals Categorizer
Categorizes deals with cmd=2 based on comment patterns and creates a data table
"""

import mysql.connector
from mysql.connector import Error
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import re
import json
from tabulate import tabulate

# Fix Windows encoding issues
if sys.platform == "win32":
    import codecs
    import io
    try:
        # Check if stdout has a buffer attribute (not in subprocess environments)
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except (AttributeError, OSError):
        # Fallback for subprocess environments or different Windows setups
        pass  # Keep original stdout/stderr

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

def get_current_month_info():
    """Get current month information for optimization"""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Calculate current month date range
    month_start = datetime(current_year, current_month, 1)
    if current_month == 12:
        month_end = datetime(current_year + 1, 1, 1)
    else:
        month_end = datetime(current_year, current_month + 1, 1)
    
    return {
        'year': current_year,
        'month': current_month,
        'month_start': month_start,
        'month_end': month_end,
        'month_name': month_start.strftime('%B'),
        'date_range': f"{month_start.strftime('%Y-%m-%d')} to {(month_end - timedelta(days=1)).strftime('%Y-%m-%d')}"
    }

def display_deals_optimization_info():
    """Display current month optimization information for deals categorizer"""
    month_info = get_current_month_info()
    print("=" * 70)
    print("🚀 DEALS CATEGORIZER - CURRENT MONTH OPTIMIZATION")
    print("=" * 70)
    print(f"📅 Processing Month: {month_info['month_name']} {month_info['year']} (Month {month_info['month']})")
    print(f"📊 Date Range: {month_info['date_range']}")
    print(f"⚡ Performance: Only categorizing current month deals")
    print(f"🎯 Optimization: Ignoring all historical deal data")
    print("=" * 70)

class DealsCategorizerTool:
    def __init__(self, db_name='mt5gn_live'):
        self.connection = None
        self.db_name = db_name
    
    def connect_to_database(self) -> bool:
        """Connect to MySQL database"""
        try:
            if self.db_name not in DB_CONFIGS:
                print(f"❌ Unknown database: {self.db_name}")
                return False
            
            db_config = DB_CONFIGS[self.db_name]
            self.connection = mysql.connector.connect(**db_config)
            if self.connection.is_connected():
                # Only print connection info in non-JSON mode
                if '--json' not in sys.argv:
                    print(f"✓ Connected to MySQL database '{db_config['database']}' at {db_config['host']}")
                return True
        except Error as e:
            print(f"✗ Error connecting to MySQL: {e}")
            return False
    
    def close_connection(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            # Only print connection info in non-JSON mode
            if '--json' not in sys.argv:
                print("✓ Database connection closed.")
    
    def categorize_comment(self, comment: str) -> str:
        """Categorize comment based on patterns"""
        if comment is None:
            return "Promotion"
        
        comment_upper = comment.upper().strip()
        
        # Check for cancelled transactions first
        if comment_upper.startswith("CANCELLED WITH"):
            return "Withdrawal"
        elif comment_upper.startswith("CANCELLED DEP"):
            return "Deposit"
        # Check for regular patterns
        elif comment_upper.startswith("DT"):
            return "Deposit"
        elif comment_upper.startswith("WT") or comment_upper.startswith("WITH"):
            return "Withdrawal"
        else:
            return "Promotion"
    
    def analyze_comment_samples(self, year: int = 2025, limit: int = 100) -> None:
        """Analyze comment samples to understand patterns"""
        try:
            cursor = self.connection.cursor()
            
            deals_table = f"mt5_deals_{year}"
            
            query = f"""
            SELECT DISTINCT Comment
            FROM {deals_table}
            WHERE Action = 2 
            AND Comment IS NOT NULL 
            AND Comment != ''
            AND Login > 9999
            LIMIT {limit}
            """
            
            cursor.execute(query)
            comments = cursor.fetchall()
            
            print(f"\n📝 Comment samples from {deals_table} (Action=2):")
            print("=" * 60)
            
            categories = {"Deposit": [], "Withdrawal": [], "Promotion": []}
            
            for (comment,) in comments:
                category = self.categorize_comment(comment)
                categories[category].append(comment)
            
            for category, comment_list in categories.items():
                print(f"\n{category} ({len(comment_list)} samples):")
                for comment in comment_list[:10]:  # Show first 10
                    print(f"  - {comment}")
                if len(comment_list) > 10:
                    print(f"  ... and {len(comment_list) - 10} more")
            
            cursor.close()
            
        except Error as e:
            print(f"✗ Error analyzing comments: {e}")
    
    def get_categorized_deals(self, year: int = 2025, limit: Optional[int] = None, groups: Optional[List[str]] = None, 
                             min_login: Optional[int] = None, max_login: Optional[int] = None) -> List[Dict]:
        """Get deals with cmd=2 categorized by comments"""
        try:
            cursor = self.connection.cursor()
            
            deals_table = f"mt5_deals_{year}"
            
            # Build WHERE clause with filters
            where_conditions = ["d.Action = 2", "d.Login > 9999"]
            query_params = []
            
            # Add login range filters
            if min_login is not None:
                where_conditions.append("d.Login >= %s")
                query_params.append(min_login)
            
            if max_login is not None:
                where_conditions.append("d.Login <= %s")
                query_params.append(max_login)
            
            # Add group filter - need to join with mt5_users table
            group_join = ""
            if groups:
                group_join = "LEFT JOIN mt5_users u ON d.Login = u.Login"
                group_placeholders = ','.join(['%s'] * len(groups))
                where_conditions.append(f"u.`Group` IN ({group_placeholders})")
                query_params.extend(groups)
            
            where_clause = " AND ".join(where_conditions)
            limit_clause = f"LIMIT {limit}" if limit else ""
            
            query = f"""
            SELECT 
                d.Deal,
                d.Login,
                d.Time,
                d.Comment,
                d.Profit
            FROM {deals_table} d
            {group_join}
            WHERE {where_clause}
            ORDER BY d.Login ASC, d.Time ASC
            {limit_clause}
            """
            
            cursor.execute(query, query_params)
            results = cursor.fetchall()
            
            categorized_deals = []
            
            for deal, login, time, comment, profit in results:
                category = self.categorize_comment(comment)
                
                categorized_deals.append({
                    'deal_id': deal,
                    'login': login,
                    'time': time,
                    'comment': comment or '',
                    'profit': float(profit) if profit else 0.0,
                    'category': category
                })
            
            cursor.close()
            return categorized_deals
            
        except Error as e:
            print(f"✗ Error getting categorized deals: {e}")
            return []

    def get_monthly_deals_by_login(self, year: int = None, limit: Optional[int] = None, groups: Optional[List[str]] = None, 
                                  min_login: Optional[int] = None, max_login: Optional[int] = None) -> List[Dict]:
        """Get action=2 deals grouped by login with categories for the current month ONLY"""
        try:
            cursor = self.connection.cursor()
            
            # Get current month info - ALWAYS use current month and year
            month_info = get_current_month_info()
            current_year = month_info['year']
            current_month = month_info['month']
            
            # ALWAYS use current year and month (ignore year parameter for current month optimization)
            year = current_year
            deals_table = f"mt5_deals_{year}"
            
            # Use current month date range only
            month_start = month_info['month_start']
            month_end = month_info['month_end']
            
            # Only print debug info in non-JSON mode
            if '--json' not in sys.argv:
                print(f"📊 DEALS CATEGORIZER - CURRENT MONTH ONLY")
                print(f"📅 Processing Month: {month_info['month_name']} {year} (CURRENT MONTH)")
                print(f"📊 Date Range: {month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')}")
                print(f"🎯 OPTIMIZATION: Only current month data, ignoring historical years")
            
            # Build WHERE clause with filters
            where_conditions = ["d.Action = 2", "d.Login > 9999", "d.Time >= %s", "d.Time < %s"]
            query_params = [month_start, month_end]
            
            # Add login range filters
            if min_login is not None:
                where_conditions.append("d.Login >= %s")
                query_params.append(min_login)
            
            if max_login is not None:
                where_conditions.append("d.Login <= %s")
                query_params.append(max_login)
            
            # Add group filter - ensure LEFT JOIN is always included when groups are specified
            group_join = "LEFT JOIN mt5_users u ON d.Login = u.Login"
            if groups:
                group_placeholders = ','.join(['%s'] * len(groups))
                where_conditions.append(f"u.`Group` IN ({group_placeholders})")
                query_params.extend(groups)
            
            where_clause = " AND ".join(where_conditions)
            limit_clause = f"LIMIT {limit}" if limit else ""
            
            # Query for current month with index hints
            # Also get agent and zip info from mt5_users table
            query = f"""
            SELECT /*+ USE_INDEX({deals_table}, Time) */
                d.Deal,
                d.Login,
                d.Time,
                d.Comment,
                d.Profit,
                YEAR(d.Time) as deal_year,
                MONTH(d.Time) as deal_month,
                u.Agent,
                u.ZipCode
            FROM {deals_table} d
            {group_join}
            WHERE {where_clause}
            ORDER BY d.Login ASC, d.Time ASC
            {limit_clause}
            """
            
            cursor.execute(query, query_params)
            results = cursor.fetchall()
            
            # Only print debug info in non-JSON mode
            if '--json' not in sys.argv:
                print(f"✓ Found {len(results)} deals in current month {month_info['month_name']} {year}")
            
            monthly_deals = []
            
            for deal, login, time, comment, profit, deal_year, deal_month, agent, zip_code in results:
                category = self.categorize_comment(comment)
                
                monthly_deals.append({
                    'deal_id': deal,
                    'login': login,
                    'time': time,
                    'year': deal_year,
                    'month': deal_month,
                    'month_name': time.strftime('%B') if time else f"Month {deal_month}",
                    'comment': comment or '',
                    'profit': float(profit) if profit else 0.0,
                    'category': category,
                    'agent': agent or '',
                    'zip_code': zip_code or ''
                })
            
            cursor.close()
            return monthly_deals
            
        except Error as e:
            print(f"✗ Error getting monthly deals: {e}")
            return []

    def get_summary_by_category(self, year: int = None) -> Dict:
        """Get summary statistics by category for the current month ONLY"""
        try:
            cursor = self.connection.cursor()
            
            # Get current month info - ALWAYS use current month and year
            month_info = get_current_month_info()
            current_year = month_info['year']
            current_month = month_info['month']
            
            # ALWAYS use current year and month (ignore year parameter for current month optimization)
            year = current_year
            deals_table = f"mt5_deals_{year}"
            
            # Use current month date range only
            month_start = month_info['month_start']
            month_end = month_info['month_end']
            
            # Only print debug info in non-JSON mode
            if '--json' not in sys.argv:
                print(f"📊 SUMMARY: Current month ONLY: {month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')}")
                print(f"🎯 OPTIMIZATION: Ignoring all historical data, current month focus")
            
            deals_table = f"mt5_deals_{year}"
            
            # Query for current month with index hints
            query = f"""
            SELECT /*+ USE_INDEX({deals_table}, Time) */
                Comment,
                COUNT(*) as deal_count,
                SUM(Profit) as total_profit,
                AVG(Profit) as avg_profit,
                MIN(Profit) as min_profit,
                MAX(Profit) as max_profit
            FROM {deals_table}
            WHERE Action = 2 
            AND Login > 9999
            AND Time >= %s AND Time < %s
            GROUP BY Comment
            ORDER BY deal_count DESC
            """
            
            cursor.execute(query, (month_start, month_end))
            results = cursor.fetchall()
            
            summary = {
                "Deposit": {"count": 0, "total": 0, "avg": 0, "min": 0, "max": 0},
                "Withdrawal": {"count": 0, "total": 0, "avg": 0, "min": 0, "max": 0},
                "Promotion": {"count": 0, "total": 0, "avg": 0, "min": 0, "max": 0}
            }
            
            for comment, count, total, avg, min_val, max_val in results:
                category = self.categorize_comment(comment)
                
                summary[category]["count"] += count
                summary[category]["total"] += float(total) if total else 0
                
                if summary[category]["count"] > 0:
                    summary[category]["avg"] = summary[category]["total"] / summary[category]["count"]
                
                if min_val is not None:
                    if summary[category]["min"] == 0:
                        summary[category]["min"] = float(min_val)
                    else:
                        summary[category]["min"] = min(summary[category]["min"], float(min_val))
                
                if max_val is not None:
                    summary[category]["max"] = max(summary[category]["max"], float(max_val))
            
            cursor.close()
            return summary
            
        except Error as e:
            print(f"✗ Error getting summary: {e}")
            return {}

    def categorize_comment(self, comment: str) -> str:
        """Categorize comment based on patterns"""
        if comment is None:
            return "Promotion"
        
        comment_upper = comment.upper().strip()
        
        # Check for cancelled transactions first
        if comment_upper.startswith("CANCELLED WITH"):
            return "Withdrawal"
        elif comment_upper.startswith("CANCELLED DEP"):
            return "Deposit"
        # Check for regular patterns
        elif comment_upper.startswith("DT"):
            return "Deposit"
        elif comment_upper.startswith("WT") or comment_upper.startswith("WITH"):
            return "Withdrawal"
        else:
            return "Promotion"
    
    def analyze_comment_samples(self, year: int = 2025, limit: int = 100) -> None:
        """Analyze comment samples to understand patterns"""
        try:
            cursor = self.connection.cursor()
            
            deals_table = f"mt5_deals_{year}"
            
            query = f"""
            SELECT DISTINCT Comment
            FROM {deals_table}
            WHERE Action = 2 
            AND Comment IS NOT NULL 
            AND Comment != ''
            AND Login > 9999
            LIMIT {limit}
            """
            
            cursor.execute(query)
            comments = cursor.fetchall()
            
            print(f"\n📝 Comment samples from {deals_table} (Action=2):")
            print("=" * 60)
            
            categories = {"Deposit": [], "Withdrawal": [], "Promotion": []}
            
            for (comment,) in comments:
                category = self.categorize_comment(comment)
                categories[category].append(comment)
            
            for category, comment_list in categories.items():
                print(f"\n{category} ({len(comment_list)} samples):")
                for comment in comment_list[:10]:  # Show first 10
                    print(f"  - {comment}")
                if len(comment_list) > 10:
                    print(f"  ... and {len(comment_list) - 10} more")
            
            cursor.close()
            
        except Error as e:
            print(f"✗ Error analyzing comments: {e}")
    
def print_deals_table(deals: List[Dict], max_rows: int = 50):
    """Print deals in table format"""
    if not deals:
        print("No deals to display")
        return
    
    # Limit rows for display
    display_deals = deals[:max_rows]
    
    headers = ["Deal ID", "Login", "Time", "Category", "Profit", "Comment"]
    
    table_data = []
    for deal in display_deals:
        table_data.append([
            deal['deal_id'],
            deal['login'],
            deal['time'].strftime('%Y-%m-%d %H:%M:%S') if deal['time'] else 'N/A',
            deal['category'],
            f"{deal['profit']:,.2f}",
            (deal['comment'][:30] + '...') if len(deal['comment']) > 30 else deal['comment']
        ])
    
    print(f"\n[C] Categorized Deals (showing {len(display_deals)} of {len(deals)} total)")
    print("=" * 100)
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if len(deals) > max_rows:
        print(f"\n... and {len(deals) - max_rows} more deals")


def print_monthly_deals_table(monthly_deals: List[Dict], max_rows: int = 50):
    """Print monthly deals in table format optimized for Excel export"""
    if not monthly_deals:
        print("No monthly deals to display")
        return
    
    # Limit rows for display
    display_deals = monthly_deals[:max_rows]
    
    headers = ["Login", "Year", "Month", "Deal ID", "Category", "Profit", "Comment", "Date", "Agent", "ZIP"]
    
    table_data = []
    for deal in display_deals:
        table_data.append([
            deal['login'],
            deal['year'],
            deal['month_name'],
            deal['deal_id'],
            deal['category'],
            deal['profit'],  # Keep as number for Excel
            (deal['comment'][:40] + '...') if len(deal['comment']) > 40 else deal['comment'],
            deal['time'].strftime('%Y-%m-%d %H:%M:%S') if deal['time'] else 'N/A',
            deal.get('agent', ''),
            deal.get('zip_code', '')
        ])
    
    print(f"\n[C] Monthly Deals by Login (showing {len(display_deals)} of {len(monthly_deals)} total)")
    print("=" * 120)
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if len(monthly_deals) > max_rows:
        print(f"\n... and {len(monthly_deals) - max_rows} more deals")


def print_summary_table(summary: Dict):
    """Print summary statistics table"""
    headers = ["Category", "Count", "Total Profit", "Avg Profit", "Min Profit", "Max Profit"]
    
    table_data = []
    for category, stats in summary.items():
        table_data.append([
            category,
            f"{stats['count']:,}",
            f"{stats['total']:,.2f}",
            f"{stats['avg']:,.2f}",
            f"{stats['min']:,.2f}",
            f"{stats['max']:,.2f}"
        ])
    
    print(f"\n📊 Summary by Category")
    print("=" * 80)
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Categorize deals with Action=2 based on comment patterns - CURRENT MONTH OPTIMIZATION",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Categories:
  - Deposit: Comments starting with "DT" or "CANCELLED DEP"
  - Withdrawal: Comments starting with "WT", "WITH", or "CANCELLED WITH"
  - Promotion: All other comments

🚀 OPTIMIZATION: Always processes current month data only for optimal performance.
Historical data (2024 and earlier) is ignored for faster processing.

Examples:
  python deals_categorizer.py                     # Analyze current month (July 2025)
  python deals_categorizer.py --monthly           # Current month deals grouped by login
  python deals_categorizer.py -l 100              # Limit to 100 deals (current month)
  python deals_categorizer.py --samples           # Show comment samples (current month)
  python deals_categorizer.py --summary-only      # Show only summary (current month)
  python deals_categorizer.py --json              # JSON output (current month)
        """
    )
    
    parser.add_argument(
        '-db', '--database',
        type=str,
        default='mt5gn_live',
        help='Database to connect to (default: mt5gn_live)'
    )
    
    parser.add_argument(
        '-y', '--year',
        type=int,
        default=datetime.now().year,
        help=f'Year to analyze (default: {datetime.now().year} - current year, always uses current month)'
    )
    
    parser.add_argument(
        '-l', '--limit',
        type=int,
        help='Limit number of deals to process'
    )
    
    parser.add_argument(
        '--groups', '-g',
        type=str,
        nargs='*',
        help='Filter by specific groups'
    )
    
    parser.add_argument(
        '--min-login',
        type=int,
        help='Minimum login ID'
    )
    
    parser.add_argument(
        '--max-login',
        type=int,
        help='Maximum login ID'
    )
    
    parser.add_argument(
        '--samples',
        action='store_true',
        help='Show comment samples and exit'
    )
    
    parser.add_argument(
        '--monthly',
        action='store_true',
        help='Show monthly deals organized by login and month'
    )
    
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Show only summary statistics'
    )
    
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    args = parser.parse_args()
    
    # Only print header in non-JSON mode
    if not args.json:
        print("[C] Deals Categorizer Tool")
        print("=" * 50)
    
    # Initialize categorizer
    categorizer = DealsCategorizerTool(args.database)
    
    try:
        # Connect to database
        if not categorizer.connect_to_database():
            sys.exit(1)
        
        # Show samples if requested
        if args.samples:
            categorizer.analyze_comment_samples(args.year)
            return
        
        # Get summary
        summary = categorizer.get_summary_by_category(args.year)
        
        if args.summary_only:
            print_summary_table(summary)
            return
        
        # Get categorized deals
        if not args.json:
            print(f"\n🔍 Analyzing deals for year {args.year}...")
        
        if args.monthly:
            deals = categorizer.get_monthly_deals_by_login(args.year, args.limit, args.groups, args.min_login, args.max_login)
        else:
            deals = categorizer.get_categorized_deals(args.year, args.limit, args.groups, args.min_login, args.max_login)
        
        if not deals:
            if not args.json:
                print("✗ No deals found")
            sys.exit(1)
        
        # Output results
        if args.json:
            output_data = {
                "summary": summary,
                "deals": deals
            }
            print(json.dumps(output_data, indent=2, default=str))
        else:
            print_summary_table(summary)
            
            if args.monthly:
                print_monthly_deals_table(deals)
            else:
                print_deals_table(deals)
        
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        categorizer.close_connection()


if __name__ == "__main__":
    main()
