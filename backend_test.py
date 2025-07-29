#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Telegram Monitoring Bot
Tests all endpoints and functionality as specified in the review request.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Load backend URL from frontend .env
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

print(f"Testing backend API at: {API_BASE}")

class TelegramBotAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_resources = {
            'groups': [],
            'watchlist_users': [],
            'forwarding_destinations': []
        }

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

    def test_root_endpoint(self):
        """Test GET /api/ - Basic connectivity"""
        try:
            response = self.session.get(f"{API_BASE}/")
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'version' in data:
                    self.log_test("Root Endpoint", True, f"API version: {data.get('version')}", data)
                else:
                    self.log_test("Root Endpoint", False, "Missing expected fields in response", data)
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Connection error: {str(e)}")

    def test_bot_connection(self):
        """Test POST /api/test/bot - Telegram bot integration"""
        try:
            response = self.session.post(f"{API_BASE}/test/bot")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'bot_info' in data:
                    bot_info = data['bot_info']
                    self.log_test("Bot Connection Test", True, 
                                f"Bot: @{bot_info.get('username')} (ID: {bot_info.get('id')})", data)
                else:
                    self.log_test("Bot Connection Test", False, "Invalid response format", data)
            else:
                self.log_test("Bot Connection Test", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Bot Connection Test", False, f"Request error: {str(e)}")

    def test_group_management(self):
        """Test Group Management CRUD operations"""
        
        # Test CREATE group
        import random
        unique_id = f"-100{random.randint(1000000000, 9999999999)}"
        test_group_data = {
            "group_id": unique_id,
            "group_name": "Test Monitoring Group",
            "group_type": "supergroup",
            "invite_link": "https://t.me/testgroup",
            "description": "Test group for monitoring system"
        }
        
        try:
            # CREATE
            response = self.session.post(f"{API_BASE}/groups", json=test_group_data)
            
            if response.status_code == 200:
                created_group = response.json()
                group_id = created_group.get('id')
                self.created_resources['groups'].append(group_id)
                self.log_test("Create Group", True, f"Created group with ID: {group_id}", created_group)
                
                # READ - Get all groups
                response = self.session.get(f"{API_BASE}/groups")
                if response.status_code == 200:
                    groups = response.json()
                    self.log_test("List Groups", True, f"Retrieved {len(groups)} groups", len(groups))
                    
                    # READ - Get specific group
                    response = self.session.get(f"{API_BASE}/groups/{group_id}")
                    if response.status_code == 200:
                        group = response.json()
                        self.log_test("Get Specific Group", True, f"Retrieved group: {group.get('group_name')}", group)
                        
                        # UPDATE
                        update_data = {
                            "group_id": test_group_data["group_id"],
                            "group_name": "Updated Test Group",
                            "group_type": "supergroup",
                            "description": "Updated description"
                        }
                        response = self.session.put(f"{API_BASE}/groups/{group_id}", json=update_data)
                        if response.status_code == 200:
                            updated_group = response.json()
                            self.log_test("Update Group", True, f"Updated group name to: {updated_group.get('group_name')}", updated_group)
                        else:
                            self.log_test("Update Group", False, f"HTTP {response.status_code}", response.text)
                            
                        # DELETE
                        response = self.session.delete(f"{API_BASE}/groups/{group_id}")
                        if response.status_code == 200:
                            self.log_test("Delete Group", True, "Group successfully removed from monitoring")
                            self.created_resources['groups'].remove(group_id)
                        else:
                            self.log_test("Delete Group", False, f"HTTP {response.status_code}", response.text)
                    else:
                        self.log_test("Get Specific Group", False, f"HTTP {response.status_code}", response.text)
                else:
                    self.log_test("List Groups", False, f"HTTP {response.status_code}", response.text)
            else:
                self.log_test("Create Group", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Group Management", False, f"Error: {str(e)}")

    def test_watchlist_management(self):
        """Test Watchlist Management CRUD operations"""
        
        test_user_data = {
            "username": "testuser_monitor",
            "user_id": "123456789",
            "full_name": "Test User Monitor",
            "group_ids": [],
            "keywords": ["urgent", "important", "alert"]
        }
        
        try:
            # CREATE
            response = self.session.post(f"{API_BASE}/watchlist", json=test_user_data)
            
            if response.status_code == 200:
                created_user = response.json()
                user_id = created_user.get('id')
                self.created_resources['watchlist_users'].append(user_id)
                self.log_test("Create Watchlist User", True, f"Created user: @{created_user.get('username')}", created_user)
                
                # READ - Get all watchlist users
                response = self.session.get(f"{API_BASE}/watchlist")
                if response.status_code == 200:
                    users = response.json()
                    self.log_test("List Watchlist Users", True, f"Retrieved {len(users)} users", len(users))
                    
                    # READ - Get specific user
                    response = self.session.get(f"{API_BASE}/watchlist/{user_id}")
                    if response.status_code == 200:
                        user = response.json()
                        self.log_test("Get Specific Watchlist User", True, f"Retrieved user: @{user.get('username')}", user)
                        
                        # UPDATE
                        update_data = {
                            "username": "updated_testuser",
                            "user_id": test_user_data["user_id"],
                            "full_name": "Updated Test User",
                            "group_ids": ["-1001234567890"],
                            "keywords": ["critical", "emergency"]
                        }
                        response = self.session.put(f"{API_BASE}/watchlist/{user_id}", json=update_data)
                        if response.status_code == 200:
                            updated_user = response.json()
                            self.log_test("Update Watchlist User", True, f"Updated username to: @{updated_user.get('username')}", updated_user)
                        else:
                            self.log_test("Update Watchlist User", False, f"HTTP {response.status_code}", response.text)
                            
                        # DELETE
                        response = self.session.delete(f"{API_BASE}/watchlist/{user_id}")
                        if response.status_code == 200:
                            self.log_test("Delete Watchlist User", True, "User successfully removed from watchlist")
                            self.created_resources['watchlist_users'].remove(user_id)
                        else:
                            self.log_test("Delete Watchlist User", False, f"HTTP {response.status_code}", response.text)
                    else:
                        self.log_test("Get Specific Watchlist User", False, f"HTTP {response.status_code}", response.text)
                else:
                    self.log_test("List Watchlist Users", False, f"HTTP {response.status_code}", response.text)
            else:
                self.log_test("Create Watchlist User", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Watchlist Management", False, f"Error: {str(e)}")

    def test_message_endpoints(self):
        """Test Message Logs and Search endpoints"""
        
        try:
            # Test GET /api/messages
            response = self.session.get(f"{API_BASE}/messages")
            if response.status_code == 200:
                messages = response.json()
                self.log_test("Get Message Logs", True, f"Retrieved {len(messages)} messages", len(messages))
                
                # Test with query parameters
                response = self.session.get(f"{API_BASE}/messages?limit=10&skip=0")
                if response.status_code == 200:
                    limited_messages = response.json()
                    self.log_test("Get Message Logs with Pagination", True, f"Retrieved {len(limited_messages)} messages with limit", len(limited_messages))
                else:
                    self.log_test("Get Message Logs with Pagination", False, f"HTTP {response.status_code}", response.text)
            else:
                self.log_test("Get Message Logs", False, f"HTTP {response.status_code}", response.text)
            
            # Test GET /api/messages/search
            response = self.session.get(f"{API_BASE}/messages/search?q=test&limit=10")
            if response.status_code == 200:
                search_result = response.json()
                if 'messages' in search_result and 'total' in search_result:
                    self.log_test("Search Messages", True, f"Search returned {search_result.get('total')} total results", search_result)
                else:
                    self.log_test("Search Messages", False, "Invalid search response format", search_result)
            else:
                self.log_test("Search Messages", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Message Endpoints", False, f"Error: {str(e)}")

    def test_statistics_endpoint(self):
        """Test GET /api/stats - System statistics"""
        
        try:
            response = self.session.get(f"{API_BASE}/stats")
            
            if response.status_code == 200:
                stats = response.json()
                expected_fields = ['total_groups', 'total_watchlist_users', 'total_messages', 
                                 'total_forwarded', 'messages_today', 'last_updated']
                
                missing_fields = [field for field in expected_fields if field not in stats]
                
                if not missing_fields:
                    self.log_test("Statistics Endpoint", True, 
                                f"Groups: {stats.get('total_groups')}, Users: {stats.get('total_watchlist_users')}, Messages: {stats.get('total_messages')}", 
                                stats)
                else:
                    self.log_test("Statistics Endpoint", False, f"Missing fields: {missing_fields}", stats)
            else:
                self.log_test("Statistics Endpoint", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Statistics Endpoint", False, f"Error: {str(e)}")

    def test_error_handling(self):
        """Test error handling with invalid inputs"""
        
        # Test invalid group creation
        try:
            invalid_group = {"invalid_field": "test"}
            response = self.session.post(f"{API_BASE}/groups", json=invalid_group)
            if response.status_code >= 400:
                self.log_test("Error Handling - Invalid Group Creation", True, f"Correctly returned HTTP {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid Group Creation", False, f"Should have failed but got HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Invalid Group Creation", False, f"Error: {str(e)}")
        
        # Test non-existent resource access
        try:
            response = self.session.get(f"{API_BASE}/groups/non-existent-id")
            if response.status_code == 404:
                self.log_test("Error Handling - Non-existent Group", True, "Correctly returned 404 for non-existent group")
            else:
                self.log_test("Error Handling - Non-existent Group", False, f"Expected 404 but got HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Non-existent Group", False, f"Error: {str(e)}")
        
        # Test invalid watchlist user creation
        try:
            invalid_user = {"invalid_field": "test"}
            response = self.session.post(f"{API_BASE}/watchlist", json=invalid_user)
            if response.status_code >= 400:
                self.log_test("Error Handling - Invalid Watchlist User", True, f"Correctly returned HTTP {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid Watchlist User", False, f"Should have failed but got HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Invalid Watchlist User", False, f"Error: {str(e)}")

    def cleanup_resources(self):
        """Clean up any created test resources"""
        print("\n🧹 Cleaning up test resources...")
        
        # Clean up groups
        for group_id in self.created_resources['groups']:
            try:
                response = self.session.delete(f"{API_BASE}/groups/{group_id}")
                if response.status_code == 200:
                    print(f"✅ Cleaned up group: {group_id}")
                else:
                    print(f"⚠️  Failed to clean up group: {group_id}")
            except Exception as e:
                print(f"❌ Error cleaning up group {group_id}: {e}")
        
        # Clean up watchlist users
        for user_id in self.created_resources['watchlist_users']:
            try:
                response = self.session.delete(f"{API_BASE}/watchlist/{user_id}")
                if response.status_code == 200:
                    print(f"✅ Cleaned up watchlist user: {user_id}")
                else:
                    print(f"⚠️  Failed to clean up watchlist user: {user_id}")
            except Exception as e:
                print(f"❌ Error cleaning up watchlist user {user_id}: {e}")

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Telegram Bot Backend API Tests")
        print("=" * 60)
        
        # Run tests in logical order
        self.test_root_endpoint()
        self.test_bot_connection()
        self.test_group_management()
        self.test_watchlist_management()
        self.test_message_endpoints()
        self.test_statistics_endpoint()
        self.test_error_handling()
        
        # Cleanup
        self.cleanup_resources()
        
        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test['success']:
                    print(f"  • {test['test']}: {test['details']}")
        
        print("\n" + "=" * 60)
        
        # Return summary for programmatic use
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'results': self.test_results
        }

if __name__ == "__main__":
    tester = TelegramBotAPITester()
    try:
        summary = tester.run_all_tests()
        # Exit with appropriate code
        exit(0 if summary and summary['failed'] == 0 else 1)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        exit(1)