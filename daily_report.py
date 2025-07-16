#!/usr/bin/env python3
"""
Daily Financial Report Generator
Generates login-based daily financial reports with equity, deposits, withdrawals, and promotions
"""

import mysql.connector
from mysql.connector import Error
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
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

# Import deals categorizer functionality
try:
    from deals_categorizer import DealsCategorizerTool
except ImportError:
    print("❌ Error: deals_categorizer.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

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

def connect_to_database(db_name='mt5gn_live'):
    """Connect to MySQL database"""
    try:
        if db_name not in DB_CONFIGS:
            print(f"❌ Unknown database: {db_name}")
            return None
        
        db_config = DB_CONFIGS[db_name]
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def get_daily_report(connection, target_date=None, limit=50, db_name='mt5gn_live', 
                   groups=None, min_login=None, max_login=None, min_profit=None, max_profit=None,
                   agent=None, zip_code=None):
    """
    Generate daily financial report for current month only
    
    Args:
        connection: Database connection
        target_date: Target date for report (default: latest date from current month)
        limit: Maximum number of records to return
        db_name: Database name for deals categorizer
        groups: List of groups to filter by
        min_login: Minimum login ID
        max_login: Maximum login ID
        min_profit: Minimum profit threshold
        max_profit: Maximum profit threshold
        agent: Agent filter
        zip_code: ZIP code filter
    """
    try:
        cursor = connection.cursor()
        
        # Display optimization info
        display_optimization_info()
        
        # Get current month info
        month_info = get_current_month_info()
        current_year = month_info['year']
        current_month = month_info['month']
        month_start = month_info['month_start']
        month_end = month_info['month_end']
        
        # Convert to timestamps
        month_start_ts = int(month_start.timestamp())
        month_end_ts = int(month_end.timestamp())
        
        # If no target date provided, get the latest date from current month
        if not target_date:
            cursor.execute(f"""
                SELECT MAX(DATE(FROM_UNIXTIME(Datetime))) as latest_date 
                FROM mt5_daily_{current_year}
                WHERE Datetime >= %s AND Datetime < %s
                AND Login > 9999
            """, (month_start_ts, month_end_ts))
            result = cursor.fetchone()
            if result and result[0]:
                target_date = result[0]
                print(f"📅 Using latest available date from current month: {target_date}")
            else:
                print(f"❌ No data found in current month: {current_year}-{current_month:02d}")
                return []
        
        # Convert target date to Unix timestamp for better performance
        target_date_start = int(datetime.combine(target_date, datetime.min.time()).timestamp())
        target_date_end = target_date_start + 86400  # +24 hours
        
        print(f"⏱️  Fetching daily data for {target_date}...")
        
        # Build WHERE clause with filters
        where_conditions = ["d.Datetime >= %s AND d.Datetime < %s", "d.Login > 9999"]
        query_params = [target_date_start, target_date_end]
        
        # Add group filter
        if groups:
            group_placeholders = ','.join(['%s'] * len(groups))
            where_conditions.append(f"d.`Group` IN ({group_placeholders})")
            query_params.extend(groups)
        
        # Add login range filters
        if min_login is not None:
            where_conditions.append("d.Login >= %s")
            query_params.append(min_login)
        
        if max_login is not None:
            where_conditions.append("d.Login <= %s")
            query_params.append(max_login)
        
        # Add agent filter
        if agent:
            where_conditions.append("u.Agent = %s")
            query_params.append(agent)
        
        # Add ZIP filter
        if zip_code:
            where_conditions.append("u.ZipCode = %s")
            query_params.append(zip_code)
        
        # Add profit filters (will be applied after joining with monthly data)
        # For now, we'll collect all data and filter later
        
        # Build limit clause
        limit_clause = f"LIMIT {limit}" if limit is not None else ""
        
        # Optimized main query for daily equity data (current month only)
        # Added index hints for better performance and JOIN with mt5_users for agent/zip filters
        daily_query = f"""
            SELECT /*+ USE_INDEX(d, Datetime) */
                d.Login,
                d.Name,
                d.`Group` as Group_Name,
                d.Currency,
                d.Balance,
                d.EquityPrevDay,
                d.EquityPrevMonth,
                FROM_UNIXTIME(d.Datetime) as ReportDate,
                u.Agent,
                u.ZipCode
            FROM mt5_daily_{current_year} d
            LEFT JOIN mt5_users u ON d.Login = u.Login
            WHERE {' AND '.join(where_conditions)}
            ORDER BY d.Login
            {limit_clause}
        """
        
        cursor.execute(daily_query, query_params)
        daily_data = cursor.fetchall()
        
        if not daily_data:
            print(f"❌ No daily data found for date: {target_date}")
            return []
        
        print(f"✓ Found {len(daily_data)} daily records")
        
        # Get list of logins for monthly data lookup
        login_list = [row[0] for row in daily_data]
        
        print(f"⏱️  Fetching monthly deals data...")
        
        # Get monthly deals using optimized query (current month only)
        monthly_data = get_monthly_deals_summary_optimized(connection, login_list, current_year, current_month, db_name)
        
        print(f"✓ Found monthly data for {len(monthly_data)} logins")
        
        # Combine data
        report_data = []
        for row in daily_data:
            login = row[0]
            monthly_info = monthly_data.get(login, {
                'monthly_deposits': 0,
                'monthly_withdrawals': 0,
                'monthly_promotions': 0,
                'monthly_credit': 0,
                'deposit_count': 0,
                'withdrawal_count': 0,
                'promotion_count': 0,
                'credit_count': 0
            })
            
            # Calculate EquityPL = -1 * (prev_day_equity - prev_month_equity - monthly_deposits - monthly_withdrawals - monthly_promotions - monthly_credit)
            prev_day_equity = row[5] or 0
            prev_month_equity = row[6] or 0
            monthly_deposits = monthly_info['monthly_deposits']
            monthly_withdrawals = monthly_info['monthly_withdrawals']
            monthly_promotions = monthly_info['monthly_promotions']
            monthly_credit = monthly_info['monthly_credit']
            
            equity_pl = -1 * (prev_day_equity - prev_month_equity - monthly_deposits - monthly_withdrawals - monthly_promotions - monthly_credit)
            
            report_data.append({
                'login': login,
                'name': row[1] or '',
                'group': row[2] or '',
                'currency': row[3] or '',
                'balance': row[4] or 0,
                'prev_day_equity': prev_day_equity,
                'prev_month_equity': prev_month_equity,
                'monthly_deposits': monthly_deposits,
                'monthly_withdrawals': monthly_withdrawals,
                'monthly_promotions': monthly_promotions,
                'monthly_credit': monthly_credit,
                'equity_pl': equity_pl,
                'net_pl': equity_pl - monthly_credit - monthly_promotions,
                'deposit_count': monthly_info['deposit_count'],
                'withdrawal_count': monthly_info['withdrawal_count'],
                'promotion_count': monthly_info['promotion_count'],
                'credit_count': monthly_info['credit_count'],
                'report_date': row[7],
                'agent': row[8] if len(row) > 8 else '',  # Agent from mt5_users
                'zip_code': row[9] if len(row) > 9 else ''  # ZipCode from mt5_users
            })
        
        # Apply profit filters if specified
        if min_profit is not None or max_profit is not None:
            filtered_data = []
            for record in report_data:
                # Calculate net monthly profit (including credit)
                net_monthly_profit = (record['monthly_deposits'] + record['monthly_withdrawals'] + 
                                    record['monthly_promotions'] + record['monthly_credit'])
                
                # Apply profit filters
                if min_profit is not None and net_monthly_profit < min_profit:
                    continue
                if max_profit is not None and net_monthly_profit > max_profit:
                    continue
                
                filtered_data.append(record)
            
            report_data = filtered_data
            print(f"📊 Applied profit filters: {len(report_data)} records remain")
        
        cursor.close()
        return report_data
        
    except Error as e:
        print(f"❌ Error generating daily report: {e}")
        return []

def get_monthly_deals_summary_optimized(connection, login_list, current_year, current_month, db_name='mt5gn_live'):
    """
    Get monthly deals summary using optimized direct query for current month only
    """
    try:
        cursor = connection.cursor()
        
        # Calculate current month date range
        month_start = datetime(current_year, current_month, 1)
        if current_month == 12:
            month_end = datetime(current_year + 1, 1, 1)
        else:
            month_end = datetime(current_year, current_month + 1, 1)
        
        # Calculate current month date range
        month_start = datetime(current_year, current_month, 1)
        if current_month == 12:
            month_end = datetime(current_year + 1, 1, 1)
        else:
            month_end = datetime(current_year, current_month + 1, 1)
        
        # Convert to datetime strings for deals query (since Time column is datetime, not timestamp)
        month_start_str = month_start.strftime('%Y-%m-%d %H:%M:%S')
        month_end_str = month_end.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"📊 Fetching deals for CURRENT MONTH ONLY: {month_start.strftime('%Y-%m-%d')} to {(month_end - timedelta(days=1)).strftime('%Y-%m-%d')}")
        print(f"⚡ PERFORMANCE: Using optimized current month queries only")
        print(f"🔍 Date range: {month_start_str} to {month_end_str}")
        print(f"📋 Login count: {len(login_list)}")
        
        # Create login list for IN clause
        if not login_list:
            return {}
        
        # Limit login list size to avoid MySQL query length limits
        login_list = login_list[:500]  # Limit to 500 logins
        login_placeholders = ','.join(['%s'] * len(login_list))
        
        # Optimized query - Use the same categorization logic as deals_categorizer.py
        # Include both Action=2 and Action=3 deals
        deals_query = f"""
            SELECT /*+ USE_INDEX(mt5_deals_{current_year}, Time) */
                Login,
                CASE 
                    WHEN Action = 3 THEN 'Credit'
                    WHEN Comment IS NULL THEN 'Promotion'
                    WHEN UPPER(TRIM(Comment)) LIKE 'CANCELLED WITH%' THEN 'Withdrawal'
                    WHEN UPPER(TRIM(Comment)) LIKE 'CANCELLED DEP%' THEN 'Deposit'
                    WHEN UPPER(TRIM(Comment)) LIKE 'DT%' THEN 'Deposit'
                    WHEN UPPER(TRIM(Comment)) LIKE 'WT%' OR UPPER(TRIM(Comment)) LIKE 'WITH%' THEN 'Withdrawal'
                    ELSE 'Promotion'
                END as Category,
                SUM(Profit) as Total_Profit,
                COUNT(*) as Deal_Count
            FROM mt5_deals_{current_year}
            WHERE (Action = 2 OR Action = 3)
            AND Login IN ({login_placeholders})
            AND Time >= %s AND Time < %s
            AND Login > 9999
            GROUP BY Login, Category
            ORDER BY Login
        """
        
        # Execute query with login list and datetime range
        query_params = login_list + [month_start_str, month_end_str]
        cursor.execute(deals_query, query_params)
        deals_data = cursor.fetchall()
        
        # Debug specific login if present (80060)
        if 80060 in login_list:
            debug_login_deals(connection, 80060, current_year, current_month)
        
        print(f"🎯 Raw deals query returned {len(deals_data)} rows")
        if len(deals_data) > 0:
            print("📋 Sample deals data:")
            for i, row in enumerate(deals_data[:3]):  # Show first 3 rows
                print(f"  Row {i+1}: Login={row[0]}, Category={row[1]}, Profit={row[2]}, Count={row[3]}")
        
        # Process results
        monthly_summary = {}
        
        for login, category, total_profit, deal_count in deals_data:
            if login not in monthly_summary:
                monthly_summary[login] = {
                    'monthly_deposits': 0,
                    'monthly_withdrawals': 0,
                    'monthly_promotions': 0,
                    'monthly_credit': 0,
                    'deposit_count': 0,
                    'withdrawal_count': 0,
                    'promotion_count': 0,
                    'credit_count': 0
                }
            
            profit_value = float(total_profit) if total_profit else 0
            
            if category == "Deposit":
                monthly_summary[login]['monthly_deposits'] += profit_value
                monthly_summary[login]['deposit_count'] += deal_count
            elif category == "Withdrawal":
                monthly_summary[login]['monthly_withdrawals'] += profit_value  # Keep negative for withdrawals
                monthly_summary[login]['withdrawal_count'] += deal_count
            elif category == "Promotion":
                monthly_summary[login]['monthly_promotions'] += profit_value
                monthly_summary[login]['promotion_count'] += deal_count
            elif category == "Credit":
                monthly_summary[login]['monthly_credit'] += profit_value
                monthly_summary[login]['credit_count'] += deal_count
        
        cursor.close()
        return monthly_summary
        
    except Error as e:
        print(f"❌ Error getting optimized monthly deals summary: {e}")
        return {}

