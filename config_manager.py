#!/usr/bin/env python3
"""
Configuration Manager
Handles saving, loading, and managing task configurations
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional, List
import inquirer
from tabulate import tabulate


class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.task_creator")
        self.config_file = os.path.join(self.config_dir, "saved_configs.json")
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
    
    def save_config(self, config_name: str, config: Dict):
        """Save configuration to file"""
        try:
            saved_configs = self.load_all_configs()
            saved_configs[config_name] = {
                **config,
                'saved_at': datetime.now().isoformat(),
                'description': f"Config saved on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(saved_configs, f, indent=2)
            
            print(f"✓ Configuration '{config_name}' saved successfully")
            return True
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return False
    
    def load_all_configs(self) -> Dict:
        """Load all saved configurations"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"❌ Error loading configurations: {e}")
            return {}
    
    def load_config(self, config_name: str) -> Optional[Dict]:
        """Load specific configuration"""
        saved_configs = self.load_all_configs()
        return saved_configs.get(config_name)
    
    def delete_config(self, config_name: str) -> bool:
        """Delete saved configuration"""
        try:
            saved_configs = self.load_all_configs()
            if config_name in saved_configs:
                del saved_configs[config_name]
                with open(self.config_file, 'w') as f:
                    json.dump(saved_configs, f, indent=2)
                print(f"✓ Configuration '{config_name}' deleted")
                return True
            else:
                print(f"❌ Configuration '{config_name}' not found")
                return False
        except Exception as e:
            print(f"❌ Error deleting configuration: {e}")
            return False
    
    def list_saved_configs(self):
        """List all saved configurations"""
        saved_configs = self.load_all_configs()
        if not saved_configs:
            print("📁 No saved configurations found")
            return []
        
        print(f"\n📁 Saved Configurations ({len(saved_configs)}):")
        print("=" * 60)
        
        config_data = []
        for name, config in saved_configs.items():
            saved_at = config.get('saved_at', 'Unknown')
            if saved_at != 'Unknown':
                try:
                    saved_dt = datetime.fromisoformat(saved_at)
                    saved_at = saved_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            groups_info = "All Groups"
            if config.get('groups'):
                groups_info = f"{len(config['groups'])} groups"
            
            config_data.append([
                name,
                config.get('database', 'N/A'),
                groups_info,
                f"{config.get('min_login', 'N/A'):,} - {config.get('max_login', 'N/A'):,}",
                config.get('report_type', 'N/A'),
                saved_at
            ])
        
        headers = ['Name', 'Database', 'Groups', 'Login Range', 'Report Type', 'Saved At']
        print(tabulate(config_data, headers=headers, tablefmt='grid'))
        
        return list(saved_configs.keys())
    
    def handle_saved_configs(self, selected_config: Dict) -> bool:
        """Handle loading of saved configurations at startup"""
        saved_configs = self.load_all_configs()
        
        if not saved_configs:
            print("📁 No saved configurations found. Starting with new configuration...")
            return True, selected_config
        
        print(f"\n📁 Found {len(saved_configs)} saved configuration(s)")
        
        # Show available options
        config_options = [
            "Create New Configuration",
            "Load Saved Configuration",
            "Manage Saved Configurations"
        ]
        
        questions = [
            inquirer.List('action',
                         message="What would you like to do?",
                         choices=config_options,
                         default="Load Saved Configuration")
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            return False, selected_config
        
        action = answers['action']
        
        if action == "Create New Configuration":
            print("✓ Starting with new configuration...")
            return True, selected_config
            
        elif action == "Load Saved Configuration":
            return self._load_saved_config(selected_config)
            
        elif action == "Manage Saved Configurations":
            return self._manage_saved_configs(selected_config)
        
        return True, selected_config
    
    def _load_saved_config(self, selected_config: Dict) -> tuple:
        """Load a saved configuration"""
        saved_configs = self.load_all_configs()
        
        if not saved_configs:
            print("❌ No saved configurations found")
            return True, selected_config
        
        # Show configurations with details
        config_choices = []
        for name, config in saved_configs.items():
            saved_at = config.get('saved_at', 'Unknown')
            if saved_at != 'Unknown':
                try:
                    saved_dt = datetime.fromisoformat(saved_at)
                    saved_at = saved_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            groups_info = "All Groups"
            if config.get('groups'):
                groups_info = f"{len(config['groups'])} groups"
            
            choice_text = f"{name} | {config.get('database', 'N/A')} | {groups_info} | {saved_at}"
            config_choices.append(choice_text)
        
        config_choices.append("← Back to Main Menu")
        
        questions = [
            inquirer.List('config',
                         message="Select configuration to load",
                         choices=config_choices)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or answers['config'] == "← Back to Main Menu":
            return self.handle_saved_configs(selected_config)
        
        # Extract config name from choice
        config_name = answers['config'].split(' | ')[0]
        config = self.load_config(config_name)
        
        if not config:
            print(f"❌ Error loading configuration '{config_name}'")
            return False, selected_config
        
        # Load configuration into selected_config
        loaded_config = {
            'database': config.get('database', 'mt5gn_live'),
            'groups': config.get('groups'),
            'removed_logins': config.get('removed_logins', []),
            'min_login': config.get('min_login'),
            'max_login': config.get('max_login'),
            'report_type': config.get('report_type'),
            'limit': config.get('limit')
        }
        
        print(f"✓ Configuration '{config_name}' loaded successfully")
        print(f"  Database: {loaded_config['database']}")
        print(f"  Groups: {len(loaded_config['groups']) if loaded_config['groups'] else 'All'}")
        print(f"  Login Range: {loaded_config['min_login']:,} - {loaded_config['max_login']:,}")
        print(f"  Report Type: {loaded_config['report_type']}")
        if loaded_config['removed_logins']:
            print(f"  Removed Logins: {len(loaded_config['removed_logins'])}")
        
        return True, loaded_config
    
    def _manage_saved_configs(self, selected_config: Dict) -> tuple:
        """Manage saved configurations"""
        while True:
            management_options = [
                "List All Configurations",
                "Delete Configuration",
                "← Back to Main Menu"
            ]
            
            questions = [
                inquirer.List('action',
                             message="Configuration Management",
                             choices=management_options)
            ]
            
            answers = inquirer.prompt(questions)
            if not answers or answers['action'] == "← Back to Main Menu":
                return self.handle_saved_configs(selected_config)
            
            action = answers['action']
            
            if action == "List All Configurations":
                self.list_saved_configs()
                input("\nPress Enter to continue...")
                
            elif action == "Delete Configuration":
                if not self._delete_config_interactive():
                    continue
        
        return True, selected_config
    
    def _delete_config_interactive(self) -> bool:
        """Interactive configuration deletion"""
        saved_configs = self.load_all_configs()
        
        if not saved_configs:
            print("❌ No saved configurations to delete")
            return True
        
        config_names = list(saved_configs.keys())
        config_names.append("← Cancel")
        
        questions = [
            inquirer.List('config',
                         message="Select configuration to delete",
                         choices=config_names)
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or answers['config'] == "← Cancel":
            return True
        
        config_name = answers['config']
        
        # Confirm deletion
        questions = [
            inquirer.Confirm('confirm',
                           message=f"Are you sure you want to delete '{config_name}'?",
                           default=False)
        ]
        
        answers = inquirer.prompt(questions)
        if answers and answers['confirm']:
            self.delete_config(config_name)
        
        return True
    
    def offer_save_config(self, selected_config: Dict):
        """Offer to save the current configuration"""
        questions = [
            inquirer.Confirm('save',
                           message="Save this configuration for future use?",
                           default=False)
        ]
        
        answers = inquirer.prompt(questions)
        if answers and answers['save']:
            questions = [
                inquirer.Text('name',
                             message="Enter configuration name",
                             validate=lambda _, x: len(x.strip()) > 0)
            ]
            
            answers = inquirer.prompt(questions)
            if answers and answers['name']:
                config_name = answers['name'].strip()
                
                # Check if config already exists
                existing_configs = self.load_all_configs()
                if config_name in existing_configs:
                    questions = [
                        inquirer.Confirm('overwrite',
                                       message=f"Configuration '{config_name}' already exists. Overwrite?",
                                       default=False)
                    ]
                    
                    answers = inquirer.prompt(questions)
                    if not answers or not answers['overwrite']:
                        print("❌ Configuration not saved")
                        return
                
                # Save configuration
                config_to_save = selected_config.copy()
                self.save_config(config_name, config_to_save)
