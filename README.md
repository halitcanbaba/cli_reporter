# MT5 Trading Analysis Tool

A comprehensive Python-based analysis tool for MetaTrader 5 trading data. This tool provides daily reports, deal categorization, Excel exports, and automated reporting features for MT5 trading accounts.

## Features

### 📊 Daily Reports
- **Comprehensive daily financial reports** with user balances, equity changes, and transaction summaries
- **Filtering capabilities** by groups, login ranges, profit ranges, agent, and ZIP code
- **Agent and ZIP information** integration for enhanced user tracking
- **Optimized queries** for current month performance

### 💳 Deal Categorization
- **Automatic deal categorization** (Deposits, Withdrawals, Promotions, Credits, Trades)
- **Monthly and yearly analysis** with detailed profit/loss breakdowns
- **Agent and ZIP code tracking** for deal attribution
- **Deal-by-deal reporting** with full transaction history

### 📈 Excel Export
- **Professional Excel reports** with formatting and styling
- **Multiple sheet organization** (Summary, Daily Report, Deals Categorizer)
- **Automatic column sizing** and number formatting
- **Group name handling** with proper display of long group names
- **Configurable exports** based on saved configurations

### 🤖 Automation & Integration
- **Telegram bot integration** for automated reporting
- **Scheduled reporting** with configurable intervals
- **Task management** with modular configuration
- **Database connection management** with multiple database support

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/mt5-trading-analysis.git
cd mt5-trading-analysis
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure database connection:**
   - Update database credentials in your configuration files
   - Ensure MySQL server is accessible

4. **Cross-platform compatibility:**
   - The tool automatically detects the correct Python command (`python` or `python3`)
   - Works on Windows, macOS, and Linux systems
   - No manual configuration needed for Python command detection

## Usage

### Cross-Platform Command Execution
The tool automatically detects the correct Python command based on your operating system:
- **Windows**: Uses `python`, `python3`, or `py` (whichever is available)
- **macOS/Linux**: Uses `python3` by default
- **Automatic detection**: No manual configuration required

### Daily Reports

Generate daily financial reports with various filtering options:

```bash
# Basic daily report
python3 daily_report.py

# With specific parameters
python3 daily_report.py --database mt5gn_live --limit 100 --groups "GROUP1,GROUP2"

# With date and profit filters
python3 daily_report.py --date 2025-07-14 --min-profit 100 --max-profit 5000

# With agent and ZIP filters
python3 daily_report.py --agent 308 --zip 516
```

### Deal Categorization

Analyze and categorize trading deals:

```bash
# Monthly deals for current year
python3 deals_categorizer.py --monthly

# Specific year analysis
python3 deals_categorizer.py --year 2024 --limit 50

# With database selection
python3 deals_categorizer.py --database mt5gn_live --monthly
```

### Excel Export

Export reports to Excel with professional formatting:

```bash
# Using saved configuration
python3 excel_exporter.py --config config_name

# Direct export
python3 -c "
from excel_exporter import ExcelExporter
config = {
    'name': 'monthly_report',
    'database': 'mt5gn_live',
    'limit': 100,
    'groups': ['GROUP1', 'GROUP2']
}
exporter = ExcelExporter()
filename = exporter.export_config_report_to_xlsx(config)
print(f'Report exported to: {filename}')
"
```

### Configuration Management

Manage and save report configurations:

```bash
# Interactive configuration creator
python3 config_manager.py

# Task creation with modular approach
python3 task_creator_modular.py
```

## Configuration Options

### Database Configuration
- **Multi-database support** with dynamic connection management
- **Configurable timeouts** and connection pooling
- **Error handling** and automatic reconnection

### Report Filters
- **Groups**: Filter by specific user groups
- **Login Range**: Min/max login ID filtering
- **Date Range**: Custom date range selection
- **Profit Range**: Min/max profit filtering
- **Agent**: Filter by agent ID
- **ZIP Code**: Filter by ZIP code

### Export Options
- **Multiple formats**: Console table, Excel export
- **Styling options**: Professional formatting, column sizing
- **Data organization**: Multiple sheets, sorted data
- **Custom naming**: Configurable file names with timestamps

## File Structure

```
mt5-trading-analysis/
├── daily_report.py          # Daily financial report generator
├── deals_categorizer.py     # Deal categorization and analysis
├── excel_exporter.py        # Excel export functionality
├── database_manager.py      # Database connection management
├── config_manager.py        # Configuration management
├── telegram_bot.py          # Telegram integration
├── telegram_integration.py  # Telegram bot setup
├── scheduler.py             # Task scheduling
├── run_scheduler.py         # Scheduler runner
├── task_creator_modular.py  # Task creation utility
├── mysql_analyzer.py        # MySQL analysis tools
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Features in Detail

### Daily Reports
- **Balance tracking**: Current balance, previous day/month equity
- **Transaction summaries**: Deposits, withdrawals, promotions, credits
- **P/L calculations**: Equity P/L and Net P/L
- **User information**: Names, groups, currencies, agents, ZIP codes
- **Sorting options**: Sort by Net P/L (ascending/descending)

### Deal Categorization
- **Smart categorization**: Automatic deal type detection
- **Monthly analysis**: Month-by-month deal breakdown
- **Profit analysis**: Total, average, min/max profit per category
- **Agent tracking**: Deal attribution to specific agents
- **Date filtering**: Flexible date range selection

### Excel Export Features
- **Professional formatting**: Headers, borders, alternating row colors
- **Number formatting**: Currency formatting, no thousands separators for IDs
- **Column sizing**: Auto-sized columns with special handling for group names
- **Multiple sheets**: Organized data across different sheets
- **Summary information**: Configuration details and generation timestamps

## Database Schema

The tool works with MT5 database schema including:
- **mt5_users**: User account information
- **mt5_deals**: Trading deals and transactions
- **Custom fields**: Agent and ZIP code integration

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the code comments
- Review the example usage in the scripts

## Changelog

### Recent Updates
- ✅ Added agent and ZIP code integration
- ✅ Fixed group name truncation in Excel exports
- ✅ Removed thousands separators from Login and Deal ID columns
- ✅ Enhanced column width handling for long group names
- ✅ Improved Excel formatting and styling
- ✅ Added comprehensive filtering options
- ✅ Optimized database queries for current month performance

## Requirements

- Python 3.7+
- MySQL Server
- Required Python packages (see requirements.txt)

## Security

- Database credentials should be properly secured
- Use environment variables for sensitive configuration
- Regular security updates for dependencies recommended
