#!/usr/bin/env python3
"""
Comprehensive Telegram Bot Functionality Test
Tests all major bot features including commands, callbacks, authentication, and integration.
"""

import requests
import json
import time
import hashlib
import hmac
from datetime import datetime, timezone
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
telegram_bot_token = "8342094196:AAE-E8jIYLjYflUPtY0G02NLbogbDpN_FE8"

class BotTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.auth_token = None
        self.test_user_data = None

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    Details: {details}")
        print()

    def setup_test_user(self):
        """Setup a test user for bot testing"""
        try:
            import random
            
            # Generate unique test data
            timestamp = int(time.time())
            random_suffix = random.randint(1000, 9999)
            
            telegram_id = random.randint(100000000, 999999999)
            username = f"bottest_{timestamp}_{random_suffix}"
            org_name = f"Bot Test Organization {timestamp}"
            
            registration_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": "Bot",
                "last_name": "Tester",
                "photo_url": "https://example.com/bot_tester.jpg",
                "organization_name": org_name
            }
            
            response = self.session.post(f"{API_BASE}/auth/register", json=registration_data)
            
            if response.status_code == 200:
                auth_response = response.json()
                self.auth_token = auth_response['access_token']
                self.test_user_data = {
                    'telegram_id': telegram_id,
                    'username': username,
                    'organization_name': org_name,
                    'user_id': auth_response['user']['id'],
                    'organization_id': auth_response['user']['organization_id']
                }
                
                # Set auth header for subsequent tests
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                
                self.log_test("Test User Setup", True, f"Created test user @{username}")
                return True
            else:
                self.log_test("Test User Setup", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Test User Setup", False, f"Error: {str(e)}")
            return False

    def create_mock_telegram_update(self, message_text: str, chat_id: int = 123456789, user_id: int = None, username: str = "bottester"):
        """Create a mock Telegram update for testing"""
        if user_id is None:
            user_id = self.test_user_data['telegram_id'] if self.test_user_data else 987654321
            
        return {
            "update_id": int(time.time()),
            "message": {
                "message_id": int(time.time()),
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": "Bot",
                    "last_name": "Tester",
                    "username": username
                },
                "chat": {
                    "id": chat_id,
                    "first_name": "Bot",
                    "last_name": "Tester",
                    "username": username,
                    "type": "private"
                },
                "date": int(time.time()),
                "text": message_text
            }
        }

    def create_mock_callback_query(self, callback_data: str, chat_id: int = 123456789, user_id: int = None, username: str = "bottester"):
        """Create a mock Telegram callback query for testing"""
        if user_id is None:
            user_id = self.test_user_data['telegram_id'] if self.test_user_data else 987654321
            
        return {
            "update_id": int(time.time()),
            "callback_query": {
                "id": f"callback_{int(time.time())}",
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": "Bot",
                    "last_name": "Tester",
                    "username": username
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
                        "id": chat_id,
                        "first_name": "Bot",
                        "last_name": "Tester",
                        "username": username,
                        "type": "private"
                    },
                    "date": int(time.time()),
                    "text": "Previous message text"
                },
                "chat_instance": f"chat_instance_{int(time.time())}",
                "data": callback_data
            }
        }

    def test_bot_connection(self):
        """Test bot connection and basic info"""
        try:
            response = self.session.post(f"{API_BASE}/test/bot")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'bot_info' in data:
                    bot_info = data['bot_info']
                    self.log_test("Bot Connection", True, 
                                f"Bot: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
                else:
                    self.log_test("Bot Connection", False, "Invalid response format")
            else:
                self.log_test("Bot Connection", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Bot Connection", False, f"Error: {str(e)}")

    def test_webhook_setup(self):
        """Test webhook setup"""
        try:
            response = self.session.post(f"{API_BASE}/telegram/set-webhook")
            
            if response.status_code == 200:
                webhook_data = response.json()
                if webhook_data.get('status') == 'success':
                    self.log_test("Webhook Setup", True, "Webhook configured successfully")
                else:
                    self.log_test("Webhook Setup", False, "Webhook setup failed")
            else:
                self.log_test("Webhook Setup", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Webhook Setup", False, f"Error: {str(e)}")

    def test_bot_commands(self):
        """Test all bot commands"""
        commands = ["/start", "/help", "/menu"]
        
        for command in commands:
            try:
                update_data = self.create_mock_telegram_update(command)
                
                response = self.session.post(
                    f"{API_BASE}/telegram/webhook/{webhook_secret}",
                    json=update_data
                )
                
                if response.status_code == 200:
                    webhook_response = response.json()
                    if webhook_response.get('status') == 'ok':
                        self.log_test(f"Bot Command {command}", True, "Command processed successfully")
                    else:
                        self.log_test(f"Bot Command {command}", False, "Webhook status not 'ok'")
                else:
                    self.log_test(f"Bot Command {command}", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Bot Command {command}", False, f"Error: {str(e)}")

    def test_inline_keyboards(self):
        """Test inline keyboard callback queries"""
        callbacks = ["status", "groups", "watchlist", "messages", "settings", "help", "main_menu", "admin_menu"]
        
        for callback in callbacks:
            try:
                update_data = self.create_mock_callback_query(callback)
                
                response = self.session.post(
                    f"{API_BASE}/telegram/webhook/{webhook_secret}",
                    json=update_data
                )
                
                if response.status_code == 200:
                    webhook_response = response.json()
                    if webhook_response.get('status') == 'ok':
                        self.log_test(f"Inline Keyboard - {callback.title()}", True, "Callback processed successfully")
                    else:
                        self.log_test(f"Inline Keyboard - {callback.title()}", False, "Webhook status not 'ok'")
                else:
                    self.log_test(f"Inline Keyboard - {callback.title()}", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Inline Keyboard - {callback.title()}", False, f"Error: {str(e)}")

    def test_webhook_authentication(self):
        """Test webhook authentication"""
        try:
            update_data = self.create_mock_telegram_update("/start")
            
            # Test with valid secret
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                self.log_test("Webhook Auth - Valid Secret", True, "Valid secret accepted")
            else:
                self.log_test("Webhook Auth - Valid Secret", False, f"HTTP {response.status_code}")
            
            # Test with invalid secret
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/invalid_secret",
                json=update_data
            )
            
            if response.status_code == 403:
                self.log_test("Webhook Auth - Invalid Secret", True, "Invalid secret rejected with HTTP 403")
            else:
                self.log_test("Webhook Auth - Invalid Secret", False, f"Expected HTTP 403, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Webhook Authentication", False, f"Error: {str(e)}")

    def test_database_integration(self):
        """Test bot's integration with database"""
        try:
            # Test statistics access
            response = self.session.get(f"{API_BASE}/stats")
            
            if response.status_code == 200:
                stats = response.json()
                required_stats = ['total_groups', 'total_watchlist_users', 'total_messages']
                
                if all(stat in stats for stat in required_stats):
                    self.log_test("Database Integration - Statistics", True, 
                                f"Bot can access statistics data")
                else:
                    missing_stats = [stat for stat in required_stats if stat not in stats]
                    self.log_test("Database Integration - Statistics", False, 
                                f"Missing statistics: {missing_stats}")
            else:
                self.log_test("Database Integration - Statistics", False, 
                            f"Cannot access statistics: HTTP {response.status_code}")
            
            # Test groups access
            response = self.session.get(f"{API_BASE}/groups")
            
            if response.status_code == 200:
                self.log_test("Database Integration - Groups", True, "Bot can access groups data")
            else:
                self.log_test("Database Integration - Groups", False, 
                            f"Cannot access groups: HTTP {response.status_code}")
            
            # Test watchlist access
            response = self.session.get(f"{API_BASE}/watchlist")
            
            if response.status_code == 200:
                self.log_test("Database Integration - Watchlist", True, "Bot can access watchlist data")
            else:
                self.log_test("Database Integration - Watchlist", False, 
                            f"Cannot access watchlist: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Database Integration", False, f"Error: {str(e)}")

    def test_error_handling(self):
        """Test bot error handling"""
        try:
            # Test unknown command
            unknown_command_update = self.create_mock_telegram_update("/unknown_command")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{webhook_secret}",
                json=unknown_command_update
            )
            
            if response.status_code == 200:
                self.log_test("Error Handling - Unknown Command", True, "Unknown command handled gracefully")
            else:
                self.log_test("Error Handling - Unknown Command", False, 
                            f"Failed to handle unknown command: HTTP {response.status_code}")
            
            # Test unknown callback
            unknown_callback_update = self.create_mock_callback_query("unknown_action")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{webhook_secret}",
                json=unknown_callback_update
            )
            
            if response.status_code == 200:
                self.log_test("Error Handling - Unknown Callback", True, "Unknown callback handled gracefully")
            else:
                self.log_test("Error Handling - Unknown Callback", False, 
                            f"Failed to handle unknown callback: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Error Handling", False, f"Error: {str(e)}")

    def test_multi_tenant_support(self):
        """Test multi-tenant support"""
        try:
            if not self.test_user_data:
                self.log_test("Multi-Tenant Support", False, "No test user data available")
                return
            
            # Create a test group for this organization
            test_group_data = {
                "group_id": f"-100{int(time.time())}",
                "group_name": "Bot Test Group",
                "group_type": "supergroup",
                "description": "Test group for bot multi-tenant testing"
            }
            
            response = self.session.post(f"{API_BASE}/groups", json=test_group_data)
            
            if response.status_code == 200:
                created_group = response.json()
                
                # Test that bot status command works with tenant data
                status_update = self.create_mock_callback_query("status")
                
                response = self.session.post(
                    f"{API_BASE}/telegram/webhook/{webhook_secret}",
                    json=status_update
                )
                
                if response.status_code == 200:
                    self.log_test("Multi-Tenant Support", True, 
                                "Bot processes commands with tenant-specific data")
                else:
                    self.log_test("Multi-Tenant Support", False, 
                                f"Bot failed to process tenant command: HTTP {response.status_code}")
                
                # Clean up
                self.session.delete(f"{API_BASE}/groups/{created_group['id']}")
                
            else:
                self.log_test("Multi-Tenant Support", False, 
                            f"Could not create test group: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Multi-Tenant Support", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all bot functionality tests"""
        print("🤖 COMPREHENSIVE TELEGRAM BOT FUNCTIONALITY TESTS")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_user():
            print("⚠️ Warning: Test user setup failed. Some tests may not work properly.")
        
        # Core bot functionality
        self.test_bot_connection()
        self.test_webhook_setup()
        
        # Bot commands
        self.test_bot_commands()
        
        # Inline keyboards
        self.test_inline_keyboards()
        
        # Authentication and security
        self.test_webhook_authentication()
        
        # Integration features
        self.test_database_integration()
        self.test_multi_tenant_support()
        
        # Error handling
        self.test_error_handling()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test['success']:
                    print(f"  • {test['test']}: {test['details']}")
        
        print("\n" + "=" * 60)
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests/total_tests)*100 if total_tests > 0 else 0
        }

if __name__ == "__main__":
    tester = BotTester()
    results = tester.run_all_tests()
    
    print(f"🎯 FINAL RESULT: {results['passed']}/{results['total']} tests passed ({results['success_rate']:.1f}%)")
    
    if results['success_rate'] >= 85:
        print("🎉 Telegram Bot functionality is working excellently!")
    elif results['success_rate'] >= 70:
        print("✅ Telegram Bot functionality is working well with minor issues")
    elif results['success_rate'] >= 50:
        print("⚠️ Telegram Bot functionality has some issues but core features work")
    else:
        print("❌ Telegram Bot functionality needs significant fixes")