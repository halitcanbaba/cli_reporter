#!/usr/bin/env python3
"""
Scheduled Task Manager
Manages scheduled tasks for sending reports to different Telegram groups at specified times
"""

import os
import json
import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import inquirer
from telegram_bot import TelegramIntegration
from config_manager import ConfigManager


class ScheduledTaskManager:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.task_creator")
        self.tasks_config_file = os.path.join(self.config_dir, "scheduled_tasks.json")
        self.telegram_integration = TelegramIntegration()
        self.config_manager = ConfigManager()
        self.tasks = {}
        self.scheduler_thread = None
        self.stop_scheduler = False
        self._ensure_config_dir()
        self._load_tasks()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
    
    def _load_tasks(self):
        """Load scheduled tasks from file"""
        try:
            if os.path.exists(self.tasks_config_file):
                with open(self.tasks_config_file, 'r') as f:
                    self.tasks = json.load(f)
                    print(f"✓ Loaded {len(self.tasks)} scheduled tasks")
            else:
                self.tasks = {}
        except Exception as e:
            print(f"❌ Error loading tasks: {e}")
            self.tasks = {}
    
    def _save_tasks(self):
        """Save scheduled tasks to file"""
        try:
            with open(self.tasks_config_file, 'w') as f:
                json.dump(self.tasks, f, indent=2)
            print("✓ Tasks saved successfully")
            return True
        except Exception as e:
            print(f"❌ Error saving tasks: {e}")
            return False
    
    def create_task(self):
        """Create a new scheduled task"""
        print("\n📅 Create New Scheduled Task")
        print("=" * 50)
        
        # Check if Telegram is configured
        telegram_status = self.telegram_integration.get_telegram_status()
        if not telegram_status['configured']:
            print("❌ Telegram integration not configured!")
            print("Please setup Telegram integration first.")
            return False
        
        try:
            # First ask basic questions
            basic_questions = [
                inquirer.Text('task_name', message="Enter task name (unique identifier)"),
                inquirer.Text('description', message="Enter task description"),
                inquirer.List('report_type', 
                             message="Select report type",
                             choices=['Saved Configuration Report'])
            ]
            
            basic_answers = inquirer.prompt(basic_questions)
            if not basic_answers:
                print("❌ Task creation cancelled")
                return False
            
            # Initialize answers dict
            answers = basic_answers.copy()
            
            # For saved configuration, database will come from config
            answers['database'] = 'from_config'
            
            # Ask remaining questions
            remaining_questions = [
                inquirer.Text('chat_id', message="Enter Telegram chat ID (group or private)"),
                inquirer.Text('send_time', message="Enter send time (HH:MM format, e.g., 09:30)"),
                inquirer.List('frequency', 
                             message="Select frequency",
                             choices=['Daily', 'Weekly', 'Monthly']),
                inquirer.Confirm('active', message="Activate this task immediately?", default=True)
            ]
            
            remaining_answers = inquirer.prompt(remaining_questions)
            if not remaining_answers:
                print("❌ Task creation cancelled")
                return False
            
            answers.update(remaining_answers)
            
            # Get saved configuration
            saved_configs = self.config_manager.load_all_configs()
            if not saved_configs:
                print("❌ No saved configurations found!")
                print("Please create a configuration first using the main task creator.")
                return False
            
            config_choices = []
            for name, config in saved_configs.items():
                groups_info = f"{len(config.get('groups', []))} groups" if config.get('groups') else "All groups"
                database = config.get('database', 'Unknown')
                report_type = config.get('report_type', 'Unknown')
                choice_text = f"{name} - {database} - {groups_info} - {report_type}"
                config_choices.append((choice_text, name))
            
            config_question = [
                inquirer.List('config_name',
                             message="Select saved configuration to use",
                             choices=config_choices)
            ]
            
            config_answer = inquirer.prompt(config_question)
            if not config_answer:
                print("❌ Configuration selection cancelled")
                return False
            
            saved_config_name = config_answer['config_name']
            selected_config = saved_configs[saved_config_name]
            
            # Update database from configuration
            answers['database'] = selected_config.get('database', 'mt5gn_live')
            
            print(f"✓ Selected configuration: {saved_config_name}")
            print(f"   📊 Report Type: {selected_config.get('report_type', 'Unknown')}")
            print(f"   🗄️ Database: {answers['database']}")
            print(f"   👥 Groups: {len(selected_config.get('groups', []))} selected" if selected_config.get('groups') else "   👥 Groups: All groups")
            print(f"   🔢 Login Range: {selected_config.get('min_login', 'N/A')} - {selected_config.get('max_login', 'N/A')}")
            print(f"   📋 Record Limit: {selected_config.get('limit', 'N/A')}")
            
            # Validate task name uniqueness
            if answers['task_name'] in self.tasks:
                print(f"❌ Task '{answers['task_name']}' already exists!")
                return False
            
            # Validate time format
            try:
                time_parts = answers['send_time'].split(':')
                if len(time_parts) != 2:
                    raise ValueError("Invalid time format")
                hour, minute = int(time_parts[0]), int(time_parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time values")
            except ValueError:
                print("❌ Invalid time format! Please use HH:MM format (e.g., 09:30)")
                return False
            
            # Test chat ID
            print(f"\n🔍 Testing chat ID {answers['chat_id']}...")
            test_message = f"🤖 Task Creator Test\n\nTesting connection for scheduled task: {answers['task_name']}"
            
            if not self.telegram_integration.send_telegram_message(test_message, chat_id=answers['chat_id']):
                print("❌ Failed to send test message to chat ID")
                confirm = inquirer.confirm("Continue anyway?", default=False)
                if not confirm:
                    return False
            else:
                print("✓ Test message sent successfully!")
            
            # Create task object
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
                'next_run': self._calculate_next_run(answers['send_time'], answers['frequency']),
                'run_count': 0,
                'saved_config_name': saved_config_name  # Store the configuration name
            }
            
            # Save task
            self.tasks[answers['task_name']] = task
            if self._save_tasks():
                print(f"✓ Task '{answers['task_name']}' created successfully!")
                if answers['active']:
                    print(f"📅 Next run scheduled for: {task['next_run']}")
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
    
    def _calculate_next_run(self, send_time: str, frequency: str) -> str:
        """Calculate next run time for a task"""
        try:
            hour, minute = map(int, send_time.split(':'))
            now = datetime.now()
            
            if frequency == 'Daily':
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
            elif frequency == 'Weekly':
                # Schedule for next Monday at specified time
                days_ahead = 0 - now.weekday()  # Monday is 0
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            elif frequency == 'Monthly':
                # Schedule for first day of next month
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=1, hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=1, hour=hour, minute=minute, second=0, microsecond=0)
            else:
                next_run = now + timedelta(days=1)
            
            return next_run.isoformat()
        except Exception as e:
            print(f"❌ Error calculating next run: {e}")
            return datetime.now().isoformat()
    
    def list_tasks(self):
        """List all scheduled tasks"""
        print("\n📋 Scheduled Tasks")
        print("=" * 80)
        
        if not self.tasks:
            print("No scheduled tasks found.")
            return
        
        for task_name, task in self.tasks.items():
            status = "🟢 Active" if task['active'] else "🔴 Inactive"
            print(f"\n📌 {task_name}")
            print(f"   Description: {task['description']}")
            print(f"   Report Type: {task['report_type']}")
            if task.get('saved_config_name'):
                print(f"   Configuration: {task['saved_config_name']}")
            print(f"   Database: {task['database']}")
            print(f"   Chat ID: {task['chat_id']}")
            print(f"   Schedule: {task['frequency']} at {task['send_time']}")
            print(f"   Status: {status}")
            print(f"   Next Run: {task.get('next_run', 'Not scheduled')}")
            print(f"   Run Count: {task.get('run_count', 0)}")
            if task.get('last_run'):
                print(f"   Last Run: {task['last_run']}")
            if task.get('success_count', 0) > 0:
                success_rate = (task.get('success_count', 0) / max(task.get('run_count', 1), 1)) * 100
                print(f"   Success Rate: {success_rate:.1f}%")
    
    def toggle_task(self, task_name: str = None):
        """Toggle task active/inactive status"""
        if not self.tasks:
            print("No tasks available.")
            return False
        
        if not task_name:
            choices = list(self.tasks.keys())
            questions = [
                inquirer.List('task_name', 
                             message="Select task to toggle",
                             choices=choices)
            ]
            answers = inquirer.prompt(questions)
            if not answers:
                return False
            task_name = answers['task_name']
        
        if task_name not in self.tasks:
            print(f"❌ Task '{task_name}' not found!")
            return False
        
        task = self.tasks[task_name]
        task['active'] = not task['active']
        
        if task['active']:
            # Recalculate next run when activating
            task['next_run'] = self._calculate_next_run(task['send_time'], task['frequency'])
        
        if self._save_tasks():
            status = "activated" if task['active'] else "deactivated"
            print(f"✓ Task '{task_name}' {status} successfully!")
            return True
        else:
            print("❌ Failed to update task")
            return False
    
    def delete_task(self, task_name: str = None):
        """Delete a scheduled task"""
        if not self.tasks:
            print("No tasks available.")
            return False
        
        if not task_name:
            choices = list(self.tasks.keys())
            questions = [
                inquirer.List('task_name', 
                             message="Select task to delete",
                             choices=choices),
                inquirer.Confirm('confirm', message="Are you sure you want to delete this task?", default=False)
            ]
            answers = inquirer.prompt(questions)
            if not answers or not answers['confirm']:
                return False
            task_name = answers['task_name']
        
        if task_name not in self.tasks:
            print(f"❌ Task '{task_name}' not found!")
            return False
        
        del self.tasks[task_name]
        
        if self._save_tasks():
            print(f"✓ Task '{task_name}' deleted successfully!")
            return True
        else:
            print("❌ Failed to delete task")
            return False
    
    def execute_task(self, task_name: str):
        """Execute a specific task manually"""
        if task_name not in self.tasks:
            print(f"❌ Task '{task_name}' not found!")
            return False
        
        task = self.tasks[task_name]
        
        print(f"🚀 Executing task: {task_name}")
        
        try:
            # Generate report based on type
            if task['report_type'] == 'Saved Configuration Report':
                # Generate report using saved configuration
                report_result = self._generate_config_based_report(task)
                
                if isinstance(report_result, dict):
                    # We have Excel file to send
                    message = report_result['message']
                    excel_file = report_result['excel_file']
                    
                    # Send message with Excel file to Telegram
                    success = self.telegram_integration.send_telegram_message(
                        message=message,
                        file_path=excel_file,
                        chat_id=task['chat_id']
                    )
                    
                    # Clean up Excel file after sending
                    try:
                        import os
                        if os.path.exists(excel_file):
                            os.remove(excel_file)
                            print(f"✓ Cleaned up Excel file: {excel_file}")
                    except Exception as e:
                        print(f"⚠️ Could not remove Excel file: {e}")
                        
                else:
                    # Error message, send as text
                    success = self.telegram_integration.send_telegram_message(
                        message=report_result,
                        chat_id=task['chat_id']
                    )
            else:
                # Unsupported report type
                error_message = f"❌ Unsupported report type: {task['report_type']}\n\nOnly 'Saved Configuration Report' is supported."
                success = self.telegram_integration.send_telegram_message(
                    message=error_message,
                    chat_id=task['chat_id']
                )
            
            if success:
                # Update task execution info
                task['last_run'] = datetime.now().isoformat()
                task['run_count'] = task.get('run_count', 0) + 1
                task['success_count'] = task.get('success_count', 0) + 1
                task['next_run'] = self._calculate_next_run(task['send_time'], task['frequency'])
                task['last_error'] = None  # Clear any previous errors
                self._save_tasks()
                
                print(f"✓ Task '{task_name}' executed successfully!")
                print(f"📅 Next run scheduled for: {task['next_run']}")
                return True
            else:
                # Update error tracking
                task['last_run'] = datetime.now().isoformat()
                task['run_count'] = task.get('run_count', 0) + 1
                task['error_count'] = task.get('error_count', 0) + 1
                task['last_error'] = f"Failed to send report at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                task['next_run'] = self._calculate_next_run(task['send_time'], task['frequency'])
                self._save_tasks()
                
                print(f"❌ Failed to send report for task '{task_name}'")
                return False
                
        except Exception as e:
            print(f"❌ Error executing task '{task_name}': {e}")
            return False
    
    def _generate_config_based_report(self, task: dict) -> str:
        """Generate report using saved configuration"""
        try:
            saved_config_name = task.get('saved_config_name')
            if not saved_config_name:
                return "❌ No saved configuration specified for this task"
            
            # Load the saved configuration
            config = self.config_manager.load_config(saved_config_name)
            if not config:
                return f"❌ Saved configuration '{saved_config_name}' not found"
            
            # Execute the configuration-based report
            return self._execute_config_based_report(config, saved_config_name)
            
        except Exception as e:
            return f"❌ Error generating config-based report: {str(e)}"
    
    def _execute_config_based_report(self, config: dict, config_name: str) -> str:
        """Execute report generation based on configuration parameters"""
        try:
            from excel_exporter import ExcelExporter
            import os
            
            print(f"📊 Generating report for configuration: {config_name}")
            print(f"🗄️ Database: {config.get('database', 'Unknown')}")
            print(f"👥 Groups: {len(config.get('groups', []))} selected" if config.get('groups') else "👥 Groups: All groups")
            
            # Create Excel file using the new function
            excel_exporter = ExcelExporter()
            
            # Export to Excel using saved configuration
            excel_path = excel_exporter.export_config_report_to_xlsx(config)
            
            if excel_path and os.path.exists(excel_path):
                print(f"✓ Excel file created: {excel_path}")
                
                # Format summary message for Telegram
                summary_message = self._format_config_summary_for_telegram(config, config_name, excel_path)
                
                return {
                    'message': summary_message,
                    'excel_file': excel_path,
                    'config_name': config_name,
                    'report_type': config.get('report_type', 'Configuration Report')
                }
            else:
                return f"❌ Failed to create Excel file for configuration: {config_name}"
            
        except Exception as e:
            return f"❌ Error executing config-based report: {str(e)}"
    
    def _format_config_summary_for_telegram(self, config: dict, config_name: str, excel_path: str) -> str:
        """Format configuration summary for Telegram"""
        try:
            import os
            
            # Get file size
            file_size = os.path.getsize(excel_path) if os.path.exists(excel_path) else 0
            file_size_mb = file_size / (1024 * 1024)
            
            # Format report
            report = f"""📊 <b>Configuration Report</b>
🔧 <b>Configuration:</b> {config_name}
🗄️ <b>Database:</b> {config.get('database', 'Unknown').upper()}
⏰ <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 <b>Configuration Details:</b>"""
            
            # Add groups information
            groups = config.get('groups', [])
            if groups:
                report += f"\n👥 Groups: {len(groups)} selected"
                if len(groups) <= 5:
                    report += f" ({', '.join(groups)})"
            else:
                report += "\n👥 Groups: All groups"
            
            # Add login range
            if config.get('min_login') is not None or config.get('max_login') is not None:
                min_login = config.get('min_login', 'N/A')
                max_login = config.get('max_login', 'N/A')
                report += f"\n🔢 Login Range: {min_login:,} - {max_login:,}"
            
            # Add date range
            if config.get('start_date') and config.get('end_date'):
                report += f"\n📅 Date Range: {config['start_date']} to {config['end_date']}"
            
            # Add profit range
            if config.get('min_profit') is not None or config.get('max_profit') is not None:
                min_profit = config.get('min_profit', 'N/A')
                max_profit = config.get('max_profit', 'N/A')
                if min_profit != 'N/A':
                    min_profit = f"${min_profit:,.2f}"
                if max_profit != 'N/A':
                    max_profit = f"${max_profit:,.2f}"
                report += f"\n💰 Profit Range: {min_profit} - {max_profit}"
            
            # Add file information
            report += f"""

📎 <b>Excel Report Generated:</b>
📁 File Size: {file_size_mb:.2f} MB
📊 Contains: Daily Report & Deals Categorizer data
🔍 Based on your saved configuration parameters

✅ Report ready for analysis!"""
            
            return report
            
        except Exception as e:
            return f"📊 Configuration Report: {config_name}\n❌ Error formatting summary: {str(e)}"
    
    def _format_monthly_summary_for_telegram(self, results: list, config: dict, config_name: str) -> str:
        """Format monthly summary results for Telegram"""
        if not results:
            return f"❌ No data found for configuration: {config_name}"
        
        # Calculate summary statistics
        total_logins = len(results)
        total_balance = sum(float(r.get('balance', 0)) for r in results)
        total_deposits = sum(float(r.get('monthly_deposits', 0)) for r in results)
        total_withdrawals = sum(float(r.get('monthly_withdrawals', 0)) for r in results)
        total_promotions = sum(float(r.get('monthly_promotions', 0)) for r in results)
        net_flow = total_deposits - total_withdrawals + total_promotions
        
        # Format report
        report = f"""📊 <b>Monthly Summary Report</b>
🔧 <b>Configuration:</b> {config_name}
🗄️ <b>Database:</b> {config.get('database', 'Unknown').upper()}
⏰ <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 <b>Summary Statistics:</b>
👥 Total Logins: {total_logins:,}
💰 Total Balance: ${total_balance:,.2f}
📈 Monthly Deposits: ${total_deposits:,.2f}
📉 Monthly Withdrawals: ${total_withdrawals:,.2f}
🎁 Monthly Promotions: ${total_promotions:,.2f}
📊 Net Monthly Flow: ${net_flow:,.2f}

🔝 <b>Top {min(10, len(results))} Accounts:</b>"""
        
        # Sort by balance and show top accounts
        sorted_results = sorted(results, key=lambda x: float(x.get('balance', 0)), reverse=True)
        for i, record in enumerate(sorted_results[:10], 1):
            login = record.get('login', 'N/A')
            balance = float(record.get('balance', 0))
            monthly_total = float(record.get('monthly_deposits', 0)) - float(record.get('monthly_withdrawals', 0)) + float(record.get('monthly_promotions', 0))
            report += f"\n{i}. Login {login}: ${balance:,.2f} (Monthly: ${monthly_total:+,.2f})"
        
        if len(results) > 10:
            report += f"\n... and {len(results) - 10} more accounts"
        
        return report
    
    def _format_balance_report_for_telegram(self, results: list, config: dict, config_name: str) -> str:
        """Format balance report results for Telegram"""
        if not results:
            return f"❌ No data found for configuration: {config_name}"
        
        total_logins = len(results)
        total_balance = sum(float(r.get('balance', 0)) for r in results)
        avg_balance = total_balance / total_logins if total_logins > 0 else 0
        
        report = f"""💰 <b>Balance Report</b>
🔧 <b>Configuration:</b> {config_name}
🗄️ <b>Database:</b> {config.get('database', 'Unknown').upper()}
⏰ <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 <b>Balance Summary:</b>
👥 Total Logins: {total_logins:,}
💰 Total Balance: ${total_balance:,.2f}
📊 Average Balance: ${avg_balance:,.2f}

🔝 <b>Top {min(10, len(results))} Balances:</b>"""
        
        sorted_results = sorted(results, key=lambda x: float(x.get('balance', 0)), reverse=True)
        for i, record in enumerate(sorted_results[:10], 1):
            login = record.get('login', 'N/A')
            balance = float(record.get('balance', 0))
            report += f"\n{i}. Login {login}: ${balance:,.2f}"
        
        if len(results) > 10:
            report += f"\n... and {len(results) - 10} more accounts"
        
        return report
    
    def _format_financial_report_for_telegram(self, results: list, config: dict, config_name: str) -> str:
        """Format financial report results for Telegram"""
        if not results:
            return f"❌ No data found for configuration: {config_name}"
        
        total_deposits = sum(float(r.get('monthly_deposits', 0)) for r in results)
        total_withdrawals = sum(float(r.get('monthly_withdrawals', 0)) for r in results)
        total_promotions = sum(float(r.get('monthly_promotions', 0)) for r in results)
        deposit_count = sum(int(r.get('deposit_count', 0)) for r in results)
        withdrawal_count = sum(int(r.get('withdrawal_count', 0)) for r in results)
        promotion_count = sum(int(r.get('promotion_count', 0)) for r in results)
        net_flow = total_deposits - total_withdrawals + total_promotions
        
        report = f"""💸 <b>Financial Report</b>
🔧 <b>Configuration:</b> {config_name}
🗄️ <b>Database:</b> {config.get('database', 'Unknown').upper()}
⏰ <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 <b>Financial Summary:</b>
💰 Monthly Deposits: ${total_deposits:,.2f} ({deposit_count:,} txns)
💸 Monthly Withdrawals: ${total_withdrawals:,.2f} ({withdrawal_count:,} txns)
🎁 Monthly Promotions: ${total_promotions:,.2f} ({promotion_count:,} txns)
📈 Net Monthly Flow: ${net_flow:,.2f}

🔝 <b>Top {min(10, len(results))} Financial Activity:</b>"""
        
        # Sort by total financial activity
        sorted_results = sorted(results, key=lambda x: float(x.get('monthly_deposits', 0)) + float(x.get('monthly_withdrawals', 0)) + float(x.get('monthly_promotions', 0)), reverse=True)
        for i, record in enumerate(sorted_results[:10], 1):
            login = record.get('login', 'N/A')
            deposits = float(record.get('monthly_deposits', 0))
            withdrawals = float(record.get('monthly_withdrawals', 0))
            promotions = float(record.get('monthly_promotions', 0))
            total_activity = deposits + withdrawals + promotions
            net_amount = deposits - withdrawals + promotions
            report += f"\n{i}. Login {login}: ${total_activity:,.2f} activity (Net: ${net_amount:+,.2f})"
        
        if len(results) > 10:
            report += f"\n... and {len(results) - 10} more accounts"
        
        return report
    
    def _format_transaction_report_for_telegram(self, results: list, config: dict, config_name: str) -> str:
        """Format transaction report results for Telegram"""
        if not results:
            return f"❌ No data found for configuration: {config_name}"
        
        total_transactions = sum(int(r.get('total_transactions', 0)) for r in results)
        total_volume = sum(float(r.get('total_volume', 0)) for r in results)
        avg_volume = total_volume / total_transactions if total_transactions > 0 else 0
        
        report = f"""📊 <b>Transaction Report</b>
🔧 <b>Configuration:</b> {config_name}
🗄️ <b>Database:</b> {config.get('database', 'Unknown').upper()}
⏰ <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 <b>Transaction Summary:</b>
📊 Total Transactions: {total_transactions:,}
💰 Total Volume: ${total_volume:,.2f}
📊 Average Volume: ${avg_volume:,.2f}

🔝 <b>Top {min(10, len(results))} Transaction Activity:</b>"""
        
        sorted_results = sorted(results, key=lambda x: int(x.get('total_transactions', 0)), reverse=True)
        for i, record in enumerate(sorted_results[:10], 1):
            login = record.get('login', 'N/A')
            transactions = int(record.get('total_transactions', 0))
            volume = float(record.get('total_volume', 0))
            avg_txn = volume / transactions if transactions > 0 else 0
            report += f"\n{i}. Login {login}: {transactions:,} txns (${volume:,.2f}, avg: ${avg_txn:,.2f})"
        
        if len(results) > 10:
            report += f"\n... and {len(results) - 10} more accounts"
        
        return report
    
    def start_scheduler(self):
        """Start the task scheduler in a background thread"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            print("⚠️ Scheduler is already running!")
            return False
        
        self.stop_scheduler = False
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print("🚀 Scheduler started successfully!")
        print("📅 Monitoring scheduled tasks...")
        return True
    
    def stop_scheduler_service(self):
        """Stop the task scheduler"""
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            print("⚠️ Scheduler is not running!")
            return False
        
        self.stop_scheduler = True
        print("🛑 Stopping scheduler...")
        return True
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        print("🔄 Scheduler thread started")
        
        while not self.stop_scheduler:
            try:
                now = datetime.now()
                
                # Check each active task
                for task_name, task in self.tasks.items():
                    if not task['active']:
                        continue
                    
                    next_run_str = task.get('next_run')
                    if not next_run_str:
                        continue
                    
                    try:
                        next_run = datetime.fromisoformat(next_run_str)
                        
                        # Check if it's time to run the task (within 1 minute window)
                        if now >= next_run and (now - next_run).total_seconds() < 60:
                            print(f"⏰ Executing scheduled task: {task_name}")
                            print(f"   📊 Report Type: {task['report_type']}")
                            print(f"   🗄️ Database: {task['database']}")
                            print(f"   💬 Chat ID: {task['chat_id']}")
                            print(f"   📅 Scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"   ⏱️ Actual execution: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            execution_success = self.execute_task(task_name)
                            
                            if execution_success:
                                print(f"✅ Successfully executed scheduled task: {task_name}")
                            else:
                                print(f"❌ Failed to execute scheduled task: {task_name}")
                                # Add error logging
                                error_msg = f"Scheduled execution failed at {now.strftime('%Y-%m-%d %H:%M:%S')}"
                                task['last_error'] = error_msg
                                self._save_tasks()
                    
                    except ValueError as e:
                        print(f"❌ Invalid next_run format for task {task_name}: {e}")
                
                # Sleep for 30 seconds before checking again
                time.sleep(30)
                
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(60)  # Wait longer on error
        
        print("🛑 Scheduler thread stopped")
    
    def get_scheduler_status(self):
        """Get current scheduler status"""
        running = (self.scheduler_thread and 
                  self.scheduler_thread.is_alive() and 
                  not self.stop_scheduler)
        active_tasks = sum(1 for task in self.tasks.values() if task['active'])
        
        return {
            'running': running,
            'total_tasks': len(self.tasks),
            'active_tasks': active_tasks,
            'thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }
    
    def get_task_statistics(self):
        """Get detailed task statistics for monitoring"""
        if not self.tasks:
            return {
                'total_tasks': 0,
                'active_tasks': 0,
                'inactive_tasks': 0,
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'success_rate': 0,
                'tasks_with_errors': 0,
                'next_execution': None,
                'last_execution': None
            }
        
        total_tasks = len(self.tasks)
        active_tasks = sum(1 for task in self.tasks.values() if task['active'])
        inactive_tasks = total_tasks - active_tasks
        
        total_executions = sum(task.get('run_count', 0) for task in self.tasks.values())
        successful_executions = sum(task.get('success_count', 0) for task in self.tasks.values())
        failed_executions = sum(task.get('error_count', 0) for task in self.tasks.values())
        
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        tasks_with_errors = sum(1 for task in self.tasks.values() if task.get('last_error'))
        
        # Find next execution
        next_execution = None
        next_executions = []
        for task in self.tasks.values():
            if task['active'] and task.get('next_run'):
                try:
                    next_run_time = datetime.fromisoformat(task['next_run'])
                    next_executions.append(next_run_time)
                except:
                    pass
        
        if next_executions:
            next_execution = min(next_executions)
        
        # Find last execution
        last_execution = None
        last_executions = []
        for task in self.tasks.values():
            if task.get('last_run'):
                try:
                    last_run_time = datetime.fromisoformat(task['last_run'])
                    last_executions.append(last_run_time)
                except:
                    pass
        
        if last_executions:
            last_execution = max(last_executions)
        
        return {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'inactive_tasks': inactive_tasks,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': success_rate,
            'tasks_with_errors': tasks_with_errors,
            'next_execution': next_execution,
            'last_execution': last_execution
        }
    
    def get_task_health_report(self):
        """Generate a health report for all tasks"""
        health_report = []
        now = datetime.now()
        
        for task_name, task in self.tasks.items():
            health_status = "🟢 Healthy"
            issues = []
            
            # Check if task is active
            if not task['active']:
                health_status = "🟡 Inactive"
                issues.append("Task is disabled")
            
            # Check for recent errors
            if task.get('last_error'):
                health_status = "🔴 Unhealthy"
                issues.append(f"Last error: {task['last_error']}")
            
            # Check success rate
            total_runs = task.get('run_count', 0)
            success_runs = task.get('success_count', 0)
            if total_runs > 0:
                success_rate = (success_runs / total_runs) * 100
                if success_rate < 90:
                    health_status = "🟡 Warning" if health_status == "🟢 Healthy" else health_status
                    issues.append(f"Low success rate: {success_rate:.1f}%")
            
            # Check if next run is overdue (for active tasks)
            if task['active'] and task.get('next_run'):
                try:
                    next_run = datetime.fromisoformat(task['next_run'])
                    if next_run < now:
                        time_overdue = now - next_run
                        if time_overdue.total_seconds() > 300:  # 5 minutes
                            health_status = "🔴 Unhealthy"
                            issues.append(f"Overdue by {time_overdue}")
                except:
                    pass
            
            health_report.append({
                'task_name': task_name,
                'health_status': health_status,
                'issues': issues,
                'total_runs': total_runs,
                'success_rate': (success_runs / total_runs * 100) if total_runs > 0 else 0,
                'last_run': task.get('last_run'),
                'next_run': task.get('next_run')
            })
        
        return health_report

    def _prepare_daily_report_excel_data(self, results: list, config: dict, config_name: str) -> dict:
        """Prepare daily report data for Excel export"""
        if not results:
            return {'sheets': {}, 'summary': 'No data available'}
        
        # Calculate summary statistics
        total_logins = len(results)
        total_balance = sum(float(r.get('balance', 0)) for r in results)
        total_deposits = sum(float(r.get('monthly_deposits', 0)) for r in results)
        total_withdrawals = sum(float(r.get('monthly_withdrawals', 0)) for r in results)
        total_promotions = sum(float(r.get('monthly_promotions', 0)) for r in results)
        net_flow = total_deposits - total_withdrawals + total_promotions
        
        # Prepare main data sheet
        main_data = []
        for record in results:
            main_data.append({
                'Login': record.get('login', 'N/A'),
                'Balance': float(record.get('balance', 0)),
                'Monthly Deposits': float(record.get('monthly_deposits', 0)),
                'Monthly Withdrawals': float(record.get('monthly_withdrawals', 0)),
                'Monthly Promotions': float(record.get('monthly_promotions', 0)),
                'Net Monthly Flow': float(record.get('monthly_deposits', 0)) - float(record.get('monthly_withdrawals', 0)) + float(record.get('monthly_promotions', 0)),
                'Deposit Count': int(record.get('deposit_count', 0)),
                'Withdrawal Count': int(record.get('withdrawal_count', 0)),
                'Promotion Count': int(record.get('promotion_count', 0)),
                'Last Activity': record.get('last_activity', 'N/A'),
                'Registration Date': record.get('registration_date', 'N/A')
            })
        
        # Prepare summary sheet
        summary_data = [
            {'Metric': 'Total Logins', 'Value': total_logins},
            {'Metric': 'Total Balance', 'Value': total_balance},
            {'Metric': 'Total Monthly Deposits', 'Value': total_deposits},
            {'Metric': 'Total Monthly Withdrawals', 'Value': total_withdrawals},
            {'Metric': 'Total Monthly Promotions', 'Value': total_promotions},
            {'Metric': 'Net Monthly Flow', 'Value': net_flow},
            {'Metric': 'Average Balance', 'Value': total_balance / total_logins if total_logins > 0 else 0}
        ]
        
        return {
            'sheets': {
                'Daily Report Data': main_data,
                'Summary': summary_data
            },
            'summary': f"Daily Report: {total_logins} accounts, ${total_balance:,.2f} total balance, ${net_flow:,.2f} net flow",
            'config_info': {
                'name': config_name,
                'database': config.get('database', 'Unknown'),
                'groups': len(config.get('groups', [])),
                'report_type': 'Daily Report'
            }
        }
    
    def _prepare_deals_excel_data(self, results: list, config: dict, config_name: str) -> dict:
        """Prepare deals categorizer data for Excel export"""
        if not results:
            return {'sheets': {}, 'summary': 'No data available'}
        
        # Categorize deals
        deposits = [r for r in results if r.get('deal_type') == 'Deposit']
        withdrawals = [r for r in results if r.get('deal_type') == 'Withdrawal']
        promotions = [r for r in results if r.get('deal_type') == 'Promotion']
        
        # Calculate totals
        total_deposit_amount = sum(float(d.get('amount', 0)) for d in deposits)
        total_withdrawal_amount = sum(float(w.get('amount', 0)) for w in withdrawals)
        total_promotion_amount = sum(float(p.get('amount', 0)) for p in promotions)
        
        # Prepare deposits sheet
        deposits_data = []
        for deal in deposits:
            deposits_data.append({
                'Login': deal.get('login', 'N/A'),
                'Amount': float(deal.get('amount', 0)),
                'Date': deal.get('deal_time', 'N/A'),
                'Comment': deal.get('comment', 'N/A'),
                'Ticket': deal.get('ticket', 'N/A')
            })
        
        # Prepare withdrawals sheet
        withdrawals_data = []
        for deal in withdrawals:
            withdrawals_data.append({
                'Login': deal.get('login', 'N/A'),
                'Amount': abs(float(deal.get('amount', 0))),
                'Date': deal.get('deal_time', 'N/A'),
                'Comment': deal.get('comment', 'N/A'),
                'Ticket': deal.get('ticket', 'N/A')
            })
        
        # Prepare promotions sheet
        promotions_data = []
        for deal in promotions:
            promotions_data.append({
                'Login': deal.get('login', 'N/A'),
                'Amount': float(deal.get('amount', 0)),
                'Date': deal.get('deal_time', 'N/A'),
                'Comment': deal.get('comment', 'N/A'),
                'Ticket': deal.get('ticket', 'N/A')
            })
        
        # Prepare summary sheet
        summary_data = [
            {'Category': 'Deposits', 'Count': len(deposits), 'Total Amount': total_deposit_amount},
            {'Category': 'Withdrawals', 'Count': len(withdrawals), 'Total Amount': total_withdrawal_amount},
            {'Category': 'Promotions', 'Count': len(promotions), 'Total Amount': total_promotion_amount},
            {'Category': 'Net Flow', 'Count': len(results), 'Total Amount': total_deposit_amount - total_withdrawal_amount + total_promotion_amount}
        ]
        
        return {
            'sheets': {
                'Deposits': deposits_data,
                'Withdrawals': withdrawals_data,
                'Promotions': promotions_data,
                'Summary': summary_data
            },
            'summary': f"Deals Report: {len(deposits)} deposits (${total_deposit_amount:,.2f}), {len(withdrawals)} withdrawals (${total_withdrawal_amount:,.2f}), {len(promotions)} promotions (${total_promotion_amount:,.2f})",
            'config_info': {
                'name': config_name,
                'database': config.get('database', 'Unknown'),
                'groups': len(config.get('groups', [])),
                'report_type': 'Deals Categorizer'
            }
        }
    
    def _prepare_monthly_summary_excel_data(self, results: list, config: dict, config_name: str) -> dict:
        """Prepare monthly summary data for Excel export"""
        if not results:
            return {'sheets': {}, 'summary': 'No data available'}
        
        # Calculate summary statistics
        total_logins = len(results)
        total_balance = sum(float(r.get('balance', 0)) for r in results)
        total_deposits = sum(float(r.get('monthly_deposits', 0)) for r in results)
        total_withdrawals = sum(float(r.get('monthly_withdrawals', 0)) for r in results)
        total_promotions = sum(float(r.get('monthly_promotions', 0)) for r in results)
        net_flow = total_deposits - total_withdrawals + total_promotions
        
        # Prepare main data sheet
        main_data = []
        for record in results:
            main_data.append({
                'Login': record.get('login', 'N/A'),
                'Balance': float(record.get('balance', 0)),
                'Monthly Deposits': float(record.get('monthly_deposits', 0)),
                'Monthly Withdrawals': float(record.get('monthly_withdrawals', 0)),
                'Monthly Promotions': float(record.get('monthly_promotions', 0)),
                'Net Monthly Flow': float(record.get('monthly_deposits', 0)) - float(record.get('monthly_withdrawals', 0)) + float(record.get('monthly_promotions', 0)),
                'Group': record.get('group', 'N/A'),
                'Country': record.get('country', 'N/A'),
                'Registration Date': record.get('registration', 'N/A'),
                'Last Activity': record.get('last_activity', 'N/A')
            })
        
        # Prepare summary sheet
        summary_data = [
            {'Metric': 'Total Accounts', 'Value': total_logins},
            {'Metric': 'Total Balance', 'Value': total_balance},
            {'Metric': 'Monthly Deposits', 'Value': total_deposits},
            {'Metric': 'Monthly Withdrawals', 'Value': total_withdrawals},
            {'Metric': 'Monthly Promotions', 'Value': total_promotions},
            {'Metric': 'Net Monthly Flow', 'Value': net_flow},
            {'Metric': 'Average Balance per Account', 'Value': total_balance / total_logins if total_logins > 0 else 0}
        ]
        
        return {
            'sheets': {
                'Monthly Summary': main_data,
                'Statistics': summary_data
            },
            'summary': f"Monthly Summary: {total_logins} accounts, ${net_flow:,.2f} net flow",
            'config_info': {
                'name': config_name,
                'database': config.get('database', 'Unknown'),
                'groups': len(config.get('groups', [])),
                'report_type': 'Monthly Summary'
            }
        }
    
    def _prepare_balance_excel_data(self, results: list, config: dict, config_name: str) -> dict:
        """Prepare balance report data for Excel export"""
        if not results:
            return {'sheets': {}, 'summary': 'No data available'}
        
        total_logins = len(results)
        total_balance = sum(float(r.get('balance', 0)) for r in results)
        avg_balance = total_balance / total_logins if total_logins > 0 else 0
        
        # Prepare main data sheet
        main_data = []
        for record in results:
            main_data.append({
                'Login': record.get('login', 'N/A'),
                'Balance': float(record.get('balance', 0)),
                'Group': record.get('group', 'N/A'),
                'Country': record.get('country', 'N/A'),
                'Registration': record.get('registration', 'N/A'),
                'Last Activity': record.get('last_activity', 'N/A')
            })
        
        return {
            'sheets': {
                'Balance Report': main_data
            },
            'summary': f"Balance Report: {total_logins} accounts, ${total_balance:,.2f} total balance",
            'config_info': {
                'name': config_name,
                'database': config.get('database', 'Unknown'),
                'groups': len(config.get('groups', [])),
                'report_type': 'Balance Report'
            }
        }
    
    def _prepare_financial_excel_data(self, results: list, config: dict, config_name: str) -> dict:
        """Prepare financial report data for Excel export"""
        if not results:
            return {'sheets': {}, 'summary': 'No data available'}
        
        total_deposits = sum(float(r.get('monthly_deposits', 0)) for r in results)
        total_withdrawals = sum(float(r.get('monthly_withdrawals', 0)) for r in results)
        total_promotions = sum(float(r.get('monthly_promotions', 0)) for r in results)
        net_flow = total_deposits - total_withdrawals + total_promotions
        
        # Prepare main data sheet
        main_data = []
        for record in results:
            main_data.append({
                'Login': record.get('login', 'N/A'),
                'Monthly Deposits': float(record.get('monthly_deposits', 0)),
                'Monthly Withdrawals': float(record.get('monthly_withdrawals', 0)),
                'Monthly Promotions': float(record.get('monthly_promotions', 0)),
                'Net Flow': float(record.get('monthly_deposits', 0)) - float(record.get('monthly_withdrawals', 0)) + float(record.get('monthly_promotions', 0)),
                'Deposit Count': int(record.get('deposit_count', 0)),
                'Withdrawal Count': int(record.get('withdrawal_count', 0)),
                'Promotion Count': int(record.get('promotion_count', 0))
            })
        
        return {
            'sheets': {
                'Financial Report': main_data
            },
            'summary': f"Financial Report: ${net_flow:,.2f} net flow, {len(results)} accounts",
            'config_info': {
                'name': config_name,
                'database': config.get('database', 'Unknown'),
                'groups': len(config.get('groups', [])),
                'report_type': 'Financial Report'
            }
        }
    
    def _prepare_transaction_excel_data(self, results: list, config: dict, config_name: str) -> dict:
        """Prepare transaction report data for Excel export"""
        if not results:
            return {'sheets': {}, 'summary': 'No data available'}
        
        total_transactions = sum(int(r.get('total_transactions', 0)) for r in results)
        total_volume = sum(float(r.get('total_volume', 0)) for r in results)
        
        # Prepare main data sheet
        main_data = []
        for record in results:
            main_data.append({
                'Login': record.get('login', 'N/A'),
                'Total Transactions': int(record.get('total_transactions', 0)),
                'Total Volume': float(record.get('total_volume', 0)),
                'Average Transaction': float(record.get('total_volume', 0)) / max(int(record.get('total_transactions', 1)), 1),
                'Group': record.get('group', 'N/A'),
                'Last Transaction Date': record.get('last_transaction_date', 'N/A')
            })
        
        return {
            'sheets': {
                'Transaction Report': main_data
            },
            'summary': f"Transaction Report: {total_transactions:,} transactions, ${total_volume:,.2f} volume",
            'config_info': {
                'name': config_name,
                'database': config.get('database', 'Unknown'),
                'groups': len(config.get('groups', [])),
                'report_type': 'Transaction Report'
            }
        }
    
    def _format_excel_summary_for_telegram(self, excel_data: dict, config: dict, config_name: str) -> str:
        """Format Excel summary message for Telegram"""
        config_info = excel_data.get('config_info', {})
        summary = excel_data.get('summary', 'Report generated')
        
        message = f"""📊 <b>Scheduled Report Generated</b>
