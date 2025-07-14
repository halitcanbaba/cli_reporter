#!/usr/bin/env python3
"""
Quick start script for the Scheduled Task Manager
"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import and run the scheduler
try:
    from scheduler import main
    
    if __name__ == "__main__":
        print("🚀 Starting Scheduled Task Manager...")
        print("=" * 50)
        main()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n👋 Goodbye!")
    sys.exit(0)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
