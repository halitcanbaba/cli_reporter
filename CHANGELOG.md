# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-07-14

### Added
- **Daily Report Generator**: Comprehensive daily financial reports with user balances, equity changes, and transaction summaries
- **Deal Categorization**: Automatic categorization of deals (Deposits, Withdrawals, Promotions, Credits, Trades)
- **Excel Export**: Professional Excel reports with formatting, styling, and multiple sheet organization
- **Agent and ZIP Integration**: Added agent and ZIP code tracking across all reports
- **Multiple Database Support**: Dynamic database connection management
- **Filtering System**: Advanced filtering by groups, login ranges, profit ranges, agent, and ZIP code
- **Telegram Integration**: Automated reporting through Telegram bot
- **Task Scheduling**: Configurable scheduled reporting
- **Configuration Management**: Save and load report configurations

### Features
- **Optimized Performance**: Current month optimization for faster queries
- **Professional Formatting**: Excel exports with proper styling, borders, and column sizing
- **Group Name Handling**: Proper display of long group names without truncation
- **Number Formatting**: Removed thousands separators from Login and Deal ID columns
- **Sorting Options**: Sort reports by Net P/L (ascending/descending)
- **Error Handling**: Comprehensive error handling and logging
- **Multi-format Output**: Console tables and Excel exports

### Technical Details
- **Database Schema**: Compatible with MT5 database structure
- **Python 3.7+**: Modern Python support with type hints
- **MySQL Integration**: Efficient MySQL connection management
- **Excel Generation**: Using openpyxl for professional Excel output
- **CLI Interface**: Command-line interface for all tools

### Components
- `daily_report.py`: Daily financial report generator
- `deals_categorizer.py`: Deal categorization and analysis
- `excel_exporter.py`: Excel export functionality
- `database_manager.py`: Database connection management
- `config_manager.py`: Configuration management
- `telegram_bot.py`: Telegram integration
- `scheduler.py`: Task scheduling
- `mysql_analyzer.py`: MySQL analysis tools

### Dependencies
- mysql-connector-python==8.0.33
- tabulate==0.9.0
- inquirer==3.1.3
- openpyxl==3.1.2
- python-telegram-bot==20.7
- schedule==1.2.0

### Fixed
- Group name truncation in Excel exports
- Thousands separator formatting in ID columns
- Column width handling for long group names
- Excel formatting and styling consistency
- Database connection timeout handling

### Security
- Database credential management
- Error handling for sensitive operations
- Input validation and sanitization

## [Unreleased]

### Planned
- Web interface for report generation
- API endpoints for programmatic access
- Additional export formats (PDF, CSV)
- Enhanced filtering options
- Real-time data updates
- Dashboard interface
