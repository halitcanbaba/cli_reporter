# Contributing to MT5 Trading Analysis Tool

Thank you for your interest in contributing to the MT5 Trading Analysis Tool! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you are expected to uphold our code of conduct. Please be respectful, inclusive, and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- MySQL Server access
- Git for version control
- Basic understanding of trading/financial concepts

### Development Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/mt5-trading-analysis.git
   cd mt5-trading-analysis
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up database connection**
   - Configure your test database credentials
   - Ensure you have access to MT5 database schema

## Contributing Guidelines

### Reporting Issues

When reporting issues, please include:
- **Clear description** of the problem
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **System information** (OS, Python version, etc.)
- **Error messages** and stack traces if applicable

### Suggesting Features

For feature requests:
- **Clear description** of the proposed feature
- **Use case** explaining why this feature would be valuable
- **Implementation ideas** if you have them
- **Backwards compatibility** considerations

### Code Contributions

#### Branch Naming
- `feature/description-of-feature`
- `bugfix/description-of-fix`
- `hotfix/critical-issue`
- `docs/documentation-update`

#### Commit Messages
Use clear, descriptive commit messages:
```
feat: add agent filtering to daily reports
fix: resolve group name truncation in Excel export
docs: update README with new filtering options
style: improve code formatting in excel_exporter.py
```

#### Code Style

- **Follow PEP 8** Python style guide
- **Use type hints** where appropriate
- **Add docstrings** for all functions and classes
- **Keep functions focused** and single-purpose
- **Use meaningful variable names**

Example:
```python
def calculate_net_pl(deposits: float, withdrawals: float, equity_change: float) -> float:
    """
    Calculate net profit/loss for a trading account.
    
    Args:
        deposits: Total deposit amount
        withdrawals: Total withdrawal amount (should be negative)
        equity_change: Change in equity
    
    Returns:
        Net profit/loss amount
    """
    return equity_change - deposits - withdrawals
```

#### Testing

- **Write tests** for new features
- **Test edge cases** and error conditions
- **Ensure backwards compatibility**
- **Test with different databases** if applicable

#### Documentation

- **Update README.md** for new features
- **Add inline comments** for complex logic
- **Update CHANGELOG.md** with your changes
- **Include usage examples** where appropriate

## Project Structure

```
mt5-trading-analysis/
├── daily_report.py          # Daily financial report generator
├── deals_categorizer.py     # Deal categorization and analysis
├── excel_exporter.py        # Excel export functionality
├── database_manager.py      # Database connection management
├── config_manager.py        # Configuration management
├── telegram_bot.py          # Telegram integration
├── scheduler.py             # Task scheduling
├── requirements.txt         # Dependencies
├── README.md               # Main documentation
├── CONTRIBUTING.md         # This file
├── CHANGELOG.md           # Version history
└── LICENSE                # License information
```

## Development Guidelines

### Database Operations

- **Use parameterized queries** to prevent SQL injection
- **Handle connection errors** gracefully
- **Close connections** properly
- **Use transactions** for multiple operations

### Error Handling

- **Catch specific exceptions** rather than generic ones
- **Provide meaningful error messages**
- **Log errors** appropriately
- **Don't expose sensitive information** in error messages

### Performance

- **Optimize database queries** for large datasets
- **Use appropriate data structures**
- **Consider memory usage** for large reports
- **Implement caching** where beneficial

### Security

- **Validate input** parameters
- **Sanitize database queries**
- **Handle credentials** securely
- **Don't commit sensitive information**

## Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** following the guidelines above
3. **Write or update tests** as needed
4. **Update documentation** if required
5. **Ensure all tests pass**
6. **Submit a pull request** with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots if UI changes
   - Test results

### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Commit messages are clear and descriptive

## Release Process

1. **Update version** in setup.py
2. **Update CHANGELOG.md** with release notes
3. **Create release branch** from main
4. **Tag the release** with version number
5. **Create GitHub release** with release notes

## Getting Help

- **Check existing issues** for similar problems
- **Read the documentation** thoroughly
- **Ask questions** in issue discussions
- **Join project discussions** for general questions

## Recognition

Contributors will be recognized in:
- **README.md** contributors section
- **Release notes** for significant contributions
- **GitHub contributors** page

## Areas for Contribution

### High Priority
- **Performance optimization** for large datasets
- **Additional export formats** (PDF, CSV)
- **Enhanced error handling**
- **Web interface** development

### Medium Priority
- **Additional filtering options**
- **Report customization** features
- **API development** for programmatic access
- **Database schema** improvements

### Low Priority
- **Code refactoring** for better maintainability
- **Documentation** improvements
- **Testing** coverage expansion
- **UI/UX** enhancements

## Questions?

If you have questions about contributing, please:
1. Check this document first
2. Look at existing issues and pull requests
3. Create a new issue with the "question" label
4. Be specific about what you need help with

Thank you for contributing to the MT5 Trading Analysis Tool!