def get_monthly_deals_summary(login_list, start_date, end_date, db_name='mt5gn_live'):
    """
    Get monthly deals summary using deals categorizer logic (legacy method)
    """
    try:
        # Create deals categorizer instance and get monthly deals
        categorizer = DealsCategorizerTool(db_name)
        
        # Connect to database
        if not categorizer.connect_to_database():
            return {}
        
        # Get monthly deals for the period
        monthly_deals = categorizer.get_monthly_deals_by_login(end_date.year)
        
        # Filter deals for the current month and specific logins
        current_month = end_date.month
        
        # Group deals by login and categorize
        monthly_summary = {}
        
        for deal in monthly_deals:
            login = deal['login']
            deal_month = deal['month']
            
            # Filter by month and login list
            if deal_month != current_month:
                continue
            if login_list and login not in login_list:
                continue
            
            # Initialize login summary if not exists
            if login not in monthly_summary:
                monthly_summary[login] = {
                    'monthly_deposits': 0,
                    'monthly_withdrawals': 0,
                    'monthly_promotions': 0,
                    'deposit_count': 0,
                    'withdrawal_count': 0,
                    'promotion_count': 0
                }
            
            # Categorize and sum up
            category = deal['category']
            profit_value = deal['profit']
            
            if category == "Deposit":
                monthly_summary[login]['monthly_deposits'] += profit_value
                monthly_summary[login]['deposit_count'] += 1
            elif category == "Withdrawal":
                monthly_summary[login]['monthly_withdrawals'] += profit_value  # Keep negative for withdrawals
                monthly_summary[login]['withdrawal_count'] += 1
            elif category == "Promotion":
                monthly_summary[login]['monthly_promotions'] += profit_value
                monthly_summary[login]['promotion_count'] += 1
        
        # Close categorizer connection
        categorizer.close_connection()
        
        return monthly_summary
        
    except Exception as e:
        print(f"❌ Error getting monthly deals summary: {e}")
        return {}