🔧 <b>Configuration:</b> {config_name}
🗄️ <b>Database:</b> {config_info.get('database', 'Unknown').upper()}
📋 <b>Report Type:</b> {config_info.get('report_type', 'Unknown')}
👥 <b>Groups:</b> {config_info.get('groups', 0)} selected
⏰ <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 <b>Summary:</b>
{summary}

📎 <b>Excel file attached with detailed data</b>

🔢 <b>Configuration Details:</b>
• Login Range: {config.get('min_login', 'N/A')} - {config.get('max_login', 'N/A')}
• Record Limit: {config.get('limit', 'No limit')}
• Total Sheets: {len(excel_data.get('sheets', {}))}"""

        return message

def main():
    """Main function to handle command line interface"""
    scheduler = ScheduledTaskManager()
    
    while True:
        print("\n🕐 Scheduled Task Manager")
        print("=" * 50)
        
        # Show scheduler status
        status = scheduler.get_scheduler_status()
        scheduler_status = "🟢 Running" if status['running'] else "🔴 Stopped"
        print(f"Scheduler Status: {scheduler_status}")
        print(f"Tasks: {status['active_tasks']}/{status['total_tasks']} active")
        
        choices = [
            "Create New Task",
            "List Tasks",
            "Execute Task",
            "Toggle Task (Enable/Disable)",
            "Delete Task",
            "Start Scheduler" if not status['running'] else "Stop Scheduler",
            "Setup Telegram Integration",
            "Exit"
        ]
        
        questions = [
            inquirer.List('action',
                         message="Select an action",
                         choices=choices)
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if not answers:
                break
            
            action = answers['action']
            
            if action == "Create New Task":
                scheduler.create_task()
            
            elif action == "List Tasks":
                scheduler.list_tasks()
            
            elif action == "Execute Task":
                if scheduler.tasks:
                    task_choices = list(scheduler.tasks.keys())
                    task_questions = [
                        inquirer.List('task_name',
                                     message="Select task to execute",
                                     choices=task_choices)
                    ]
                    task_answers = inquirer.prompt(task_questions)
                    if task_answers:
                        scheduler.execute_task(task_answers['task_name'])
                else:
                    print("No tasks available.")
            
            elif action == "Toggle Task (Enable/Disable)":
                scheduler.toggle_task()
            
            elif action == "Delete Task":
                scheduler.delete_task()
            
            elif action == "Start Scheduler":
                scheduler.start_scheduler()
            
            elif action == "Stop Scheduler":
                scheduler.stop_scheduler_service()
            
            elif action == "Setup Telegram Integration":
                scheduler.telegram_integration.setup_telegram_integration()
            
            elif action == "Exit":
                if status['running']:
                    print("🛑 Stopping scheduler before exit...")
                    scheduler.stop_scheduler_service()
                    time.sleep(2)
                print("👋 Goodbye!")
                break
            
            # Wait for user input before continuing
            if action != "Exit":
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            input("\nPress Enter to continue...")