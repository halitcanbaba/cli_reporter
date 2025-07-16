#!/usr/bin/env python3
"""
Telegram Integration
Handles all Telegram bot functionality for sending reports
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional
import inquirer
from telegram import Bot
from telegram.error import TelegramError


class TelegramIntegration:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.task_creator")
        self.telegram_config_file = os.path.join(self.config_dir, "telegram_config.json")
        self.telegram_bot = None
        self.telegram_chat_id = None
        self.chat_configs = {}  # Multiple chat configurations
        self._ensure_config_dir()
        self._load_telegram_config()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
    
    def _load_telegram_config(self):
        """Load Telegram configuration from file"""
        try:
            if os.path.exists(self.telegram_config_file):
                with open(self.telegram_config_file, 'r') as f:
                    config = json.load(f)
                    bot_token = config.get('bot_token')
                    self.telegram_chat_id = config.get('chat_id')  # Default chat ID
                    self.chat_configs = config.get('chat_configs', {})  # Multiple chat configs
                    
                    if bot_token:
                        self.telegram_bot = Bot(token=bot_token)
                        return True
            return False
        except Exception as e:
            print(f"❌ Error loading Telegram configuration: {e}")
            return False
    
    def _save_telegram_config(self, bot_token: str, chat_id: str):
        """Save Telegram configuration to file"""
        try:
            # Load existing config to preserve chat_configs
            existing_config = {}
            if os.path.exists(self.telegram_config_file):
                with open(self.telegram_config_file, 'r') as f:
                    existing_config = json.load(f)
            
            config = {
                'bot_token': bot_token,
                'chat_id': chat_id,
                'chat_configs': existing_config.get('chat_configs', {}),
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.telegram_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Update instance variables
            self.telegram_bot = Bot(token=bot_token)
            self.telegram_chat_id = chat_id
            self.chat_configs = config['chat_configs']
            
            print("✓ Telegram configuration saved successfully")
            return True
        except Exception as e:
            print(f"❌ Error saving Telegram configuration: {e}")
            return False
    
    def setup_telegram_integration(self):
        """Setup Telegram bot integration"""
        print("\n🤖 Telegram Bot Integration Setup")
        print("=" * 50)
        print("To use Telegram integration, you need:")
        print("1. Create a Telegram bot via @BotFather")
        print("2. Get your bot token")
        print("3. Get your chat ID (or group chat ID)")
        print("4. Add the bot to your group (if using group)")
        print()
        
        questions = [
            inquirer.Text('bot_token', message="Enter your Telegram bot token"),
            inquirer.Text('chat_id', message="Enter your chat ID (or group chat ID)")
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if answers:
                bot_token = answers['bot_token'].strip()
                chat_id = answers['chat_id'].strip()
                
                if bot_token and chat_id:
                    # Test the bot configuration
                    test_bot = Bot(token=bot_token)
                    
                    # Try to send a test message
                    print("\n🔍 Testing Telegram bot configuration...")
                    try:
                        # Send test message
                        message = "🤖 Task Creator Bot is now connected!\n\nThis is a test message to verify the integration is working."
                        
                        # Use async function to test
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(test_bot.send_message(chat_id=chat_id, text=message))
                            print("✓ Test message sent successfully!")
                        finally:
                            loop.close()
                        
                        # Save configuration
                        if self._save_telegram_config(bot_token, chat_id):
                            print("✓ Telegram integration setup complete!")
                            return True
                        else:
                            print("❌ Failed to save Telegram configuration")
                            return False
                            
                    except TelegramError as e:
                        print(f"❌ Telegram error: {e}")
                        print("Please check your bot token and chat ID")
                        return False
                        
                else:
                    print("❌ Bot token and chat ID are required")
                    return False
            else:
                print("❌ Setup cancelled")
                return False
                
        except KeyboardInterrupt:
            print("\n❌ Setup cancelled by user")
            return False
        except Exception as e:
            print(f"❌ Error during Telegram setup: {e}")
            return False
    
    def get_telegram_status(self):
        """Get current Telegram integration status"""
        if self.telegram_bot and self.telegram_chat_id:
            return {
                'configured': True,
                'chat_id': self.telegram_chat_id,
                'status': 'Active'
            }
        else:
            return {
                'configured': False,
                'chat_id': None,
                'status': 'Not configured'
            }
    
    def send_telegram_message(self, message: str, file_path: str = None, chat_id: str = None):
        """Send message and optionally file to Telegram"""
        if not self.telegram_bot:
            print("❌ Telegram bot not configured")
            return False
        
        # Use provided chat_id or default
        target_chat_id = chat_id or self.telegram_chat_id
        
        if not target_chat_id:
            print("❌ No chat ID available")
            return False
        
        try:
            # Use a completely separate thread with its own event loop
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def telegram_thread():
                try:
                    # Create completely new event loop for this thread
                    import asyncio
                    
                    # Check if there's already an event loop running
                    try:
                        loop = asyncio.get_running_loop()
                        print("[>>] Using existing event loop in thread")
                    except RuntimeError:
                        # No loop running, create a new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        print("[>>] Created new event loop in thread")
                    
                    try:
                        result = loop.run_until_complete(
                            self._send_message_and_file_sync(message, file_path, target_chat_id)
                        )
                        result_queue.put(('success', result))
                    except Exception as e:
                        print(f"❌ Loop execution error: {e}")
                        result_queue.put(('error', str(e)))
                    finally:
                        # Only close the loop if we created it
                        if loop.is_running():
                            try:
                                loop.close()
                            except RuntimeError:
                                pass  # Loop may already be closed
                        
                except Exception as e:
                    print(f"❌ Thread setup error: {e}")
                    result_queue.put(('error', str(e)))
            
            # Start thread and wait for result
            thread = threading.Thread(target=telegram_thread)
            thread.daemon = True  # Make thread daemon so it doesn't block shutdown
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            # Get result
            try:
                result_type, result_value = result_queue.get_nowait()
                if result_type == 'success':
                    return result_value
                else:
                    print(f"❌ Telegram thread error: {result_value}")
                    return False
            except queue.Empty:
                print("❌ Telegram operation timed out")
                return False
            
        except Exception as e:
            print(f"❌ Error setting up Telegram thread: {e}")
            return False
            print(f"❌ Error setting up Telegram thread: {e}")
            return False
    
    async def _send_message_and_file_sync(self, message: str, file_path: str = None, chat_id: str = None):
        """Async helper to send message and file in isolated event loop"""
        try:
            target_chat_id = chat_id or self.telegram_chat_id
            
            print(f"📤 Sending message to chat {target_chat_id}...")
            
            # Send message
            await self.telegram_bot.send_message(
                chat_id=target_chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            print("✅ Message sent successfully")
            
            # Send file if provided
            if file_path and os.path.exists(file_path):
                print(f"📎 Sending file: {file_path}")
                try:
                    with open(file_path, 'rb') as file:
                        filename = os.path.basename(file_path)
                        await self.telegram_bot.send_document(
                            chat_id=target_chat_id,
                            document=file,
                            filename=filename,
                            caption=f"📊 Financial Report: {filename}"
                        )
                    print("✅ File sent successfully")
                except Exception as e:
                    print(f"❌ Error sending file: {e}")
                    # Still return True if message was sent, file is optional
            
            return True
            
        except TelegramError as e:
            print(f"❌ Telegram API error: {e}")
            return False
        except Exception as e:
            print(f"❌ Async error: {e}")
            return False
    
    def test_telegram_connection(self):
        """Test Telegram connection"""
        if not self.telegram_bot or not self.telegram_chat_id:
            print("❌ Telegram bot not configured")
            return False
        
        try:
            message = f"🔍 <b>Telegram Connection Test</b>\n\n" \
                     f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                     f"🤖 Bot Status: Active\n" \
                     f"💬 Chat ID: {self.telegram_chat_id}\n\n" \
                     f"✅ Connection is working properly!"
            
            return asyncio.run(self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            ))
            
        except TelegramError as e:
            print(f"❌ Telegram error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error testing connection: {e}")
            return False
            
        except TelegramError as e:
            print(f"❌ Telegram error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error testing connection: {e}")
            return False
    
    def manage_telegram_settings(self):
        """Manage Telegram integration settings"""
        while True:
            status = self.get_telegram_status()
            
            print("\n🤖 Telegram Integration Management")
            print("=" * 50)
            print(f"Status: {status['status']}")
            if status['configured']:
                print(f"Chat ID: {status['chat_id']}")
            print()
            
            options = []
            if status['configured']:
                options.extend([
                    "Test Connection",
                    "Send Test Message",
                    "Reconfigure Bot",
                    "Remove Configuration"
                ])
            else:
                options.append("Setup Telegram Integration")
            
            options.append("← Back to Main Menu")
            
            questions = [
                inquirer.List('action',
                             message="Select action",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or answers['action'] == "← Back to Main Menu":
                break
            
            action = answers['action']
            
            if action == "Setup Telegram Integration":
                self.setup_telegram_integration()
            elif action == "Test Connection":
                self.test_telegram_connection()
            elif action == "Send Test Message":
                self._send_custom_test_message()
            elif action == "Reconfigure Bot":
                self.setup_telegram_integration()
            elif action == "Remove Configuration":
                self._remove_telegram_config()
            
            input("\nPress Enter to continue...")
    
    def _send_custom_test_message(self):
        """Send a custom test message"""
        questions = [
            inquirer.Text('message',
                         message="Enter test message to send",
                         default="🧪 This is a custom test message from Task Creator!")
        ]
        
        answers = inquirer.prompt(questions)
        if answers and answers['message']:
            message = answers['message'].strip()
            if self.send_telegram_message(message):
                print("✓ Custom test message sent successfully!")
            else:
                print("❌ Failed to send test message")
    
    def _remove_telegram_config(self):
        """Remove Telegram configuration"""
        questions = [
            inquirer.Confirm('confirm',
                           message="Are you sure you want to remove Telegram configuration?",
                           default=False)
        ]
        
        answers = inquirer.prompt(questions)
        if answers and answers['confirm']:
            try:
                if os.path.exists(self.telegram_config_file):
                    os.remove(self.telegram_config_file)
                
                self.telegram_bot = None
                self.telegram_chat_id = None
                
                print("✓ Telegram configuration removed successfully")
                return True
            except Exception as e:
                print(f"❌ Error removing Telegram configuration: {e}")
                return False
    
    def format_report_message(self, config: dict, results: list) -> str:
        """Format a report message for Telegram"""
        successful_results = [r for r in results if r.get('success', False)]
        
        message = f"📊 <b>Financial Analysis Report</b>\n\n"
        message += f"🗄️ <b>Database:</b> {config.get('database', 'N/A')}\n"
        message += f"📋 <b>Report Type:</b> {config.get('report_type', 'N/A').replace('_', ' ').title()}\n"
        
        if config.get('groups'):
            if len(config['groups']) <= 3:
                message += f"👥 <b>Groups:</b> {', '.join(config['groups'])}\n"
            else:
                message += f"👥 <b>Groups:</b> {len(config['groups'])} groups selected\n"
        else:
            message += f"👥 <b>Groups:</b> All Groups\n"
        
        message += f"🔢 <b>Login Range:</b> {config.get('min_login', 'N/A'):,} - {config.get('max_login', 'N/A'):,}\n"
        
        if config.get('removed_logins'):
            message += f"🚫 <b>Excluded Logins:</b> {len(config['removed_logins'])}\n"
        
        message += f"📅 <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if successful_results:
            message += f"✅ <b>Execution Status:</b> {len(successful_results)} command(s) completed successfully\n"
        else:
            message += f"❌ <b>Execution Status:</b> No successful results\n"
        
        return message
    
    def add_chat_config(self, name: str, chat_id: str, description: str = ""):
        """Add a new chat configuration"""
        try:
            # Load current config
            config = {}
            if os.path.exists(self.telegram_config_file):
                with open(self.telegram_config_file, 'r') as f:
                    config = json.load(f)
            
            # Update chat configs
            if 'chat_configs' not in config:
                config['chat_configs'] = {}
            
            config['chat_configs'][name] = {
                'chat_id': chat_id,
                'description': description,
                'added_at': datetime.now().isoformat()
            }
            
            # Save updated config
            with open(self.telegram_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Update instance
            self.chat_configs = config['chat_configs']
            
            print(f"✓ Chat configuration '{name}' added successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error adding chat configuration: {e}")
            return False
    
    def get_chat_configs(self):
        """Get all chat configurations"""
        return self.chat_configs
    
    def get_chat_id_by_name(self, name: str):
        """Get chat ID by configuration name"""
        if name in self.chat_configs:
            return self.chat_configs[name]['chat_id']
        return None
    
    def list_chat_configs(self):
        """List all chat configurations"""
        if not self.chat_configs:
            print("📭 No chat configurations found")
            return []
        
        print(f"\n📱 Telegram Chat Configurations ({len(self.chat_configs)}):")
        print("=" * 60)
        
        chat_data = []
        for name, config in self.chat_configs.items():
            description = config.get('description', 'No description')
            chat_id = config.get('chat_id', 'Unknown')
            added_at = config.get('added_at', 'Unknown')
            
            if added_at != 'Unknown':
                try:
                    added_dt = datetime.fromisoformat(added_at)
                    added_at = added_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            chat_data.append([name, chat_id, description, added_at])
        
        from tabulate import tabulate
        headers = ['Name', 'Chat ID', 'Description', 'Added At']
        print(tabulate(chat_data, headers=headers, tablefmt='grid'))
        
        return list(self.chat_configs.keys())
    
    def manage_chat_configurations(self):
        """Manage multiple chat configurations"""
        while True:
            print("\n📱 Chat Configuration Management")
            print("=" * 50)
            
            # Show current chat configs
            chat_names = self.list_chat_configs()
            
            options = [
                "➕ Add New Chat Configuration",
                "🗑️ Remove Chat Configuration",
                "🧪 Test Chat Configuration",
                "← Back to Telegram Menu"
            ]
            
            questions = [
                inquirer.List('action',
                             message="Select action",
                             choices=options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or "Back to Telegram Menu" in answers['action']:
                break
            
            action = answers['action']
            
            if "Add New Chat" in action:
                self._add_chat_config_interactive()
            elif "Remove Chat" in action:
                if chat_names:
                    self._remove_chat_config_interactive(chat_names)
                else:
                    print("❌ No chat configurations to remove")
            elif "Test Chat" in action:
                if chat_names:
                    self._test_chat_config_interactive(chat_names)
                else:
                    print("❌ No chat configurations to test")
            
            if action != "← Back to Telegram Menu":
                input("\nPress Enter to continue...")
    
    def _add_chat_config_interactive(self):
        """Interactive chat configuration addition"""
        print("\n➕ Add New Chat Configuration")
        print("-" * 30)
        
        questions = [
            inquirer.Text('name',
                         message="Enter a name for this chat configuration",
                         validate=lambda _, x: len(x.strip()) > 0),
            inquirer.Text('chat_id',
                         message="Enter the chat ID",
                         validate=lambda _, x: x.strip().lstrip('-').isdigit()),
            inquirer.Text('description',
                         message="Enter a description (optional)",
                         default="")
        ]
        
        answers = inquirer.prompt(questions)
        if answers:
            name = answers['name'].strip()
            chat_id = answers['chat_id'].strip()
            description = answers['description'].strip()
            
            # Check if name already exists
            if name in self.chat_configs:
                print(f"❌ Chat configuration '{name}' already exists")
                return False
            
            # Test the chat ID if bot is configured
            if self.telegram_bot:
                print(f"\n🔍 Testing chat ID {chat_id}...")
                try:
                    test_message = f"🧪 Test message for chat configuration '{name}'"
                    success = asyncio.run(self.telegram_bot.send_message(
                        chat_id=chat_id,
                        text=test_message
                    ))
                    if success:
                        print("✓ Test message sent successfully!")
                    else:
                        print("❌ Failed to send test message")
                        questions = [
                            inquirer.Confirm('continue',
                                           message="Continue adding this configuration anyway?",
                                           default=False)
                        ]
                        confirm = inquirer.prompt(questions)
                        if not confirm or not confirm['continue']:
                            return False
                except Exception as e:
                    print(f"❌ Error testing chat ID: {e}")
                    return False
            
            # Add the configuration
            return self.add_chat_config(name, chat_id, description)
        
        return False
    
    def _remove_chat_config_interactive(self, chat_names):
        """Interactive chat configuration removal"""
        questions = [
            inquirer.List('name',
                         message="Select chat configuration to remove",
                         choices=chat_names + ["← Cancel"])
        ]
        
        answers = inquirer.prompt(questions)
        if answers and answers['name'] != "← Cancel":
            name = answers['name']
            
            questions = [
                inquirer.Confirm('confirm',
                               message=f"Are you sure you want to remove '{name}'?",
                               default=False)
            ]
            
            confirm = inquirer.prompt(questions)
            if confirm and confirm['confirm']:
                try:
                    # Load current config
                    config = {}
                    if os.path.exists(self.telegram_config_file):
                        with open(self.telegram_config_file, 'r') as f:
                            config = json.load(f)
                    
                    # Remove from chat configs
                    if 'chat_configs' in config and name in config['chat_configs']:
                        del config['chat_configs'][name]
                        
                        # Save updated config
                        with open(self.telegram_config_file, 'w') as f:
                            json.dump(config, f, indent=2)
                        
                        # Update instance
                        self.chat_configs = config['chat_configs']
                        
                        print(f"✓ Chat configuration '{name}' removed successfully")
                        return True
                    else:
                        print(f"❌ Chat configuration '{name}' not found")
                        
                except Exception as e:
                    print(f"❌ Error removing chat configuration: {e}")
        
        return False
    
    def _test_chat_config_interactive(self, chat_names):
        """Interactive chat configuration testing"""
        questions = [
            inquirer.List('name',
                         message="Select chat configuration to test",
                         choices=chat_names + ["← Cancel"])
        ]
        
        answers = inquirer.prompt(questions)
        if answers and answers['name'] != "← Cancel":
            name = answers['name']
            chat_id = self.get_chat_id_by_name(name)
            
            if chat_id and self.telegram_bot:
                try:
                    message = f"🧪 <b>Test Message</b>\n\n" \
                             f"📱 Chat Config: {name}\n" \
                             f"💬 Chat ID: {chat_id}\n" \
                             f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" \
                             f"✅ This chat configuration is working properly!"
                    
                    success = asyncio.run(self.telegram_bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='HTML'
                    ))
                    
                    if success:
                        print(f"✓ Test message sent to '{name}' successfully!")
                    else:
                        print(f"❌ Failed to send test message to '{name}'")
                        
                except Exception as e:
                    print(f"❌ Error testing '{name}': {e}")
            else:
                print(f"❌ Chat configuration '{name}' not found or bot not configured")
    
    def select_chat_for_report(self):
        """Interactive chat selection for report sending"""
        if not self.chat_configs and not self.telegram_chat_id:
            print("❌ No chat configurations available")
            return None
        
        choices = []
        
        # Add default chat if available
        if self.telegram_chat_id:
            choices.append(f"Default Chat ({self.telegram_chat_id})")
        
        # Add configured chats
        for name, config in self.chat_configs.items():
            chat_id = config.get('chat_id', 'Unknown')
            description = config.get('description', '')
            if description:
                choices.append(f"{name} - {description} ({chat_id})")
            else:
                choices.append(f"{name} ({chat_id})")
        
        choices.append("← Skip Telegram sending")
        
        questions = [
            inquirer.List('chat',
                         message="Select chat to send the report",
                         choices=choices)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or "Skip Telegram" in answers['chat']:
            return None
        
        selected = answers['chat']
        
        # Extract chat info
        if selected.startswith("Default Chat"):
            return {
                'name': 'Default',
                'chat_id': self.telegram_chat_id
            }
        else:
            # Extract name from selection
            name = selected.split(' - ')[0] if ' - ' in selected else selected.split(' (')[0]
            chat_id = self.get_chat_id_by_name(name)
            return {
                'name': name,
                'chat_id': chat_id
            }