def format_currency(value, currency='USD'):
    """Format currency values"""
    if value is None:
        return '0.00'
    return f"{value:,.2f}"

def print_daily_report(report_data, output_format='table'):
    """Print the daily report in specified format"""
    if not report_data:
        print("❌ No data to display")
        return
    
    print(f"\n[$] Daily Financial Report - {report_data[0]['report_date'].strftime('%Y-%m-%d')}")
    print("=" * 120)
    
    # Summary statistics
    total_logins = len(report_data)
    total_deposits = sum(r['monthly_deposits'] for r in report_data)
    total_withdrawals = sum(r['monthly_withdrawals'] for r in report_data)
    total_promotions = sum(r['monthly_promotions'] for r in report_data)
    total_credits = sum(r['monthly_credit'] for r in report_data)
    total_equity_pl = sum(r['equity_pl'] for r in report_data)
    total_net_pl = sum(r['net_pl'] for r in report_data)
    total_deposit_count = sum(r['deposit_count'] for r in report_data)
    total_withdrawal_count = sum(r['withdrawal_count'] for r in report_data)
    total_promotion_count = sum(r['promotion_count'] for r in report_data)
    total_credit_count = sum(r['credit_count'] for r in report_data)
    
    print(f"📊 Summary Statistics:")
    print(f"   Total Logins: {total_logins:,}")
    print(f"   Monthly Deposits: {format_currency(total_deposits)} ({total_deposit_count:,} transactions)")
    print(f"   Monthly Withdrawals: {format_currency(abs(total_withdrawals))} ({total_withdrawal_count:,} transactions)")
    print(f"   Monthly Promotions: {format_currency(total_promotions)} ({total_promotion_count:,} transactions)")
    print(f"   Monthly Credits: {format_currency(total_credits)} ({total_credit_count:,} transactions)")
    print(f"   Total Equity P/L: {format_currency(total_equity_pl)}")
    print(f"   Total Net P/L: {format_currency(total_net_pl)}")
    print(f"   Net Monthly Flow: {format_currency(total_deposits + total_withdrawals + total_promotions + total_credits)}")
    
    # Prepare table data
    table_data = []
    headers = [
        'Login',
        'Name',
        'Group',
        'Currency',
        'Balance',
        'Prev Day Equity',
        'Prev Month Equity',
        'Monthly Deposits',
        'Monthly Withdrawals',
        'Monthly Promotions',
        'Monthly Credits',
        'Equity P/L',
        'Net P/L',
        'Dep Count',
        'Wth Count',
        'Promo Count',
        'Credit Count',
        'Agent',
        'ZIP'
    ]
    
    for record in report_data:
        table_data.append([
            record['login'],
            record['name'][:30] if record['name'] else '',  # Slightly increase name length
            record['group'] if record['group'] else '',  # Show full group name
            record['currency'],
            format_currency(record['balance']),
            format_currency(record['prev_day_equity']),
            format_currency(record['prev_month_equity']),
            format_currency(record['monthly_deposits']),
            format_currency(abs(record['monthly_withdrawals'])),  # Show withdrawals as positive in table
            format_currency(record['monthly_promotions']),
            format_currency(record['monthly_credit']),
            format_currency(record['equity_pl']),
            format_currency(record['net_pl']),
            record['deposit_count'],
            record['withdrawal_count'],
            record['promotion_count'],
            record['credit_count'],
            record.get('agent', ''),
            record.get('zip_code', '')
        ])
    
    print(f"\n📋 Detailed Report (showing {len(table_data)} records):")
    print("=" * 120)
    print(tabulate(table_data, headers=headers, tablefmt='grid', numalign='right'))

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

