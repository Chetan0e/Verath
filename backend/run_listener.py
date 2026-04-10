#!/usr/bin/env python3
"""
Always-on listener for SecondBrain.
Records audio chunks and processes them when speech is detected.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.listener import start_listener
from app.services.pipeline import process_audio

def main():
    """Start the always-on listener."""
    print("🎤 Starting SecondBrain Always-on Listener")
    print("=" * 50)
    print("This will continuously listen for speech and process it.")
    print("Press Ctrl+C to stop.")
    print("=" * 50)
    
    try:
        start_listener(process_audio)
    except KeyboardInterrupt:
        print("\n👋 Listener stopped by user")
    except Exception as e:
        print(f"❌ Error in listener: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
