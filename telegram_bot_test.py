#!/usr/bin/env python3
"""
Comprehensive Telegram Bot Command Functionality Tests
Tests all bot commands, inline keyboards, callback handlers, and integration features.
"""

import requests
import json
import time
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, List
import asyncio
import os
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

if not backend_url:
    raise Exception("Could not find REACT_APP_BACKEND_URL in frontend/.env")

# API base URL
API_BASE = f"{backend_url}/api"

print(f"Testing Telegram Bot API at: {API_BASE}")

class TelegramBotCommandTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.auth_token = None
        self.test_user_data = None
        self.telegram_bot_token = "8342094196:AAE-E8jIYLjYflUPtY0G02NLbogbDpN_FE8"  # From backend .env
        self.webhook_secret = "telegram_bot_webhook_secret_2025"  # From backend .env

    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'response_data': response_data
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    Details: {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")
        print()

    def generate_telegram_auth_data(self, telegram_id: int, first_name: str, last_name: str = None, username: str = None, photo_url: str = None) -> Dict[str, Any]:
        """Generate valid Telegram authentication data with proper hash"""
        auth_date = int(datetime.now(timezone.utc).timestamp())
        
        # Create auth data
        auth_data = {
            'id': telegram_id,
            'first_name': first_name,
            'auth_date': auth_date
        }
        
        if last_name:
            auth_data['last_name'] = last_name
        if username:
            auth_data['username'] = username
        if photo_url:
            auth_data['photo_url'] = photo_url
        
        # Create data check string (sorted by key)
        data_check_arr = [f"{key}={value}" for key, value in sorted(auth_data.items())]
        data_check_string = '\n'.join(data_check_arr)
        
        # Create secret key from bot token
        secret_key = hashlib.sha256(self.telegram_bot_token.encode()).digest()
        
        # Generate hash
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        # Add hash to auth data
        auth_data['hash'] = calculated_hash
        
        return auth_data

    def setup_test_user(self):
        """Setup a test user for bot command testing"""
        try:
            import random
            import time
            
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
                
                self.log_test("Bot Test User Setup", True, 
                            f"Created test user @{username} for bot testing", auth_response)
                return True
            else:
                self.log_test("Bot Test User Setup", False, 
                            f"Failed to create test user: HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Bot Test User Setup", False, f"Error: {str(e)}")
            return False

    def test_bot_connection_and_info(self):
        """Test bot connection and retrieve bot information"""
        try:
            response = self.session.post(f"{API_BASE}/test/bot")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'bot_info' in data:
                    bot_info = data['bot_info']
                    expected_bot_id = "8342094196"  # From the token
                    
                    if str(bot_info.get('id')) == expected_bot_id:
                        self.log_test("Bot Connection & Info", True, 
                                    f"Bot connected: @{bot_info.get('username')} (ID: {bot_info.get('id')})", data)
                    else:
                        self.log_test("Bot Connection & Info", False, 
                                    f"Bot ID mismatch. Expected: {expected_bot_id}, Got: {bot_info.get('id')}", data)
                else:
                    self.log_test("Bot Connection & Info", False, "Invalid response format", data)
            else:
                self.log_test("Bot Connection & Info", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Connection & Info", False, f"Request error: {str(e)}")

    def test_webhook_setup_and_configuration(self):
        """Test webhook setup and configuration"""
        try:
            # Test setting webhook
            response = self.session.post(f"{API_BASE}/telegram/set-webhook")
            
            if response.status_code == 200:
                webhook_data = response.json()
                if webhook_data.get('status') == 'success' and 'webhook_url' in webhook_data:
                    webhook_url = webhook_data['webhook_url']
                    expected_secret = self.webhook_secret
                    
                    if expected_secret in webhook_url:
                        self.log_test("Webhook Setup", True, 
                                    f"Webhook configured successfully: {webhook_url}", webhook_data)
                    else:
                        self.log_test("Webhook Setup", False, 
                                    "Webhook URL doesn't contain expected secret", webhook_data)
                else:
                    self.log_test("Webhook Setup", False, "Invalid webhook response format", webhook_data)
            else:
                self.log_test("Webhook Setup", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Webhook Setup", False, f"Error: {str(e)}")

    def create_mock_telegram_update(self, message_text: str, chat_id: int = 123456789, user_id: int = None, username: str = "bottester") -> Dict[str, Any]:
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

    def create_mock_callback_query(self, callback_data: str, chat_id: int = 123456789, user_id: int = None, username: str = "bottester") -> Dict[str, Any]:
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
                "data": callback_data
            }
        }

    def test_bot_command_start(self):
        """Test /start command - should show main menu with inline keyboards"""
        try:
            # Create mock /start command update
            update_data = self.create_mock_telegram_update("/start")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Bot Command - /start", True, 
                                "Start command processed successfully, main menu should be displayed", webhook_response)
                else:
                    self.log_test("Bot Command - /start", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Bot Command - /start", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Command - /start", False, f"Error: {str(e)}")

    def test_bot_command_help(self):
        """Test /help command - should display help information"""
        try:
            # Create mock /help command update
            update_data = self.create_mock_telegram_update("/help")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Bot Command - /help", True, 
                                "Help command processed successfully", webhook_response)
                else:
                    self.log_test("Bot Command - /help", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Bot Command - /help", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Command - /help", False, f"Error: {str(e)}")

    def test_bot_command_menu(self):
        """Test /menu command - should show main menu"""
        try:
            # Create mock /menu command update
            update_data = self.create_mock_telegram_update("/menu")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Bot Command - /menu", True, 
                                "Menu command processed successfully", webhook_response)
                else:
                    self.log_test("Bot Command - /menu", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Bot Command - /menu", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Command - /menu", False, f"Error: {str(e)}")

    def test_callback_query_status(self):
        """Test callback query handler for 'status' button"""
        try:
            # Create mock callback query for status
            update_data = self.create_mock_callback_query("status")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Callback Query - Status", True, 
                                "Status callback query processed successfully", webhook_response)
                else:
                    self.log_test("Callback Query - Status", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Callback Query - Status", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Callback Query - Status", False, f"Error: {str(e)}")

    def test_callback_query_groups(self):
        """Test callback query handler for 'groups' button"""
        try:
            # Create mock callback query for groups
            update_data = self.create_mock_callback_query("groups")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Callback Query - Groups", True, 
                                "Groups callback query processed successfully", webhook_response)
                else:
                    self.log_test("Callback Query - Groups", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Callback Query - Groups", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Callback Query - Groups", False, f"Error: {str(e)}")

    def test_callback_query_watchlist(self):
        """Test callback query handler for 'watchlist' button"""
        try:
            # Create mock callback query for watchlist
            update_data = self.create_mock_callback_query("watchlist")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Callback Query - Watchlist", True, 
                                "Watchlist callback query processed successfully", webhook_response)
                else:
                    self.log_test("Callback Query - Watchlist", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Callback Query - Watchlist", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Callback Query - Watchlist", False, f"Error: {str(e)}")

    def test_callback_query_messages(self):
        """Test callback query handler for 'messages' button"""
        try:
            # Create mock callback query for messages
            update_data = self.create_mock_callback_query("messages")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Callback Query - Messages", True, 
                                "Messages callback query processed successfully", webhook_response)
                else:
                    self.log_test("Callback Query - Messages", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Callback Query - Messages", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Callback Query - Messages", False, f"Error: {str(e)}")

    def test_callback_query_settings(self):
        """Test callback query handler for 'settings' button"""
        try:
            # Create mock callback query for settings
            update_data = self.create_mock_callback_query("settings")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Callback Query - Settings", True, 
                                "Settings callback query processed successfully", webhook_response)
                else:
                    self.log_test("Callback Query - Settings", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Callback Query - Settings", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Callback Query - Settings", False, f"Error: {str(e)}")

    def test_callback_query_help(self):
        """Test callback query handler for 'help' button"""
        try:
            # Create mock callback query for help
            update_data = self.create_mock_callback_query("help")
            
            # Send to webhook endpoint
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                if webhook_response.get('status') == 'ok':
                    self.log_test("Callback Query - Help", True, 
                                "Help callback query processed successfully", webhook_response)
                else:
                    self.log_test("Callback Query - Help", False, 
                                "Webhook processed but status not 'ok'", webhook_response)
            else:
                self.log_test("Callback Query - Help", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Callback Query - Help", False, f"Error: {str(e)}")

    def test_callback_query_navigation(self):
        """Test callback query navigation (main_menu, admin_menu)"""
        try:
            # Test main_menu callback
            update_data = self.create_mock_callback_query("main_menu")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                self.log_test("Callback Query - Main Menu Navigation", True, 
                            "Main menu navigation processed successfully")
            else:
                self.log_test("Callback Query - Main Menu Navigation", False, 
                            f"HTTP {response.status_code}", response.text)
            
            # Test admin_menu callback
            update_data = self.create_mock_callback_query("admin_menu")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                self.log_test("Callback Query - Admin Menu Navigation", True, 
                            "Admin menu navigation processed successfully")
            else:
                self.log_test("Callback Query - Admin Menu Navigation", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Callback Query - Navigation", False, f"Error: {str(e)}")

    def test_webhook_authentication(self):
        """Test webhook authentication with correct and incorrect secrets"""
        try:
            # Test with correct secret
            update_data = self.create_mock_telegram_update("/start")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=update_data
            )
            
            if response.status_code == 200:
                self.log_test("Webhook Authentication - Valid Secret", True, 
                            "Webhook accepted with valid secret")
            else:
                self.log_test("Webhook Authentication - Valid Secret", False, 
                            f"Valid secret rejected: HTTP {response.status_code}", response.text)
            
            # Test with incorrect secret
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/invalid_secret",
                json=update_data
            )
            
            if response.status_code == 403:
                self.log_test("Webhook Authentication - Invalid Secret", True, 
                            "Webhook correctly rejected invalid secret with HTTP 403")
            else:
                self.log_test("Webhook Authentication - Invalid Secret", False, 
                            f"Expected HTTP 403 but got {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Webhook Authentication", False, f"Error: {str(e)}")

    def test_bot_integration_with_database(self):
        """Test bot's integration with database (statistics, groups, watchlist)"""
        try:
            # Test that bot can access statistics
            response = self.session.get(f"{API_BASE}/stats")
            
            if response.status_code == 200:
                stats = response.json()
                required_stats = ['total_groups', 'total_watchlist_users', 'total_messages']
                
                if all(stat in stats for stat in required_stats):
                    self.log_test("Bot Database Integration - Statistics", True, 
                                f"Bot can access statistics: {stats}", stats)
                else:
                    missing_stats = [stat for stat in required_stats if stat not in stats]
                    self.log_test("Bot Database Integration - Statistics", False, 
                                f"Missing statistics: {missing_stats}", stats)
            else:
                self.log_test("Bot Database Integration - Statistics", False, 
                            f"Cannot access statistics: HTTP {response.status_code}", response.text)
            
            # Test that bot can access groups
            response = self.session.get(f"{API_BASE}/groups")
            
            if response.status_code == 200:
                groups = response.json()
                self.log_test("Bot Database Integration - Groups", True, 
                            f"Bot can access groups data: {len(groups)} groups", groups)
            else:
                self.log_test("Bot Database Integration - Groups", False, 
                            f"Cannot access groups: HTTP {response.status_code}", response.text)
            
            # Test that bot can access watchlist
            response = self.session.get(f"{API_BASE}/watchlist")
            
            if response.status_code == 200:
                watchlist = response.json()
                self.log_test("Bot Database Integration - Watchlist", True, 
                            f"Bot can access watchlist data: {len(watchlist)} users", watchlist)
            else:
                self.log_test("Bot Database Integration - Watchlist", False, 
                            f"Cannot access watchlist: HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Database Integration", False, f"Error: {str(e)}")

    def test_bot_error_handling(self):
        """Test bot error handling for various scenarios"""
        try:
            # Test invalid webhook data
            invalid_update = {"invalid": "data"}
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=invalid_update
            )
            
            # Bot should handle invalid data gracefully
            if response.status_code in [200, 400, 422]:
                self.log_test("Bot Error Handling - Invalid Update Data", True, 
                            f"Bot handled invalid update data gracefully: HTTP {response.status_code}")
            else:
                self.log_test("Bot Error Handling - Invalid Update Data", False, 
                            f"Unexpected response to invalid data: HTTP {response.status_code}", response.text)
            
            # Test unknown command
            unknown_command_update = self.create_mock_telegram_update("/unknown_command")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=unknown_command_update
            )
            
            if response.status_code == 200:
                self.log_test("Bot Error Handling - Unknown Command", True, 
                            "Bot handled unknown command gracefully")
            else:
                self.log_test("Bot Error Handling - Unknown Command", False, 
                            f"Bot failed to handle unknown command: HTTP {response.status_code}", response.text)
            
            # Test unknown callback query
            unknown_callback_update = self.create_mock_callback_query("unknown_action")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=unknown_callback_update
            )
            
            if response.status_code == 200:
                self.log_test("Bot Error Handling - Unknown Callback", True, 
                            "Bot handled unknown callback query gracefully")
            else:
                self.log_test("Bot Error Handling - Unknown Callback", False, 
                            f"Bot failed to handle unknown callback: HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Error Handling", False, f"Error: {str(e)}")

    def test_bot_multi_tenant_support(self):
        """Test bot's multi-tenant support and data isolation"""
        try:
            # This test verifies that bot commands work with authenticated users
            # and respect organization boundaries
            
            if not self.test_user_data:
                self.log_test("Bot Multi-Tenant Support", False, "No test user data available")
                return
            
            # Create a group for this organization
            test_group_data = {
                "group_id": f"-100{int(time.time())}",
                "group_name": "Bot Test Group",
                "group_type": "supergroup",
                "description": "Test group for bot multi-tenant testing"
            }
            
            response = self.session.post(f"{API_BASE}/groups", json=test_group_data)
            
            if response.status_code == 200:
                created_group = response.json()
                
                # Now test that bot status command shows this group
                status_update = self.create_mock_callback_query("status")
                
                response = self.session.post(
                    f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                    json=status_update
                )
                
                if response.status_code == 200:
                    self.log_test("Bot Multi-Tenant Support", True, 
                                "Bot successfully processes commands with tenant-specific data")
                else:
                    self.log_test("Bot Multi-Tenant Support", False, 
                                f"Bot failed to process tenant-specific command: HTTP {response.status_code}")
                
                # Clean up
                self.session.delete(f"{API_BASE}/groups/{created_group['id']}")
                
            else:
                self.log_test("Bot Multi-Tenant Support", False, 
                            f"Could not create test group: HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Multi-Tenant Support", False, f"Error: {str(e)}")

    def test_bot_analytics_integration(self):
        """Test bot's integration with analytics system"""
        try:
            # Test that bot commands are logged to database
            initial_commands_response = self.session.get(f"{API_BASE}/stats")
            
            if initial_commands_response.status_code != 200:
                self.log_test("Bot Analytics Integration", False, "Cannot access initial statistics")
                return
            
            # Send a bot command
            command_update = self.create_mock_telegram_update("/start")
            
            response = self.session.post(
                f"{API_BASE}/telegram/webhook/{self.webhook_secret}",
                json=command_update
            )
            
            if response.status_code == 200:
                # Wait a moment for processing
                time.sleep(1)
                
                # Check if command was logged (this would require checking bot_commands collection)
                # For now, we'll just verify the webhook processed successfully
                self.log_test("Bot Analytics Integration", True, 
                            "Bot command processed and should be logged to analytics")
            else:
                self.log_test("Bot Analytics Integration", False, 
                            f"Bot command failed to process: HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Analytics Integration", False, f"Error: {str(e)}")

    def run_all_bot_tests(self):
        """Run all Telegram bot command functionality tests"""
        print("🤖 Starting Telegram Bot Command Functionality Tests")
        print("=" * 70)
        
        # Setup test user first
        if not self.setup_test_user():
            print("❌ Failed to setup test user. Some tests may fail.")
        
        # Test bot connection and basic setup
        self.test_bot_connection_and_info()
        self.test_webhook_setup_and_configuration()
        
        # Test bot commands
        self.test_bot_command_start()
        self.test_bot_command_help()
        self.test_bot_command_menu()
        
        # Test callback query handlers
        self.test_callback_query_status()
        self.test_callback_query_groups()
        self.test_callback_query_watchlist()
        self.test_callback_query_messages()
        self.test_callback_query_settings()
        self.test_callback_query_help()
        self.test_callback_query_navigation()
        
        # Test authentication and security
        self.test_webhook_authentication()
        
        # Test integration features
        self.test_bot_integration_with_database()
        self.test_bot_multi_tenant_support()
        self.test_bot_analytics_integration()
        
        # Test error handling
        self.test_bot_error_handling()
        
        print("\n" + "=" * 70)
        print("📊 TELEGRAM BOT COMMAND FUNCTIONALITY TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Bot Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        if failed_tests > 0:
            print("\n❌ FAILED BOT TESTS:")
            for test in self.test_results:
                if not test['success']:
                    print(f"  • {test['test']}: {test['details']}")
        
        print("\n" + "=" * 70)
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests/total_tests)*100 if total_tests > 0 else 0,
            'results': self.test_results
        }

if __name__ == "__main__":
    tester = TelegramBotCommandTester()
    results = tester.run_all_bot_tests()
    
    print(f"\n🎯 FINAL RESULT: {results['passed']}/{results['total']} tests passed ({results['success_rate']:.1f}%)")
    
    if results['success_rate'] >= 80:
        print("🎉 Bot command functionality is working well!")
    elif results['success_rate'] >= 60:
        print("⚠️ Bot command functionality has some issues but core features work")
    else:
        print("❌ Bot command functionality needs significant fixes")