def display_optimization_info():
    """Display current month optimization information"""
    month_info = get_current_month_info()
    print("=" * 70)
    print("🚀 CURRENT MONTH OPTIMIZATION ACTIVE")
    print("=" * 70)
    print(f"📅 Processing Month: {month_info['month_name']} {month_info['year']} (Month {month_info['month']})")
    print(f"📊 Date Range: {month_info['date_range']}")
    print(f"⚡ Performance: Only querying current month data")
    print(f"🎯 Optimization: Skipping all historical months")
    print("=" * 70)

def debug_login_deals(connection, login, current_year, current_month):
    """Debug function to check deals for a specific login"""
    try:
        cursor = connection.cursor()
        
        # Calculate current month date range
        month_start = datetime(current_year, current_month, 1)
        if current_month == 12:
            month_end = datetime(current_year + 1, 1, 1)
        else:
            month_end = datetime(current_year, current_month + 1, 1)
        
        # Convert to datetime strings for deals query (since Time column is datetime, not timestamp)
        month_start_str = month_start.strftime('%Y-%m-%d %H:%M:%S')
        month_end_str = month_end.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n🔍 Debug: Checking deals for login {login}")
        print(f"📅 Date range: {month_start} to {month_end}")
        print(f"⏱️ Date range strings: {month_start_str} to {month_end_str}")
        
        # Get raw deals for this login
        raw_query = f"""
            SELECT Deal, Login, Time, Comment, Profit, Action
            FROM mt5_deals_{current_year}
            WHERE Login = %s 
            AND Action = 2
            AND Time >= %s AND Time < %s
            ORDER BY Time
        """
        
        cursor.execute(raw_query, (login, month_start_str, month_end_str))
        raw_deals = cursor.fetchall()
        
        print(f"📊 Found {len(raw_deals)} deals with Action=2 for login {login}")
        
        if raw_deals:
            print("\n📋 Raw deals data:")
            for deal_id, login_id, time_ts, comment, profit, action in raw_deals:
                # Use already imported DealsCategorizerTool
                categorizer = DealsCategorizerTool()
                category = categorizer.categorize_comment(comment)
                print(f"  Deal {deal_id}: {time_ts} | Comment: '{comment}' | Profit: {profit} | Category: {category}")
        
        # Test categorization query
        cat_query = f"""
            SELECT 
                Login,
                CASE 
                    WHEN Comment IS NULL THEN 'Promotion'
                    WHEN UPPER(TRIM(Comment)) LIKE 'CANCELLED WITH%' THEN 'Withdrawal'
                    WHEN UPPER(TRIM(Comment)) LIKE 'CANCELLED DEP%' THEN 'Deposit'
                    WHEN UPPER(TRIM(Comment)) LIKE 'DT%' THEN 'Deposit'
                    WHEN UPPER(TRIM(Comment)) LIKE 'WT%' OR UPPER(TRIM(Comment)) LIKE 'WITH%' THEN 'Withdrawal'
                    ELSE 'Promotion'
                END as Category,
                SUM(Profit) as Total_Profit,
                COUNT(*) as Deal_Count
            FROM mt5_deals_{current_year}
            WHERE Login = %s 
            AND Action = 2
            AND Time >= %s AND Time < %s
            GROUP BY Login, Category
        """
        
        cursor.execute(cat_query, (login, month_start_str, month_end_str))
        cat_results = cursor.fetchall()
        
        print(f"\n📈 Categorized results for login {login}:")
        for login_id, category, total_profit, deal_count in cat_results:
            print(f"  {category}: {deal_count} deals, Total: {total_profit}")
        
        cursor.close()
        
    except Error as e:
        print(f"❌ Error debugging login {login}: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate daily financial reports')
    parser.add_argument('--database', '-db', type=str, default='mt5gn_live', 
                       help='Database to connect to (default: mt5gn_live)')
    parser.add_argument('--date', '-d', type=str, help='Target date (YYYY-MM-DD format, default: latest)')
    parser.add_argument('--limit', '-l', type=int, default=50000, help='Maximum number of records (default: 50000)')
    parser.add_argument('--all', '-a', action='store_true', help='Show all records (no limit)')
    parser.add_argument('--groups', '-g', type=str, nargs='*', help='Filter by specific groups')
    parser.add_argument('--min-login', type=int, help='Minimum login ID')
    parser.add_argument('--max-login', type=int, help='Maximum login ID')
    parser.add_argument('--min-profit', type=float, help='Minimum profit threshold')
    parser.add_argument('--max-profit', type=float, help='Maximum profit threshold')
    parser.add_argument('--agent', type=str, help='Filter by agent')
    parser.add_argument('--zip', type=str, help='Filter by ZIP code')
    
    args = parser.parse_args()
    
    # Parse date if provided
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD format.")
            sys.exit(1)
    
    # Set limit
    limit = None if args.all else args.limit
    
    print("[$] Daily Financial Report Generator")
    print("=" * 50)
    
    # Connect to database
    connection = connect_to_database(args.database)
    if not connection:
        sys.exit(1)
    
    try:
        db_config = DB_CONFIGS[args.database]
        print(f"✓ Connected to MySQL database '{db_config['database']}' at {db_config['host']}")
        
        # Generate report
        print(f"\n🔍 Generating daily report...")
        if target_date:
            print(f"   Target date: {target_date}")
        if limit:
            print(f"   Limit: {limit} records")
        if args.groups:
            print(f"   Groups filter: {', '.join(args.groups)}")
        if args.min_login:
            print(f"   Min login: {args.min_login}")
        if args.max_login:
            print(f"   Max login: {args.max_login}")
        if args.min_profit:
            print(f"   Min profit: {args.min_profit}")
        if args.max_profit:
            print(f"   Max profit: {args.max_profit}")
        if args.agent:
            print(f"   Agent: {args.agent}")
        if args.zip:
            print(f"   ZIP: {args.zip}")
        
        report_data = get_daily_report(connection, target_date, limit, args.database, 
                                     groups=args.groups, min_login=args.min_login, 
                                     max_login=args.max_login, min_profit=args.min_profit, 
                                     max_profit=args.max_profit, agent=args.agent, 
                                     zip_code=args.zip)
        
        if report_data:
            print_daily_report(report_data)
        else:
            print("❌ No data found for the specified criteria.")
            
    except KeyboardInterrupt:
        print("\n❌ Report generation interrupted by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if connection and connection.is_connected():
            connection.close()
            print(f"\n✓ Database connection closed.")

def generate_daily_report_for_telegram(database='mt5gn_live', target_date=None, limit=20):
    """
    Generate a simplified daily report formatted for Telegram
    
    Args:
        database: Database name to query
        target_date: Target date for report (default: latest)
        limit: Maximum number of records
    
    Returns:
        str: Formatted report text for Telegram
    """
    try:
        # Connect to database
        connection = connect_to_database(database)
        if not connection:
            return f"❌ Failed to connect to database: {database}"
        
        # Get report data
        report_data = get_daily_report(connection, target_date, limit, database)
        
        if not report_data:
            connection.close()
            return f"❌ No data found for database: {database}"
        
        # Calculate summary statistics
        total_logins = len(report_data)
        total_deposits = sum(r['monthly_deposits'] for r in report_data)
        total_withdrawals = sum(r['monthly_withdrawals'] for r in report_data)
        total_promotions = sum(r['monthly_promotions'] for r in report_data)
        total_credits = sum(r['monthly_credit'] for r in report_data)
        total_equity_pl = sum(r['equity_pl'] for r in report_data)
        total_net_pl = sum(r['net_pl'] for r in report_data)
        total_deposit_count = sum(r['deposit_count'] for r in report_data)
        total_withdrawal_count = sum(r['withdrawal_count'] for r in report_data)
        total_promotion_count = sum(r['promotion_count'] for r in report_data)
        total_credit_count = sum(r['credit_count'] for r in report_data)
        net_flow = total_deposits + total_withdrawals + total_promotions + total_credits
        
        report_date = report_data[0]['report_date'].strftime('%Y-%m-%d')
        
        # Format report for Telegram
        telegram_report = f"""📊 <b>Daily Financial Report</b>
🗄️ <b>Database:</b> {database.upper()}
📅 <b>Date:</b> {report_date}
⏰ <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 <b>Summary Statistics:</b>
👥 Total Logins: {total_logins:,}
💰 Monthly Deposits: ${total_deposits:,.2f} ({total_deposit_count:,} txns)
💸 Monthly Withdrawals: ${abs(total_withdrawals):,.2f} ({total_withdrawal_count:,} txns)
🎁 Monthly Promotions: ${total_promotions:,.2f} ({total_promotion_count:,} txns)
💳 Monthly Credits: ${total_credits:,.2f} ({total_credit_count:,} txns)
📊 Total Equity P/L: ${total_equity_pl:,.2f}
🎯 Total Net P/L: ${total_net_pl:,.2f}
📈 Net Monthly Flow: ${net_flow:,.2f}

🔝 <b>Top {min(10, len(report_data))} Accounts by Balance:</b>"""
        
        # Sort by balance and show top accounts
        sorted_data = sorted(report_data, key=lambda x: x['balance'], reverse=True)
        for i, record in enumerate(sorted_data[:10], 1):
            balance = record['balance']
            monthly_total = record['monthly_deposits'] + record['monthly_withdrawals'] + record['monthly_promotions'] + record['monthly_credit']
            equity_pl = record['equity_pl']
            net_pl = record['net_pl']
            telegram_report += f"\n{i}. Login {record['login']}: ${balance:,.2f} (Monthly: ${monthly_total:+,.2f}, Equity P/L: ${equity_pl:+,.2f}, Net P/L: ${net_pl:+,.2f})"
        
        if len(report_data) > 10:
            telegram_report += f"\n... and {len(report_data) - 10} more accounts"
        
        connection.close()
        return telegram_report
        
    except Exception as e:
        return f"❌ Error generating report: {str(e)}"


if __name__ == "__main__":
    main()
