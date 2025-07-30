#!/usr/bin/env python3
"""
Quick test for Telegram Bot callback query functionality
"""

import requests
import json
import time
from pathlib import Path

# Read the backend URL from frontend .env
frontend_env_path = Path("/app/frontend/.env")
backend_url = None

if frontend_env_path.exists():
    with open(frontend_env_path, 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                backend_url = line.split('=', 1)[1].strip()
                break

API_BASE = f"{backend_url}/api"
webhook_secret = "telegram_bot_webhook_secret_2025"

def create_mock_callback_query(callback_data: str):
    """Create a mock Telegram callback query for testing"""
    return {
        "update_id": int(time.time()),
        "callback_query": {
            "id": f"callback_{int(time.time())}",
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Bot",
                "last_name": "Tester",
                "username": "bottester"
            },
            "message": {
                "message_id": int(time.time()),
                "from": {
                    "id": 8342094196,  # Bot ID
                    "is_bot": True,
                    "first_name": "TeleWatch",
                    "username": "Telewatch_test_bot"
                },
                "chat": {
                    "id": 123456789,
                    "first_name": "Bot",
                    "last_name": "Tester",
                    "username": "bottester",
                    "type": "private"
                },
                "date": int(time.time()),
                "text": "Previous message text"
            },
            "chat_instance": f"chat_instance_{int(time.time())}",
            "data": callback_data
        }
    }

def test_callback_query(callback_data: str):
    """Test a specific callback query"""
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    update_data = create_mock_callback_query(callback_data)
    
    try:
        response = session.post(
            f"{API_BASE}/telegram/webhook/{webhook_secret}",
            json=update_data
        )
        
        print(f"Testing callback '{callback_data}': ", end="")
        if response.status_code == 200:
            print("✅ SUCCESS")
            return True
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR - {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Telegram Bot Callback Queries")
    print("=" * 50)
    
    callbacks_to_test = [
        "status",
        "groups", 
        "watchlist",
        "messages",
        "settings",
        "help",
        "main_menu",
        "admin_menu"
    ]
    
    passed = 0
    total = len(callbacks_to_test)
    
    for callback in callbacks_to_test:
        if test_callback_query(callback):
            passed += 1
    
    print("=" * 50)
    print(f"Results: {passed}/{total} callback queries working ({(passed/total)*100:.1f}%)")