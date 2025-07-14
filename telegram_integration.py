#!/usr/bin/env python3
"""
Telegram Integration Module
Handles Telegram bot integration for sending financial reports
"""

import asyncio
import aiofiles
import os
import json
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramIntegration:
    """Telegram bot integration for sending financial reports"""
    
    def __init__(self, bot_token: str = None, config_file: str = "telegram_config.json"):
        """
        Initialize Telegram integration
        
        Args:
            bot_token: Telegram bot token
            config_file: Path to config file for storing settings
        """
        self.config_file = config_file
        self.bot_token = bot_token
        self.bot = None
        self.config = {}
        
        # Load config if exists
        self.load_config()
        
        # Initialize bot if token is available
        if self.bot_token or self.config.get('bot_token'):
            self.initialize_bot()
    
    def load_config(self):
        """Load Telegram configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    logger.info(f"✓ Loaded Telegram config from {self.config_file}")
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            self.config = {}
    
    def save_config(self):
        """Save Telegram configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                logger.info(f"✓ Saved Telegram config to {self.config_file}")
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
    
    def initialize_bot(self):
        """Initialize Telegram bot"""
        try:
            token = self.bot_token or self.config.get('bot_token')
            if not token:
                logger.warning("⚠️  No bot token available")
                return False
            
            self.bot = Bot(token=token)
            logger.info("✓ Telegram bot initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Error initializing bot: {e}")
            return False
    
    def set_bot_token(self, token: str):
        """Set and save bot token"""
        self.bot_token = token
        self.config['bot_token'] = token
        self.save_config()
        return self.initialize_bot()
    
    def add_chat(self, chat_id: str, chat_name: str):
        """Add a chat to the configuration"""
        if 'chats' not in self.config:
            self.config['chats'] = {}
        
        self.config['chats'][chat_id] = {
            'name': chat_name,
            'added_date': datetime.now().isoformat()
        }
        self.save_config()
        logger.info(f"✓ Added chat: {chat_name} ({chat_id})")
    
    def get_chats(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured chats"""
        return self.config.get('chats', {})
    
    def remove_chat(self, chat_id: str):
        """Remove a chat from configuration"""
        if 'chats' in self.config and chat_id in self.config['chats']:
            chat_name = self.config['chats'][chat_id]['name']
            del self.config['chats'][chat_id]
            self.save_config()
            logger.info(f"✓ Removed chat: {chat_name} ({chat_id})")
            return True
        return False
    
    async def send_message(self, chat_id: str, message: str, parse_mode: str = ParseMode.MARKDOWN):
        """Send a text message to a chat"""
        try:
            if not self.bot:
                logger.error("❌ Bot not initialized")
                return False
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"✓ Message sent to chat {chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")
            return False
    
    async def send_document(self, chat_id: str, file_path: str, caption: str = None):
        """Send a document to a chat"""
        try:
            if not self.bot:
                logger.error("❌ Bot not initialized")
                return False
            
            if not os.path.exists(file_path):
                logger.error(f"❌ File not found: {file_path}")
                return False
            
            # Get file size
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size_mb > 50:  # Telegram limit is 50MB
                logger.error(f"❌ File too large: {file_size_mb:.2f}MB (limit: 50MB)")
                return False
            
            async with aiofiles.open(file_path, 'rb') as f:
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    caption=caption,
                    filename=os.path.basename(file_path)
                )
            
            logger.info(f"✓ Document sent to chat {chat_id}: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending document: {e}")
            return False
    
    async def send_report(self, chat_id: str, file_path: str, report_info: Dict[str, Any]):
        """Send a financial report with formatted message"""
        try:
            # Create formatted message
            message = self.format_report_message(report_info)
            
            # Send message first
            await self.send_message(chat_id, message)
            
            # Then send the file
            caption = f"📊 {report_info.get('report_type', 'Financial Report')} - {report_info.get('date', datetime.now().strftime('%Y-%m-%d'))}"
            await self.send_document(chat_id, file_path, caption)
            
            return True
        except Exception as e:
            logger.error(f"❌ Error sending report: {e}")
            return False
    
    def format_report_message(self, report_info: Dict[str, Any]) -> str:
        """Format report information into a Telegram message"""
        try:
            db_name = report_info.get('database', 'Unknown')
            report_type = report_info.get('report_type', 'Financial Report')
            date = report_info.get('date', datetime.now().strftime('%Y-%m-%d'))
            groups = report_info.get('groups', [])
            login_range = report_info.get('login_range', 'All')
            
            # Statistics
            total_logins = report_info.get('total_logins', 0)
            total_deposits = report_info.get('total_deposits', 0)
            total_withdrawals = report_info.get('total_withdrawals', 0)
            total_promotions = report_info.get('total_promotions', 0)
            
            message = f"""
🤖 **Financial Report Generated**

📊 **Report Details:**
• Database: `{db_name}`
• Type: `{report_type}`
• Date: `{date}`
• Groups: `{', '.join(groups) if groups else 'All'}`
• Login Range: `{login_range}`

📈 **Summary:**
• Total Logins: `{total_logins:,}`
• Monthly Deposits: `${total_deposits:,.2f}`
• Monthly Withdrawals: `${total_withdrawals:,.2f}`
• Monthly Promotions: `${total_promotions:,.2f}`
• Net Flow: `${(total_deposits - total_withdrawals + total_promotions):,.2f}`

⏰ Generated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
"""
            return message.strip()
        except Exception as e:
            logger.error(f"❌ Error formatting message: {e}")
            return f"📊 Financial Report Generated - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    def is_configured(self) -> bool:
        """Check if Telegram integration is properly configured"""
        return bool(self.bot and self.config.get('bot_token'))
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            'configured': self.is_configured(),
            'bot_token_set': bool(self.config.get('bot_token')),
            'chats_count': len(self.config.get('chats', {})),
            'config_file': self.config_file
        }

# Sync wrapper functions for easier integration
def run_async(coro):
    """Run async function in sync context"""
    try:
        # Try to get current event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, create a new one in a thread
            import threading
            result = None
            exception = None
            
            def run_in_thread():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(coro)
                    new_loop.close()
                except Exception as e:
                    exception = e
                finally:
                    asyncio.set_event_loop(None)
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
            if exception:
                raise exception
            return result
            
        except RuntimeError:
            # No running event loop, we can create one safely
            try:
                return asyncio.run(coro)
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    # Create a new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(coro)
                        return result
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)
                else:
                    raise
                    
    except Exception as e:
        logger.error(f"❌ Error in run_async: {e}")
        raise

def send_report_sync(telegram_integration: TelegramIntegration, chat_id: str, file_path: str, report_info: Dict[str, Any]):
    """Synchronous wrapper for sending reports"""
    return run_async(telegram_integration.send_report(chat_id, file_path, report_info))

def send_message_sync(telegram_integration: TelegramIntegration, chat_id: str, message: str):
    """Synchronous wrapper for sending messages"""
    return run_async(telegram_integration.send_message(chat_id, message))

def send_document_sync(telegram_integration: TelegramIntegration, chat_id: str, file_path: str, caption: str = None):
    """Synchronous wrapper for sending documents"""
    return run_async(telegram_integration.send_document(chat_id, file_path, caption))

# Example usage and testing
def main():
    """Test the Telegram integration"""
    print("🤖 Telegram Integration Test")
    print("=" * 50)
    
    # Initialize integration
    telegram = TelegramIntegration()
    
    # Check status
    status = telegram.get_status()
    print(f"Status: {status}")
    
    # Test configuration
    if not telegram.is_configured():
        print("⚠️  Not configured. Please set up bot token and chats.")
        return
    
    # Test sending a message
    chats = telegram.get_chats()
    if chats:
        chat_id = list(chats.keys())[0]
        print(f"Testing message to chat: {chats[chat_id]['name']}")
        
        test_message = "🧪 Test message from Financial Report Tool"
        success = send_message_sync(telegram, chat_id, test_message)
        print(f"Message sent: {success}")
    else:
        print("❌ No chats configured")

if __name__ == "__main__":
    main()
