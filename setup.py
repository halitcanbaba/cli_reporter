#!/usr/bin/env python3
"""
Setup script for MT5 Trading Analysis Tool
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mt5-trading-analysis",
    version="1.0.0",
    author="PrimeTech",
    author_email="your.email@example.com",
    description="A comprehensive Python-based analysis tool for MetaTrader 5 trading data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mt5-trading-analysis",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mt5-daily-report=daily_report:main",
            "mt5-deals-categorizer=deals_categorizer:main",
            "mt5-config-manager=config_manager:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.json"],
    },
    keywords="mt5, metatrader, trading, analysis, finance, reporting, excel",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/mt5-trading-analysis/issues",
        "Source": "https://github.com/yourusername/mt5-trading-analysis",
    },
)
