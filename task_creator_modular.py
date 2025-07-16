#!/usr/bin/env python3
"""
Task Creator - Main CLI Application
Modular version with separate components for better maintainability
"""

import os
import sys
import subprocess
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import inquirer
from tabulate import tabulate

# Import our modular components
from config_manager import ConfigManager
from database_manager import DatabaseManager
from telegram_bot import TelegramIntegration
from excel_exporter import ExcelExporter
from scheduler import ScheduledTaskManager


class TaskCreator:
    def __init__(self):
        """Initialize the task creator with proper Python command detection"""
        # Detect Python command based on OS
        self.python_cmd = self._get_python_command()
        print(f"🐍 Using Python command: {self.python_cmd}")
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager()
        self.telegram = TelegramIntegration()
        self.excel_exporter = ExcelExporter()
        self.scheduler = ScheduledTaskManager()
        
        # Initialize configuration
        self.selected_config = {}
        self.execution_results = []
    
    def _get_python_command(self):
        """Get the correct Python command for current OS"""
        if sys.platform == "win32":
            # Test different Python commands on Windows
            test_commands = ["python", "python3", "py"]
            for cmd in test_commands:
                try:
                    result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
                    if result.returncode == 0:
                        return cmd
                except:
                    continue
            return "python"  # Default fallback
        else:
            return "python3"  # Unix/Linux/macOS
    
    def show_welcome(self):
        """Show welcome message"""
        print("=" * 60)
        print("🚀 Interactive Financial Analysis Task Creator")
        print("=" * 60)
        print("Create customized financial reports with ease!")
        print()
    
    def show_main_menu(self):
        """Show main menu with all options"""
        while True:
            telegram_status = self.telegram.get_telegram_status()
            telegram_option = f"Telegram Integration ({'✓ Active' if telegram_status['configured'] else '❌ Not Setup'})"
            
            # Get scheduler status
            scheduler_status = self.scheduler.get_scheduler_status()
            scheduler_option = f"Scheduled Tasks ({'🟢 Running' if scheduler_status['running'] else '🔴 Stopped'} - {scheduler_status['active_tasks']}/{scheduler_status['total_tasks']} active)"
            
            options = [
                "🚀 Create New Report",
                "📁 Configuration Management",
                f"🤖 {telegram_option}",
                f"📅 {scheduler_option}",
                "❌ Exit"
            ]
            
            questions = [
                inquirer.List('action',
                             message="Select an option",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                break
            
            action = answers['action']
            
            if "Create New Report" in action:
                self.run_report_creation()
                break
            elif "Configuration Management" in action:
                self.manage_configurations()
            elif "Telegram Integration" in action:
                self.telegram.manage_telegram_settings()
            elif "Scheduled Tasks" in action:
                self.manage_scheduled_tasks()
            elif "Exit" in action:
                print("👋 Goodbye!")
                break
    
    def manage_configurations(self):
        """Handle configuration management"""
        while True:
            options = [
                "📋 List All Configurations",
                "🗑️ Delete Configuration",
                "← Back to Main Menu"
            ]
            
            questions = [
                inquirer.List('action',
                             message="Configuration Management",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or "Back to Main Menu" in answers['action']:
                break
            
            if "List All Configurations" in answers['action']:
                self.config_manager.list_saved_configs()
                input("\nPress Enter to continue...")
            elif "Delete Configuration" in answers['action']:
                self.config_manager._delete_config_interactive()
    
    def run_report_creation(self):
        """Run the main report creation workflow"""
        try:
            # Step 0: Check for saved configurations and offer to load
            success, self.selected_config = self.config_manager.handle_saved_configs(self.selected_config)
            if not success:
                print("❌ Configuration loading cancelled")
                return
            
            # Step 1: Select database (skip if loaded from config)
            if 'database' not in self.selected_config:
                if not self.select_database():
                    print("❌ Database selection cancelled")
                    return
            
            # Connect to selected database
            if not self.db_manager.connect_to_database(self.selected_config['database']):
                print("❌ Database connection failed")
                return
            
            # Step 2: Select group (skip if loaded from config)
            if 'groups' not in self.selected_config:
                if not self.select_group():
                    print("❌ Group selection cancelled")
                    return
            
            # Step 3: Select login range (skip if loaded from config)
            if 'min_login' not in self.selected_config or 'max_login' not in self.selected_config:
                if not self.select_login_range():
                    print("❌ Login range selection cancelled")
                    return
            
            # Step 4: Select report type (skip if loaded from config)
            if 'report_type' not in self.selected_config:
                if not self.select_report_type():
                    print("❌ Report type selection cancelled")
                    return
            
            # Step 5: Additional options (skip if loaded from config)
            if 'limit' not in self.selected_config:
                if not self.select_additional_options():
                    print("❌ Additional options cancelled")
                    return
            
            # Step 6: Show summary and confirm
            if not self.show_configuration_summary():
                print("❌ Task execution cancelled")
                return
            
            # Step 7: Execute task
            results = self.execute_task()
            
            # Step 8: Handle export and Telegram
            if results:
                self.handle_results_export(results)
            
            # Step 9: Offer to save configuration
            self.config_manager.offer_save_config(self.selected_config)
            
        except KeyboardInterrupt:
            print("\n❌ Task creator interrupted by user")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            self.db_manager.close_connection()
    
    def select_database(self):
        """Interactive database selection"""
        print("🗄️  Select database to analyze...")
        
        from database_manager import DB_CONFIGS
        
        database_choices = []
        for db_name, config in DB_CONFIGS.items():
            database_choices.append(f"{db_name} - {config['database']} at {config['host']}")
        
        questions = [
            inquirer.List('database',
                         message="Select database",
                         choices=database_choices,
                         default=database_choices[0])
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return False
        
        # Extract database name from selection
        selected_db = answers['database'].split(' - ')[0]
        self.selected_config['database'] = selected_db
        
        print(f"✓ Selected database: {selected_db}")
        return True
    
    def select_group(self):
        """Interactive group selection with regex support and multi-column display"""
        print("\n👥 Getting available login groups...")
        available_groups = self.db_manager.get_available_groups()
        
        if not available_groups:
            print("❌ No groups found in database")
            return False
        
        selected_groups = []
        removed_logins = []  # Track individually removed logins
        
        while True:
            self._show_group_status(available_groups, selected_groups, removed_logins)
            
            options = [
                "➕ Add groups by regex pattern",
                "🔍 Add individual groups (with search)",
                "❌ Remove selected groups",
                "🚫 Remove individual login IDs",
                "✅ Continue with current selection",
                "🔄 Reset selection",
                "← Back to database selection"
            ]
            
            questions = [
                inquirer.List('action',
                             message="Group selection options",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                return False
            
            action = answers['action']
            
            if "Add groups by regex" in action:
                self._add_groups_by_regex(available_groups, selected_groups)
            elif "Add individual groups" in action:
                self._add_individual_groups_with_search(available_groups, selected_groups)
            elif "Remove selected groups" in action:
                self._remove_selected_groups(selected_groups)
            elif "Remove individual login" in action:
                self._remove_individual_login(removed_logins)
            elif "Continue with current" in action:
                break
            elif "Reset selection" in action:
                selected_groups.clear()
                removed_logins.clear()
                print("✓ Selection reset")
            elif "Back to database selection" in action:
                return False  # Cancel group selection
        
        # Set configuration
        if selected_groups:
            self.selected_config['groups'] = selected_groups
        else:
            self.selected_config['groups'] = None  # All groups
        
        self.selected_config['removed_logins'] = removed_logins
        
        return True
    
    def _show_group_status(self, available_groups: List[str], selected_groups: List[str], removed_logins: List[str] = None):
        """Show current group selection status in two columns"""
        print("\n" + "=" * 80)
        print("📊 GROUP SELECTION STATUS")
        print("=" * 80)
        
        # Prepare data for two-column display
        max_rows = max(len(available_groups), len(selected_groups))
        
        table_data = []
        for i in range(max_rows):
            available = available_groups[i] if i < len(available_groups) else ""
            selected = selected_groups[i] if i < len(selected_groups) else ""
            table_data.append([available, selected])
        
        headers = [
            f"Available Groups ({len(available_groups)})",
            f"Selected Groups ({len(selected_groups)})"
        ]
        
        print(tabulate(table_data, headers=headers, tablefmt="grid", maxcolwidths=[35, 35]))
        
        # Show removed logins if any
        if removed_logins:
            print(f"\n🚫 Removed Individual Logins ({len(removed_logins)}):")
            if len(removed_logins) <= 10:
                print("   " + ", ".join(map(str, removed_logins)))
            else:
                print(f"   {', '.join(map(str, removed_logins[:10]))}... (and {len(removed_logins)-10} more)")
    
    def _add_groups_by_regex(self, available_groups: List[str], selected_groups: List[str]) -> bool:
        """Add groups using regex pattern"""
        # Filter out already selected groups
        available_unselected = [g for g in available_groups if g not in selected_groups]
        
        if not available_unselected:
            print("❌ No unselected groups available to add")
            return False
        
        while True:
            print("\n💡 Regex Pattern Examples:")
            print("   GANN.*          - Groups starting with 'GANN'")
            print("   .*REAL.*        - Groups containing 'REAL'")
            print("   GANN-TR\\\\G_SF.* - Groups starting with 'GANN-TR\\G_SF'")
            print("   .*_SF_.*        - Groups containing '_SF_'")
            print("   ^DEMO.*         - Groups starting with 'DEMO'")
            print("   .*TEST$         - Groups ending with 'TEST'")
            
            options = [
                "✏️ Enter regex pattern",
                "💡 Show more examples",
                "← Back to group menu"
            ]
            
            questions = [
                inquirer.List('choice',
                             message="Regex pattern options",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or "Back to group menu" in answers['choice']:
                return False
            
            if "Show more examples" in answers['choice']:
                print("\n🎯 More Regex Examples:")
                print("   MT5.*           - Groups starting with 'MT5'")
                print("   .*LIVE.*        - Groups containing 'LIVE'")
                print("   .*-REAL$        - Groups ending with '-REAL'")
                print("   ^[A-Z]{4}.*     - Groups starting with 4 uppercase letters")
                print("   .*[0-9]+.*      - Groups containing numbers")
                print("   (DEMO|TEST).*   - Groups starting with 'DEMO' or 'TEST'")
                print("   .*_(SF|LC)_.*   - Groups containing '_SF_' or '_LC_'")
                input("\nPress Enter to continue...")
                continue
            
            # Get pattern
            questions = [
                inquirer.Text('pattern',
                             message="Enter regex pattern",
                             validate=lambda _, x: self._validate_regex_with_feedback(x))
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                continue
            
            pattern = answers['pattern']
            
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                matched_groups = [g for g in available_unselected if regex.search(g)]
                
                if matched_groups:
                    print(f"\n✓ Found {len(matched_groups)} groups matching pattern '{pattern}':")
                    for i, group in enumerate(matched_groups[:10], 1):  # Show first 10
                        print(f"  {i:2d}. {group}")
                    if len(matched_groups) > 10:
                        print(f"     ... and {len(matched_groups)-10} more")
                    
                    questions = [
                        inquirer.Confirm('confirm',
                                       message=f"Add these {len(matched_groups)} groups?",
                                       default=True)
                    ]
                    
                    answers = inquirer.prompt(questions)
                    if answers and answers['confirm']:
                        selected_groups.extend(matched_groups)
                        print(f"✓ Added {len(matched_groups)} groups")
                        return True
                else:
                    print(f"❌ No groups matched pattern: '{pattern}'")
                    print("💡 Try a different pattern or check the examples above")
                    
            except re.error as e:
                print(f"❌ Invalid regex pattern: {e}")
            
            # Ask if user wants to try again
            questions = [
                inquirer.Confirm('retry',
                               message="Try another pattern?",
                               default=True)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or not answers['retry']:
                return False
    
    def _validate_regex_with_feedback(self, pattern: str) -> bool:
        """Validate regex pattern with helpful feedback"""
        if not pattern.strip():
            print("❌ Pattern cannot be empty")
            return False
        
        try:
            re.compile(pattern)
            return True
        except re.error as e:
            print(f"❌ Invalid regex: {e}")
            print("💡 Quick fixes:")
            if '\\G' in pattern:
                print("   - \\G is a special regex character, use \\\\G for literal \\G")
            if pattern.endswith('\\'):
                print("   - Pattern cannot end with single backslash")
            if '*' in pattern and not ('.*' in pattern or pattern.startswith('*')):
                print("   - Use .* instead of * for 'anything'")
            if '[' in pattern and ']' not in pattern:
                print("   - Unclosed bracket [ - add closing ]")
            if '(' in pattern and ')' not in pattern:
                print("   - Unclosed parenthesis ( - add closing )")
            if '{' in pattern and '}' not in pattern:
                print("   - Unclosed brace { - add closing }")
            return False
    
    def _validate_regex(self, pattern: str) -> bool:
        """Simple regex validation"""
        if not pattern.strip():
            return False
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False
    
    def _add_individual_groups_with_search(self, available_groups: List[str], selected_groups: List[str]) -> bool:
        """Add individual groups with search functionality"""
        # Filter out already selected groups
        available_unselected = [g for g in available_groups if g not in selected_groups]
        
        if not available_unselected:
            print("❌ No unselected groups available to add")
            return False
        
        while True:
            print(f"\n🔍 Available groups to add: {len(available_unselected)}")
            
            options = [
                "🔍 Search and filter groups",
                "📋 Show all groups (paginated)",
                "← Back to group menu"
            ]
            
            questions = [
                inquirer.List('choice',
                             message="How would you like to select groups?",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or "Back to group menu" in answers['choice']:
                return False
            
            if "Search and filter" in answers['choice']:
                result = self._search_and_select_groups(available_unselected, selected_groups)
                if result:
                    return True
                # If search returns False, continue the loop to allow new search
            elif "Show all groups" in answers['choice']:
                result = self._paginated_group_selection(available_unselected, selected_groups)
                if result:
                    return True
                # If paginated selection returns False, continue the loop
    
    def _search_and_select_groups(self, available_groups: List[str], selected_groups: List[str]) -> bool:
        """Search and select groups with filtering"""
        while True:
            questions = [
                inquirer.Text('search_term',
                             message="Enter search term (case-insensitive, empty to see all)",
                             default="")
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                return False
            
            search_term = answers['search_term'].strip()
            
            if search_term:
                # Filter groups by search term
                filtered_groups = [g for g in available_groups if search_term.lower() in g.lower()]
                print(f"🔍 Found {len(filtered_groups)} groups matching '{search_term}'")
            else:
                filtered_groups = available_groups[:50]  # Show first 50 if no search
                print(f"📋 Showing first {len(filtered_groups)} groups")
            
            if not filtered_groups:
                print("❌ No groups found matching your search")
                continue
            
            # Add option to refine search and back
            group_choices = filtered_groups + ["🔍 Refine search", "← Back to selection menu"]
            
            questions = [
                inquirer.Checkbox('groups',
                                 message=f"Select groups to add ({len(filtered_groups)} found)",
                                 choices=group_choices)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                return False
            
            selected_items = answers['groups']
            
            if "🔍 Refine search" in selected_items:
                continue
            elif "← Back to selection menu" in selected_items:
                return False
            
            # Remove special options and add selected groups
            actual_groups = [g for g in selected_items if g not in ["🔍 Refine search", "← Back to selection menu"]]
            
            if actual_groups:
                selected_groups.extend(actual_groups)
                print(f"✓ Added {len(actual_groups)} groups")
                return True
            else:
                print("❌ No groups selected")
                continue
    
    def _paginated_group_selection(self, available_groups: List[str], selected_groups: List[str]) -> bool:
        """Show groups in pages for selection"""
        page_size = 20
        total_pages = (len(available_groups) + page_size - 1) // page_size
        current_page = 0
        
        while True:
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(available_groups))
            page_groups = available_groups[start_idx:end_idx]
            
            print(f"\n📋 Page {current_page + 1}/{total_pages} (Groups {start_idx + 1}-{end_idx})")
            
            # Add navigation options
            nav_options = []
            if current_page > 0:
                nav_options.append("◀ Previous page")
            if current_page < total_pages - 1:
                nav_options.append("▶ Next page")
            nav_options.extend(["✅ Select from this page", "← Back to selection menu"])
            
            questions = [
                inquirer.List('action',
                             message="Navigation options",
                             choices=nav_options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                return False
            
            action = answers['action']
            
            if action == "◀ Previous page":
                current_page -= 1
            elif action == "▶ Next page":
                current_page += 1
            elif action == "✅ Select from this page":
                questions = [
                    inquirer.Checkbox('groups',
                                     message=f"Select groups from page {current_page + 1}",
                                     choices=page_groups + ["← Back to page navigation"])
                ]
                
                answers = inquirer.prompt(questions)
                if answers and answers['groups']:
                    # Filter out navigation option
                    actual_groups = [g for g in answers['groups'] if g != "← Back to page navigation"]
                    if actual_groups:
                        selected_groups.extend(actual_groups)
                        print(f"✓ Added {len(actual_groups)} groups")
                        return True
                    elif "← Back to page navigation" in answers['groups']:
                        continue
            elif action == "← Back to selection menu":
                return False

    def _remove_selected_groups(self, selected_groups: List[str]) -> bool:
        """Remove groups from selected list"""
        if not selected_groups:
            print("❌ No selected groups to remove")
            return False
        
        # Add back option to the choices
        group_choices = selected_groups + ["← Back to group menu"]
        
        questions = [
            inquirer.Checkbox('groups',
                             message="Select groups to remove",
                             choices=group_choices)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or not answers['groups']:
            return False
        
        # Check if user selected back option
        if "← Back to group menu" in answers['groups']:
            return False
        
        # Remove selected groups
        for group in answers['groups']:
            if group in selected_groups:  # Safety check
                selected_groups.remove(group)
        
        print(f"✓ Removed {len(answers['groups'])} groups")
        return True
    
    def _remove_individual_login(self, removed_logins: List[str]) -> bool:
        """Remove individual login IDs from the query"""
        while True:
            print("\n🚫 Remove Individual Login IDs")
            print("Enter login IDs to exclude from the analysis")
            
            options = [
                "✏️ Enter login IDs to remove",
                "📋 Show currently removed logins",
                "← Back to group menu"
            ]
            
            questions = [
                inquirer.List('action',
                             message="Select action",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or "Back to group menu" in answers['action']:
                return False
            
            if "Show currently removed" in answers['action']:
                if removed_logins:
                    print(f"\n🚫 Currently removed logins ({len(removed_logins)}):")
                    for i, login in enumerate(removed_logins, 1):
                        print(f"  {i:3d}. {login}")
                else:
                    print("❌ No logins currently removed")
                input("\nPress Enter to continue...")
                continue
            
            # Enter login IDs
            questions = [
                inquirer.Text('logins',
                             message="Enter login ID(s) to remove (comma-separated)",
                             validate=lambda _, x: self._validate_login_ids(x))
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or not answers['logins']:
                continue
            
            # Parse and validate login IDs
            login_ids = [id.strip() for id in answers['logins'].split(',')]
            valid_logins = []
            
            for login_id in login_ids:
                if login_id.isdigit() and int(login_id) > 9999:
                    valid_logins.append(int(login_id))
                else:
                    print(f"❌ Invalid login ID: {login_id} (must be > 9999)")
            
            if valid_logins:
                # Add to removed logins (avoid duplicates)
                added_count = 0
                for login in valid_logins:
                    if login not in removed_logins:
                        removed_logins.append(login)
                        added_count += 1
                
                print(f"✓ Added {added_count} new login(s) to removal list")
                if added_count < len(valid_logins):
                    print(f"ℹ️ {len(valid_logins) - added_count} login(s) were already in the list")
                return True
            else:
                print("❌ No valid login IDs provided")
                continue
    
    def _validate_login_ids(self, login_input: str) -> bool:
        """Validate login ID input"""
        if not login_input.strip():
            return False
        
        login_ids = [id.strip() for id in login_input.split(',')]
        
        for login_id in login_ids:
            if not login_id.isdigit():
                return False
            if int(login_id) <= 9999:
                return False
        
        return True
    
    def select_login_range(self):
        """Interactive login range selection"""
        print("\n🔢 Getting login range information...")
        
        # Get suggested range
        range_info = self.db_manager.get_login_range(self.selected_config['groups'])
        
        print(f"📈 Range info for selected criteria:")
        print(f"   Min Login: {range_info['min_login']:,}")
        print(f"   Max Login: {range_info['max_login']:,}")
        print(f"   Total Logins: {range_info['total_logins']:,}")
        
        questions = [
            inquirer.Text('min_login',
                         message="Enter minimum login ID",
                         default=str(range_info['min_login']),
                         validate=lambda _, x: x.isdigit() and int(x) >= 10000),
            inquirer.Text('max_login',
                         message="Enter maximum login ID",
                         default=str(range_info['max_login']),
                         validate=lambda _, x: x.isdigit() and int(x) >= 10000)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return False
        
        self.selected_config['min_login'] = int(answers['min_login'])
        self.selected_config['max_login'] = int(answers['max_login'])
        
        if self.selected_config['min_login'] > self.selected_config['max_login']:
            print("❌ Minimum login cannot be greater than maximum login!")
            return False
        
        print(f"✓ Selected range: {self.selected_config['min_login']:,} - {self.selected_config['max_login']:,}")
        return True
    
    def select_report_type(self):
        """Interactive report type selection"""
        print("\n📋 Select report type...")
        
        report_choices = [
            "Daily Report - Login-based daily financial summary",
            "Deals Categorizer - Categorize deals by deposit/withdrawal/promotion",
            "Combined Report - Both daily report and deals categorization"
        ]
        
        questions = [
            inquirer.List('report_type',
                         message="Select report type",
                         choices=report_choices,
                         default=report_choices[0])
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return False
        
        # Extract report type from selection
        selected = answers['report_type']
        if "Daily Report" in selected:
            self.selected_config['report_type'] = "daily_report"
        elif "Deals Categorizer" in selected:
            self.selected_config['report_type'] = "deals_categorizer"
        else:
            self.selected_config['report_type'] = "combined"
        
        print(f"✓ Selected report type: {selected}")
        return True
    
    def select_additional_options(self):
        """Interactive additional options selection"""
        print("\n⚙️ Additional options...")
        
        questions = [
            inquirer.Text('limit',
                         message="Enter record limit (0 for no limit)",
                         default="100",
                         validate=lambda _, x: x.isdigit())
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return False
        
        self.selected_config['limit'] = int(answers['limit']) if answers['limit'] != "0" else None
        
        print(f"✓ Record limit: {self.selected_config['limit'] or 'No limit'}")
        return True
    
    def show_configuration_summary(self):
        """Show final configuration summary"""
        print("\n" + "=" * 60)
        print("📋 TASK CONFIGURATION SUMMARY")
        print("=" * 60)
        
        # Format groups display
        groups_display = "All Groups"
        if self.selected_config['groups']:
            if len(self.selected_config['groups']) <= 3:
                groups_display = ", ".join(self.selected_config['groups'])
            else:
                groups_display = f"{len(self.selected_config['groups'])} groups selected"
        
        config_table = [
            ["Database", self.selected_config['database']],
            ["Groups", groups_display],
            ["Login Range", f"{self.selected_config['min_login']:,} - {self.selected_config['max_login']:,}"],
            ["Report Type", self.selected_config['report_type'].replace('_', ' ').title()],
            ["Record Limit", str(self.selected_config['limit']) if self.selected_config['limit'] else "No limit"]
        ]
        
        # Add removed logins if any
        if self.selected_config.get('removed_logins'):
            removed_display = f"{len(self.selected_config['removed_logins'])} logins excluded"
            config_table.append(["Removed Logins", removed_display])
        
        print(tabulate(config_table, headers=["Setting", "Value"], tablefmt="grid"))
        
        questions = [
            inquirer.Confirm('confirm',
                           message="Execute task with these settings?",
                           default=True)
        ]
        
        answers = inquirer.prompt(questions)
        return answers and answers['confirm']
    
    def execute_task(self):
        """Execute the configured task and capture results"""
        commands = self.build_command()
        
        # Show optimization info
        self.show_optimization_info()
        
        print(f"\n🚀 Executing {len(commands)} command(s)...")
        
        # Store results for export
        execution_results = []
        
        for i, cmd in enumerate(commands, 1):
            print(f"\n📊 Running command {i}/{len(commands)}: {' '.join(cmd)}")
            print("-" * 50)
            
            try:
                # Capture output for export
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    print(f"✓ Command {i} completed successfully")
                    # Store successful results
                    execution_results.append({
                        'command': ' '.join(cmd),
                        'output': result.stdout,
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Also print some output to console
                    if result.stdout:
                        lines = result.stdout.strip().split('\n')
                        # Show first 10 and last 10 lines if output is long
                        if len(lines) > 20:
                            print('\n'.join(lines[:10]))
                            print(f"... ({len(lines)-20} more lines) ...")
                            print('\n'.join(lines[-10:]))
                        else:
                            print(result.stdout)
                        
                else:
                    print(f"❌ Command {i} failed with return code {result.returncode}")
                    if result.stderr:
                        print(f"Error: {result.stderr}")
                    
                    execution_results.append({
                        'command': ' '.join(cmd),
                        'output': result.stderr,
                        'success': False,
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                print(f"❌ Error executing command {i}: {e}")
                execution_results.append({
                    'command': ' '.join(cmd),
                    'output': str(e),
                    'success': False,
                    'timestamp': datetime.now().isoformat()
                })
        
        print(f"\n🎉 Task execution completed!")
        return execution_results
    
    def build_command(self) -> List[str]:
        """Build command based on configuration"""
        commands = []
        
        if self.selected_config['report_type'] in ['daily_report', 'combined']:
            cmd = [self.python_cmd, "daily_report.py"]
            cmd.extend(["--database", self.selected_config['database']])
            
            if self.selected_config['limit']:
                cmd.extend(["--limit", str(self.selected_config['limit'])])
            else:
                cmd.append("--all")
            
            commands.append(cmd)
        
        if self.selected_config['report_type'] in ['deals_categorizer', 'combined']:
            cmd = [self.python_cmd, "deals_categorizer.py"]
            cmd.extend(["--database", self.selected_config['database']])
            
            # Use current year
            current_year = datetime.now().year
            cmd.extend(["--year", str(current_year)])
            cmd.append("--monthly")
            
            if self.selected_config['limit']:
                cmd.extend(["--limit", str(self.selected_config['limit'])])
            
            commands.append(cmd)
        
        return commands
    
    def handle_results_export(self, results: List[Dict]):
        """Handle exporting results to Excel and/or Telegram"""
        successful_results = [r for r in results if r['success']]
        
        if not successful_results:
            print("❌ No successful results to export")
            return
        
        export_options = ["📊 Export to Excel (XLSX)"]
        
        # Add Telegram option if configured
        telegram_status = self.telegram.get_telegram_status()
        if telegram_status['configured']:
            export_options.append("📱 Send to Telegram")
            export_options.append("📊📱 Export to Excel AND Send to Telegram")
        
        export_options.append("❌ Skip export")
        
        questions = [
            inquirer.List('export_type',
                         message="How would you like to handle the results?",
                         choices=export_options)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or "Skip export" in answers['export_type']:
            return
        
        export_type = answers['export_type']
        excel_filename = None
        
        # Export to Excel if requested
        if "Excel" in export_type:
            excel_filename = self.excel_exporter.export_results_to_xlsx(successful_results, self.selected_config)
        
        # Send to Telegram if requested
        if "Telegram" in export_type and telegram_status['configured']:
            message = self.telegram.format_report_message(self.selected_config, successful_results)
            
            # If we don't have an excel file yet, create a temporary one for Telegram
            file_to_send = excel_filename
            if not file_to_send:
                print("📊 Creating Excel file for Telegram...")
                file_to_send = self.excel_exporter.export_results_to_xlsx(successful_results, self.selected_config)
            
            if file_to_send and os.path.exists(file_to_send):
                print(f"📱 Sending to Telegram: {file_to_send}")
                if self.telegram.send_telegram_message(message, file_to_send):
                    print("✓ Results sent to Telegram successfully!")
                    
                    # If this was a temp file and we only sent to Telegram, clean it up
                    if not excel_filename and "Excel" not in export_type:
                        try:
                            os.remove(file_to_send)
                            print("🗑️ Temporary file cleaned up")
                        except:
                            pass
                else:
                    print("❌ Failed to send results to Telegram")
            else:
                print("❌ Could not create Excel file for Telegram")
    
    def show_optimization_info(self):
        """Display current month optimization information"""
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        # Calculate current month date range
        month_start = datetime(current_year, current_month, 1)
        if current_month == 12:
            month_end = datetime(current_year + 1, 1, 1)
        else:
            month_end = datetime(current_year, current_month + 1, 1)
        
        print("\n" + "=" * 70)
        print("🚀 PERFORMANCE OPTIMIZATION ACTIVE")
        print("=" * 70)
        print(f"📅 Current Month: {month_start.strftime('%B %Y')} (Month {current_month})")
        print(f"📊 Date Range: {month_start.strftime('%Y-%m-%d')} to {(month_end - timedelta(days=1)).strftime('%Y-%m-%d')}")
        print(f"⚡ Performance: Only querying current month data")
        print(f"🎯 Optimization: Skipping all historical months")
        print(f"🗄️ Database: {self.selected_config.get('database', 'N/A')}")
        print("=" * 70)
    
    def manage_scheduled_tasks(self):
        """Handle scheduled task management"""
        while True:
            status = self.scheduler.get_scheduler_status()
            
            options = [
                "📅 Create New Scheduled Task",
                "📋 List All Scheduled Tasks",
                "🚀 Execute Task Manually",
                "🔄 Toggle Task (Enable/Disable)",
                "🗑️ Delete Task",
                "📊 Task Monitoring Dashboard",
                "🟢 Start Scheduler" if not status['running'] else "🛑 Stop Scheduler",
                "← Back to Main Menu"
            ]
            
            questions = [
                inquirer.List('action',
                             message=f"📅 Scheduled Task Management (Scheduler: {'🟢 Running' if status['running'] else '🔴 Stopped'}, Active Tasks: {status['active_tasks']}/{status['total_tasks']})",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or "Back to Main Menu" in answers['action']:
                break
            
            action = answers['action']
            
            if "Create New Scheduled Task" in action:
                self.create_scheduled_task_wizard()
            elif "List All Scheduled Tasks" in action:
                self.scheduler.list_tasks()
                input("\nPress Enter to continue...")
            elif "Execute Task Manually" in action:
                self.execute_task_manually()
            elif "Toggle Task" in action:
                self.scheduler.toggle_task()
                input("\nPress Enter to continue...")
            elif "Delete Task" in action:
                self.scheduler.delete_task()
                input("\nPress Enter to continue...")
            elif "Task Monitoring Dashboard" in action:
                self.show_task_monitoring_dashboard()
            elif "Start Scheduler" in action:
                self.scheduler.start_scheduler()
                input("\nPress Enter to continue...")
            elif "Stop Scheduler" in action:
                self.scheduler.stop_scheduler_service()
                input("\nPress Enter to continue...")
    
    def create_scheduled_task_wizard(self):
        """Enhanced task creation wizard with better UI"""
        print("\n📅 Create New Scheduled Task")
        print("=" * 60)
        
        # Check if Telegram is configured
        telegram_status = self.telegram.get_telegram_status()
        if not telegram_status['configured']:
            print("❌ Telegram integration not configured!")
            print("Please setup Telegram integration first.")
            
            setup_question = [
                inquirer.Confirm('setup_telegram', 
                               message="Would you like to setup Telegram integration now?", 
                               default=True)
            ]
            setup_answer = inquirer.prompt(setup_question)
            
            if setup_answer and setup_answer['setup_telegram']:
                if self.telegram.setup_telegram_integration():
                    print("✓ Telegram integration setup complete!")
                else:
                    print("❌ Telegram integration setup failed!")
                    return False
            else:
                return False
        
        try:
            # Enhanced task creation with better validation
            questions = [
                inquirer.Text('task_name', 
                             message="Task Name (unique identifier)",
                             validate=lambda _, x: len(x.strip()) > 0 and not any(c in x for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|'])),
                inquirer.Text('description', 
                             message="Task Description",
                             validate=lambda _, x: len(x.strip()) > 0),
                inquirer.List('report_type', 
                             message="Report Type",
                             choices=[
                                 ('Daily Financial Report', 'Daily Report'),
                                 ('Weekly Financial Summary', 'Weekly Report'),
                                 ('Monthly Financial Overview', 'Monthly Report'),
                                 ('Saved Configuration Report', 'Saved Configuration Report')
                             ]),
                inquirer.List('database', 
                             message="Target Database",
                             choices=[
                                 ('MT5GN Live Server', 'mt5gn_live'),
                                 ('MT5LC Live Server', 'mt5lc_live'),
                                 ('MT5W2 Live Server', 'mt5w2_live'),
                                 ('MT5EX Live Server', 'mt5ex_live')
                             ]),
                inquirer.Text('chat_id', 
                             message="Telegram Chat ID (use @userinfobot to get your chat ID)",
                             validate=lambda _, x: x.strip().startswith('-') or x.strip().isdigit()),
                inquirer.Text('send_time', 
                             message="Send Time (HH:MM format, e.g., 09:30)",
                             validate=self._validate_time_format),
                inquirer.List('frequency', 
                             message="Frequency",
                             choices=[
                                 ('Every Day', 'Daily'),
                                 ('Every Monday', 'Weekly'),
                                 ('First day of every month', 'Monthly')
                             ]),
                inquirer.Confirm('active', 
                               message="Activate this task immediately?", 
                               default=True)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers:
                print("❌ Task creation cancelled")
                return False
            
            # If Saved Configuration Report selected, ask for configuration
            saved_config_name = None
            if answers['report_type'] == 'Saved Configuration Report':
                saved_configs = self.scheduler.config_manager.load_all_configs()
                if not saved_configs:
                    print("❌ No saved configurations found!")
                    print("Please create a configuration first using 'Create New Report'.")
                    
                    create_question = [
                        inquirer.Confirm('create_config', 
                                       message="Would you like to create a configuration now?", 
                                       default=True)
                    ]
                    create_answer = inquirer.prompt(create_question)
                    
                    if create_answer and create_answer['create_config']:
                        print("📋 Redirecting to configuration creation...")
                        print("Please use 'Create New Report' from the main menu to create a configuration first.")
                        return False
                    else:
                        return False
                
                config_choices = []
                for name, config in saved_configs.items():
                    groups_info = f"{len(config.get('groups', []))} groups" if config.get('groups') else "All groups"
                    database = config.get('database', 'Unknown')
                    report_type = config.get('report_type', 'Unknown')
                    saved_at = config.get('saved_at', '')
                    
                    # Format saved date
                    date_str = ""
                    if saved_at:
                        try:
                            saved_dt = datetime.fromisoformat(saved_at)
                            date_str = f" ({saved_dt.strftime('%m/%d %H:%M')})"
                        except:
                            pass
                    
                    choice_text = f"{name} - {database} - {groups_info} - {report_type}{date_str}"
                    config_choices.append((choice_text, name))
                
                config_question = [
                    inquirer.List('config_name',
                                 message="Select saved configuration to use for scheduled reports",
                                 choices=config_choices)
                ]
                
                config_answer = inquirer.prompt(config_question)
                if not config_answer:
                    print("❌ Configuration selection cancelled")
                    return False
                
                saved_config_name = config_answer['config_name']
                selected_config = saved_configs[saved_config_name]
                
                print(f"\n✓ Selected configuration: {saved_config_name}")
                print(f"   📊 Report Type: {selected_config.get('report_type', 'Unknown')}")
                print(f"   🗄️ Database: {selected_config.get('database', 'Unknown')}")
                print(f"   👥 Groups: {len(selected_config.get('groups', []))} selected")
                print(f"   🔢 Login Range: {selected_config.get('min_login', 'N/A')} - {selected_config.get('max_login', 'N/A')}")
                print(f"   📋 Record Limit: {selected_config.get('limit', 'N/A')}")
            
            # Check task name uniqueness
            if answers['task_name'] in self.scheduler.tasks:
                print(f"❌ Task '{answers['task_name']}' already exists!")
                return False
            
            # Show configuration summary
            print(f"\n📋 Task Configuration Summary:")
            print(f"   📌 Name: {answers['task_name']}")
            print(f"   📝 Description: {answers['description']}")
            print(f"   📊 Report Type: {answers['report_type']}")
            if saved_config_name:
                print(f"   🔧 Using Configuration: {saved_config_name}")
                selected_config = saved_configs[saved_config_name]
                print(f"      - Database Override: {answers['database']} (config: {selected_config.get('database', 'N/A')})")
                print(f"      - Groups: {len(selected_config.get('groups', []))} from config")
                print(f"      - Config Report Type: {selected_config.get('report_type', 'N/A')}")
            else:
                print(f"   🗄️ Database: {answers['database']}")
            print(f"   💬 Chat ID: {answers['chat_id']}")
            print(f"   ⏰ Schedule: {answers['frequency']} at {answers['send_time']}")
            print(f"   🔄 Status: {'Active' if answers['active'] else 'Inactive'}")
            
            confirm_questions = [
                inquirer.Confirm('confirm_create', 
                               message="Create this scheduled task?", 
                               default=True)
            ]
            
            confirm_answers = inquirer.prompt(confirm_questions)
            if not confirm_answers or not confirm_answers['confirm_create']:
                print("❌ Task creation cancelled")
                return False
            
            # Test chat ID with enhanced message
            print(f"\n🔍 Testing chat ID {answers['chat_id']}...")
            
            if saved_config_name:
                selected_config = saved_configs[saved_config_name]
                test_message = f"""🤖 <b>Task Creator - Connection Test</b>

✅ <b>Test Successful!</b>
📅 <b>Scheduled Task:</b> {answers['task_name']}
📊 <b>Report Type:</b> {answers['report_type']}
🔧 <b>Using Configuration:</b> {saved_config_name}

<b>Configuration Details:</b>
🗄️ <b>Database:</b> {answers['database']} (config: {selected_config.get('database', 'N/A')})
👥 <b>Groups:</b> {len(selected_config.get('groups', []))} from saved config
📋 <b>Config Report Type:</b> {selected_config.get('report_type', 'N/A')}
🔢 <b>Login Range:</b> {selected_config.get('min_login', 'N/A')} - {selected_config.get('max_login', 'N/A')}
⏰ <b>Schedule:</b> {answers['frequency']} at {answers['send_time']}

This chat will receive automated reports using the saved configuration."""
            else:
                test_message = f"""🤖 <b>Task Creator - Connection Test</b>

✅ <b>Test Successful!</b>
📅 <b>Scheduled Task:</b> {answers['task_name']}
📊 <b>Report Type:</b> {answers['report_type']}
🗄️ <b>Database:</b> {answers['database'].upper()}
⏰ <b>Schedule:</b> {answers['frequency']} at {answers['send_time']}

This chat will receive automated reports according to the schedule above."""
            
            if not self.telegram.send_telegram_message(test_message, chat_id=answers['chat_id']):
                print("❌ Failed to send test message to chat ID")
                continue_question = [
                    inquirer.Confirm('continue_anyway', 
                                   message="Continue creating task anyway?", 
                                   default=False)
                ]
                continue_answer = inquirer.prompt(continue_question)
                if not continue_answer or not continue_answer['continue_anyway']:
                    return False
            else:
                print("✓ Test message sent successfully!")
            
            # Create task
            task = {
                'task_name': answers['task_name'],
                'description': answers['description'],
                'report_type': answers['report_type'],
                'database': answers['database'],
                'chat_id': answers['chat_id'],
                'send_time': answers['send_time'],
                'frequency': answers['frequency'],
                'active': answers['active'],
                'created_at': datetime.now().isoformat(),
                'last_run': None,
                'next_run': self.scheduler._calculate_next_run(answers['send_time'], answers['frequency']),
                'run_count': 0,
                'success_count': 0,
                'error_count': 0,
                'last_error': None,
                'saved_config_name': saved_config_name  # Store the configuration name
            }
            
            # Save task
            self.scheduler.tasks[answers['task_name']] = task
            if self.scheduler._save_tasks():
                print(f"\n🎉 Task '{answers['task_name']}' created successfully!")
                if answers['active']:
                    next_run = datetime.fromisoformat(task['next_run'])
                    print(f"📅 Next run scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Ask if user wants to start scheduler if not running
                status = self.scheduler.get_scheduler_status()
                if not status['running']:
                    start_question = [
                        inquirer.Confirm('start_scheduler', 
                                       message="Scheduler is not running. Would you like to start it now?", 
                                       default=True)
                    ]
                    start_answer = inquirer.prompt(start_question)
                    if start_answer and start_answer['start_scheduler']:
                        self.scheduler.start_scheduler()
                
                return True
            else:
                print("❌ Failed to save task")
                return False
                
        except KeyboardInterrupt:
            print("\n❌ Task creation cancelled")
            return False
        except Exception as e:
            print(f"❌ Error creating task: {e}")
            return False
    
    def _validate_time_format(self, _, time_str):
        """Validate time format HH:MM"""
        try:
            time_parts = time_str.split(':')
            if len(time_parts) != 2:
                return False
            hour, minute = int(time_parts[0]), int(time_parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except:
            return False
    
    def execute_task_manually(self):
        """Execute a task manually with enhanced feedback"""
        if not self.scheduler.tasks:
            print("No tasks available.")
            return
        
        task_choices = []
        for task_name, task in self.scheduler.tasks.items():
            status = "🟢 Active" if task['active'] else "🔴 Inactive"
            last_run = task.get('last_run')
            last_run_str = ""
            if last_run:
                try:
                    last_run_time = datetime.fromisoformat(last_run)
                    last_run_str = f" (Last: {last_run_time.strftime('%m/%d %H:%M')})"
                except:
                    pass
            
            choice_text = f"{task_name} - {task['database']} - {status}{last_run_str}"
            task_choices.append((choice_text, task_name))
        
        questions = [
            inquirer.List('task_name',
                         message="Select task to execute manually",
                         choices=task_choices)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return
        
        task_name = answers['task_name']
        task = self.scheduler.tasks[task_name]
        
        print(f"\n🚀 Executing task: {task_name}")
        print(f"📊 Report Type: {task['report_type']}")
        print(f"🗄️ Database: {task['database']}")
        print(f"💬 Target Chat: {task['chat_id']}")
        print("⏳ Generating report...")
        
        success = self.scheduler.execute_task(task_name)
        
        if success:
            print("✅ Task executed successfully!")
        else:
            print("❌ Task execution failed!")
        
        input("\nPress Enter to continue...")
    
    def show_task_monitoring_dashboard(self):
        """Show an enhanced monitoring dashboard with health checks"""
        while True:
            print("\n📊 Task Monitoring Dashboard")
            print("=" * 80)
            
            if not self.scheduler.tasks:
                print("No scheduled tasks found.")
                input("\nPress Enter to continue...")
                return
            
            # Get detailed statistics
            stats = self.scheduler.get_task_statistics()
            health_report = self.scheduler.get_task_health_report()
            
            # Scheduler status overview
            status = self.scheduler.get_scheduler_status()
            scheduler_status = "🟢 Running" if status['running'] else "🔴 Stopped"
            
            print(f"🔧 Scheduler Status: {scheduler_status}")
            print(f"📊 Tasks Overview:")
            print(f"   • Total Tasks: {stats['total_tasks']}")
            print(f"   • Active: {stats['active_tasks']} | Inactive: {stats['inactive_tasks']}")
            print(f"   • Healthy: {len([h for h in health_report if '🟢' in h['health_status']])}")
            print(f"   • Warning: {len([h for h in health_report if '🟡' in h['health_status']])}")
            print(f"   • Unhealthy: {len([h for h in health_report if '🔴' in h['health_status']])}")
            
            print(f"\n📈 Execution Statistics:")
            print(f"   • Total Executions: {stats['total_executions']}")
            print(f"   • Successful: {stats['successful_executions']} ({stats['success_rate']:.1f}%)")
            print(f"   • Failed: {stats['failed_executions']}")
            print(f"   • Tasks with Errors: {stats['tasks_with_errors']}")
            
            # Next and last execution info
            if stats['next_execution']:
                next_exec_str = stats['next_execution'].strftime('%Y-%m-%d %H:%M:%S')
                time_until = stats['next_execution'] - datetime.now()
                if time_until.total_seconds() > 0:
                    if time_until.days > 0:
                        time_str = f"in {time_until.days}d {time_until.seconds//3600}h"
                    elif time_until.seconds > 3600:
                        time_str = f"in {time_until.seconds//3600}h {(time_until.seconds%3600)//60}m"
                    else:
                        time_str = f"in {time_until.seconds//60}m"
                    print(f"   • Next Execution: {next_exec_str} ({time_str})")
                else:
                    print(f"   • Next Execution: {next_exec_str} (⚠️ Overdue)")
            
            if stats['last_execution']:
                last_exec_str = stats['last_execution'].strftime('%Y-%m-%d %H:%M:%S')
                print(f"   • Last Execution: {last_exec_str}")
            
            # Tasks health table
            table_data = []
            now = datetime.now()
            
            for health in health_report:
                task = self.scheduler.tasks[health['task_name']]
                
                # Next run info
                next_run_str = "Not scheduled"
                time_until = ""
                if health['next_run'] and task['active']:
                    try:
                        next_run = datetime.fromisoformat(health['next_run'])
                        next_run_str = next_run.strftime('%m/%d %H:%M')
                        
                        # Calculate time until next run
                        time_diff = next_run - now
                        if time_diff.total_seconds() > 0:
                            if time_diff.days > 0:
                                time_until = f"{time_diff.days}d"
                            elif time_diff.seconds > 3600:
                                hours = time_diff.seconds // 3600
                                time_until = f"{hours}h"
                            elif time_diff.seconds > 60:
                                minutes = time_diff.seconds // 60
                                time_until = f"{minutes}m"
                            else:
                                time_until = "< 1m"
                        else:
                            time_until = "Overdue!"
                    except:
                        pass
                
                # Last run info
                last_run_str = "Never"
                if health['last_run']:
                    try:
                        last_run = datetime.fromisoformat(health['last_run'])
                        last_run_str = last_run.strftime('%m/%d %H:%M')
                    except:
                        pass
                
                # Issues summary
                issues_str = ""
                if health['issues']:
                    issues_str = "; ".join(health['issues'][:2])  # Show first 2 issues
                    if len(health['issues']) > 2:
                        issues_str += f" (+{len(health['issues'])-2} more)"
                
                table_data.append([
                    health['health_status'],
                    health['task_name'][:20],
                    task['frequency'][:8],
                    task['send_time'],
                    task['database'][:10],
                    next_run_str,
                    time_until,
                    last_run_str,
                    health['total_runs'],
                    f"{health['success_rate']:.1f}%" if health['total_runs'] > 0 else "N/A",
                    issues_str[:30] + "..." if len(issues_str) > 30 else issues_str
                ])
            
            headers = ['Health', 'Task', 'Freq', 'Time', 'Database', 'Next Run', 'Until', 'Last Run', 'Runs', 'Success', 'Issues']
            print(f"\n🏥 Task Health Report:")
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            # Recent activity with more details
            recent_activities = []
            for task_name, task in self.scheduler.tasks.items():
                if task.get('last_run'):
                    try:
                        last_run = datetime.fromisoformat(task['last_run'])
                        recent_activities.append({
                            'task': task_name,
                            'time': last_run,
                            'success': task.get('last_error') is None,
                            'database': task['database'],
                            'chat_id': task['chat_id']
                        })
                    except:
                        pass
            
            if recent_activities:
                recent_activities.sort(key=lambda x: x['time'], reverse=True)
                print(f"\n🕐 Recent Activity (Last 10):")
                for i, activity in enumerate(recent_activities[:10]):
                    status_icon = "✅" if activity['success'] else "❌"
                    time_str = activity['time'].strftime('%m/%d %H:%M:%S')
                    print(f"   {i+1:2d}. {status_icon} {activity['task'][:20]:20} | {activity['database'][:10]:10} | {time_str}")
            
            # Show alerts for unhealthy tasks
            unhealthy_tasks = [h for h in health_report if '🔴' in h['health_status']]
            if unhealthy_tasks:
                print(f"\n🚨 Alerts ({len(unhealthy_tasks)} unhealthy tasks):")
                for task_health in unhealthy_tasks:
                    print(f"   🔴 {task_health['task_name']}: {'; '.join(task_health['issues'])}")
            
            # Dashboard actions
            options = [
                "🔄 Refresh Dashboard",
                "🚀 Execute Unhealthy Task",
                "📋 Show Detailed Task Info",
                "⚙️ Task Quick Actions",
                "← Back to Scheduler Menu"
            ]
            
            questions = [
                inquirer.List('action',
                             message="Dashboard Actions",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or "Back to Scheduler Menu" in answers['action']:
                break
            elif "Execute Unhealthy Task" in answers['action']:
                self._execute_unhealthy_task()
            elif "Show Detailed Task Info" in answers['action']:
                self._show_detailed_task_info()
            elif "Task Quick Actions" in answers['action']:
                self._task_quick_actions()
            # If refresh is selected, the loop continues
    
    def _execute_unhealthy_task(self):
        """Execute an unhealthy task manually"""
        health_report = self.scheduler.get_task_health_report()
        unhealthy_tasks = [h for h in health_report if '🔴' in h['health_status']]
        
        if not unhealthy_tasks:
            print("✅ No unhealthy tasks found!")
            return
        
        task_choices = []
        for health in unhealthy_tasks:
            issues_str = "; ".join(health['issues'][:2])
            choice_text = f"{health['task_name']} - {issues_str}"
            task_choices.append((choice_text, health['task_name']))
        
        questions = [
            inquirer.List('task_name',
                         message="Select unhealthy task to execute",
                         choices=task_choices)
        ]
        
        answers = inquirer.prompt(questions)
        if answers:
            task_name = answers['task_name']
            print(f"\n🚀 Executing unhealthy task: {task_name}")
            self.scheduler.execute_task(task_name)
    
    def _show_detailed_task_info(self):
        """Show detailed information about a specific task"""
        if not self.scheduler.tasks:
            print("No tasks available.")
            return
        
        task_choices = list(self.scheduler.tasks.keys())
        questions = [
            inquirer.List('task_name',
                         message="Select task for detailed info",
                         choices=task_choices)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return
        
        task_name = answers['task_name']
        task = self.scheduler.tasks[task_name]
        
        print(f"\n📋 Detailed Task Information: {task_name}")
        print("=" * 60)
        print(f"📝 Description: {task['description']}")
        print(f"📊 Report Type: {task['report_type']}")
        if task.get('saved_config_name'):
            print(f"🔧 Saved Configuration: {task['saved_config_name']}")
            # Load and show config details
            config = self.scheduler.config_manager.load_config(task['saved_config_name'])
            if config:
                print(f"   📋 Config Report Type: {config.get('report_type', 'Unknown')}")
                print(f"   👥 Config Groups: {len(config.get('groups', []))} selected")
                print(f"   🔢 Config Login Range: {config.get('min_login', 'N/A')} - {config.get('max_login', 'N/A')}")
                print(f"   📊 Config Limit: {config.get('limit', 'N/A')}")
            else:
                print(f"   ⚠️ Configuration '{task['saved_config_name']}' not found!")
        print(f"🗄️ Database: {task['database']}")
        print(f"💬 Chat ID: {task['chat_id']}")
        print(f"⏰ Schedule: {task['frequency']} at {task['send_time']}")
        print(f"🔄 Status: {'🟢 Active' if task['active'] else '🔴 Inactive'}")
        print(f"📅 Created: {task.get('created_at', 'Unknown')}")
        
        if task.get('next_run'):
            try:
                next_run = datetime.fromisoformat(task['next_run'])
                print(f"⏭️ Next Run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                print(f"⏭️ Next Run: {task['next_run']}")
        
        if task.get('last_run'):
            try:
                last_run = datetime.fromisoformat(task['last_run'])
                print(f"⏮️ Last Run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                print(f"⏮️ Last Run: {task['last_run']}")
        
        print(f"📊 Statistics:")
        print(f"   • Total Runs: {task.get('run_count', 0)}")
        print(f"   • Successful: {task.get('success_count', 0)}")
        print(f"   • Failed: {task.get('error_count', 0)}")
        
        if task.get('run_count', 0) > 0:
            success_rate = (task.get('success_count', 0) / task['run_count']) * 100
            print(f"   • Success Rate: {success_rate:.1f}%")
        
        if task.get('last_error'):
            print(f"❌ Last Error: {task['last_error']}")
        
        input("\nPress Enter to continue...")
    
    def _task_quick_actions(self):
        """Quick actions for task management"""
        if not self.scheduler.tasks:
            print("No tasks available.")
            return
        
        actions = [
            "🔄 Toggle All Tasks",
            "🚀 Execute All Active Tasks",
            "🧹 Clear Error History",
            "📊 Export Task Statistics",
            "← Back"
        ]
        
        questions = [
            inquirer.List('action',
                         message="Quick Actions",
                         choices=actions)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or "Back" in answers['action']:
            return
        
        action = answers['action']
        
        if "Toggle All Tasks" in action:
            enable_question = [
                inquirer.Confirm('enable', 
                               message="Enable all tasks? (No = disable all)", 
                               default=True)
            ]
            enable_answer = inquirer.prompt(enable_question)
            if enable_answer:
                enable_all = enable_answer['enable']
                count = 0
                for task_name, task in self.scheduler.tasks.items():
                    if task['active'] != enable_all:
                        task['active'] = enable_all
                        if enable_all:
                            task['next_run'] = self.scheduler._calculate_next_run(task['send_time'], task['frequency'])
                        count += 1
                
                if self.scheduler._save_tasks():
                    action_word = "enabled" if enable_all else "disabled"
                    print(f"✓ {action_word.capitalize()} {count} tasks")
                else:
                    print("❌ Failed to save changes")
        
        elif "Execute All Active Tasks" in action:
            active_tasks = [name for name, task in self.scheduler.tasks.items() if task['active']]
            if not active_tasks:
                print("No active tasks to execute.")
                return
            
            confirm_question = [
                inquirer.Confirm('confirm', 
                               message=f"Execute {len(active_tasks)} active tasks?", 
                               default=True)
            ]
            confirm_answer = inquirer.prompt(confirm_question)
            
            if confirm_answer and confirm_answer['confirm']:
                print(f"🚀 Executing {len(active_tasks)} active tasks...")
                success_count = 0
                for task_name in active_tasks:
                    print(f"   Executing: {task_name}")
                    if self.scheduler.execute_task(task_name):
                        success_count += 1
                
                print(f"✓ Completed: {success_count}/{len(active_tasks)} tasks successful")
        
        elif "Clear Error History" in action:
            confirm_question = [
                inquirer.Confirm('confirm', 
                               message="Clear all error history from tasks?", 
                               default=False)
            ]
            confirm_answer = inquirer.prompt(confirm_question)
            
            if confirm_answer and confirm_answer['confirm']:
                count = 0
                for task in self.scheduler.tasks.values():
                    if task.get('last_error'):
                        task['last_error'] = None
                        task['error_count'] = 0
                        count += 1
                
                if self.scheduler._save_tasks():
                    print(f"✓ Cleared error history for {count} tasks")
                else:
                    print("❌ Failed to save changes")
        
        elif "Export Task Statistics" in action:
            print("📊 Task Statistics Export:")
            stats = self.scheduler.get_task_statistics()
            
            export_data = []
            for task_name, task in self.scheduler.tasks.items():
                export_data.append([
                    task_name,
                    task['description'],
                    task['database'],
                    task['frequency'],
                    task['send_time'],
                    'Active' if task['active'] else 'Inactive',
                    task.get('run_count', 0),
                    task.get('success_count', 0),
                    task.get('error_count', 0),
                    f"{(task.get('success_count', 0) / max(task.get('run_count', 1), 1)) * 100:.1f}%",
                    task.get('last_run', 'Never'),
                    task.get('next_run', 'Not scheduled'),
                    task.get('last_error', 'None')
                ])
            
            headers = ['Task Name', 'Description', 'Database', 'Frequency', 'Time', 'Status', 
                      'Total Runs', 'Successful', 'Failed', 'Success Rate', 
                      'Last Run', 'Next Run', 'Last Error']
            
            print(tabulate(export_data, headers=headers, tablefmt='grid'))
            
            # Offer to save to file
            save_question = [
                inquirer.Confirm('save_file', 
                               message="Save statistics to CSV file?", 
                               default=False)
            ]
            save_answer = inquirer.prompt(save_question)
            
            if save_answer and save_answer['save_file']:
                import csv
                from datetime import datetime
                
                filename = f"task_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = os.path.join(os.getcwd(), filename)
                
                try:
                    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(headers)
                        writer.writerows(export_data)
                    
                    print(f"✓ Statistics exported to: {filepath}")
                except Exception as e:
                    print(f"❌ Failed to export statistics: {e}")
        
        input("\nPress Enter to continue...")

    # ...existing code...

    # ...existing code...
def main():
    """Main function to run the interactive task creator"""
    task_creator = None
    try:
        # Create and run the task creator
        task_creator = TaskCreator()
        task_creator.show_welcome()
        task_creator.show_main_menu()
    except KeyboardInterrupt:
        print("\n❌ Task creator interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error in main: {e}")
    finally:
        # Ensure scheduler is properly stopped
        if task_creator and hasattr(task_creator, 'scheduler'):
            try:
                status = task_creator.scheduler.get_scheduler_status()
                if status['running']:
                    print("🛑 Stopping scheduler before exit...")
                    task_creator.scheduler.stop_scheduler_service()
                    import time
                    time.sleep(2)  # Give scheduler time to stop
            except AttributeError:
                print("⚠️ Scheduler does not have get_scheduler_status method")
            except Exception as e:
                print(f"⚠️ Error stopping scheduler: {e}")
        print("👋 Goodbye!")


if __name__ == "__main__":
    main()
