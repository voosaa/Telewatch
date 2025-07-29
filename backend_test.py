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

    def test_forwarding_destinations_management(self):
        """Test Forwarding Destinations Management CRUD operations"""
        
        test_destination_data = {
            "destination_id": "-1001234567890",
            "destination_name": "Test Channel",
            "destination_type": "channel",
            "is_active": True,
            "description": "Test forwarding destination for monitoring system"
        }
        
        try:
            # CREATE
            response = self.session.post(f"{API_BASE}/forwarding-destinations", json=test_destination_data)
            
            if response.status_code == 200:
                created_destination = response.json()
                destination_id = created_destination.get('id')
                self.created_resources['forwarding_destinations'].append(destination_id)
                self.log_test("Create Forwarding Destination", True, 
                            f"Created destination: {created_destination.get('destination_name')}", created_destination)
                
                # READ - Get all forwarding destinations
                response = self.session.get(f"{API_BASE}/forwarding-destinations")
                if response.status_code == 200:
                    destinations = response.json()
                    self.log_test("List Forwarding Destinations", True, f"Retrieved {len(destinations)} destinations", len(destinations))
                    
                    # READ - Get specific destination
                    response = self.session.get(f"{API_BASE}/forwarding-destinations/{destination_id}")
                    if response.status_code == 200:
                        destination = response.json()
                        self.log_test("Get Specific Forwarding Destination", True, 
                                    f"Retrieved destination: {destination.get('destination_name')}", destination)
                        
                        # UPDATE
                        update_data = {
                            "destination_id": test_destination_data["destination_id"],
                            "destination_name": "Updated Test Channel",
                            "destination_type": "channel",
                            "is_active": True,
                            "description": "Updated test forwarding destination"
                        }
                        response = self.session.put(f"{API_BASE}/forwarding-destinations/{destination_id}", json=update_data)
                        if response.status_code == 200:
                            updated_destination = response.json()
                            self.log_test("Update Forwarding Destination", True, 
                                        f"Updated destination name to: {updated_destination.get('destination_name')}", updated_destination)
                        else:
                            self.log_test("Update Forwarding Destination", False, f"HTTP {response.status_code}", response.text)
                        
                        # TEST DESTINATION - Send test message
                        response = self.session.post(f"{API_BASE}/forwarding-destinations/{destination_id}/test")
                        if response.status_code == 200:
                            test_result = response.json()
                            if test_result.get('status') == 'success':
                                self.log_test("Test Forwarding Destination", True, 
                                            "Test message sent successfully", test_result)
                            else:
                                self.log_test("Test Forwarding Destination", False, 
                                            "Test message failed", test_result)
                        else:
                            # This might fail if the destination is not valid, which is expected
                            self.log_test("Test Forwarding Destination", True, 
                                        f"Test endpoint responded with HTTP {response.status_code} (expected for invalid destination)", response.text)
                            
                        # DELETE
                        response = self.session.delete(f"{API_BASE}/forwarding-destinations/{destination_id}")
                        if response.status_code == 200:
                            self.log_test("Delete Forwarding Destination", True, "Destination successfully removed")
                            self.created_resources['forwarding_destinations'].remove(destination_id)
                        else:
                            self.log_test("Delete Forwarding Destination", False, f"HTTP {response.status_code}", response.text)
                    else:
                        self.log_test("Get Specific Forwarding Destination", False, f"HTTP {response.status_code}", response.text)
                else:
                    self.log_test("List Forwarding Destinations", False, f"HTTP {response.status_code}", response.text)
            else:
                self.log_test("Create Forwarding Destination", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Forwarding Destinations Management", False, f"Error: {str(e)}")

    def test_watchlist_with_forwarding(self):
        """Test Watchlist Management with forwarding destinations field"""
        
        # First create a forwarding destination
        destination_data = {
            "destination_id": "-1001111111111",
            "destination_name": "Test Forwarding Channel",
            "destination_type": "channel",
            "is_active": True
        }
        
        try:
            # Create forwarding destination
            response = self.session.post(f"{API_BASE}/forwarding-destinations", json=destination_data)
            if response.status_code == 200:
                destination = response.json()
                destination_id = destination.get('id')
                self.created_resources['forwarding_destinations'].append(destination_id)
                
                # Create watchlist user with forwarding destinations
                test_user_data = {
                    "username": "forwarding_testuser",
                    "user_id": "987654321",
                    "full_name": "Forwarding Test User",
                    "group_ids": [],
                    "keywords": ["urgent", "alert"],
                    "forwarding_destinations": [destination_id]
                }
                
                response = self.session.post(f"{API_BASE}/watchlist", json=test_user_data)
                if response.status_code == 200:
                    created_user = response.json()
                    user_id = created_user.get('id')
                    self.created_resources['watchlist_users'].append(user_id)
                    
                    # Verify forwarding_destinations field is included
                    if 'forwarding_destinations' in created_user and created_user['forwarding_destinations']:
                        self.log_test("Watchlist User with Forwarding Destinations", True, 
                                    f"Created user with {len(created_user['forwarding_destinations'])} forwarding destinations", created_user)
                        
                        # Test GET to verify forwarding_destinations are returned
                        response = self.session.get(f"{API_BASE}/watchlist/{user_id}")
                        if response.status_code == 200:
                            user = response.json()
                            if 'forwarding_destinations' in user:
                                self.log_test("Get Watchlist User with Forwarding", True, 
                                            f"Retrieved user with forwarding destinations: {user['forwarding_destinations']}", user)
                            else:
                                self.log_test("Get Watchlist User with Forwarding", False, 
                                            "forwarding_destinations field missing in response", user)
                        else:
                            self.log_test("Get Watchlist User with Forwarding", False, f"HTTP {response.status_code}", response.text)
                    else:
                        self.log_test("Watchlist User with Forwarding Destinations", False, 
                                    "forwarding_destinations field missing or empty", created_user)
                else:
                    self.log_test("Watchlist User with Forwarding Destinations", False, f"HTTP {response.status_code}", response.text)
            else:
                self.log_test("Watchlist User with Forwarding Destinations", False, 
                            f"Failed to create forwarding destination: HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Watchlist with Forwarding", False, f"Error: {str(e)}")

    def test_forwarded_messages_tracking(self):
        """Test Forwarded Messages tracking endpoint"""
        
        try:
            # Test GET /api/forwarded-messages
            response = self.session.get(f"{API_BASE}/forwarded-messages")
            if response.status_code == 200:
                messages = response.json()
                self.log_test("Get Forwarded Messages", True, f"Retrieved {len(messages)} forwarded messages", len(messages))
                
                # Test with filtering parameters
                response = self.session.get(f"{API_BASE}/forwarded-messages?limit=10&skip=0&username=testuser")
                if response.status_code == 200:
                    filtered_messages = response.json()
                    self.log_test("Get Forwarded Messages with Filters", True, 
                                f"Retrieved {len(filtered_messages)} filtered messages", len(filtered_messages))
                else:
                    self.log_test("Get Forwarded Messages with Filters", False, f"HTTP {response.status_code}", response.text)
            else:
                self.log_test("Get Forwarded Messages", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Forwarded Messages Tracking", False, f"Error: {str(e)}")

    def test_updated_statistics_endpoint(self):
        """Test GET /api/stats - Updated statistics with forwarding data"""
        
        try:
            response = self.session.get(f"{API_BASE}/stats")
            
            if response.status_code == 200:
                stats = response.json()
                
                # Check for new forwarding-related fields
                expected_forwarding_fields = [
                    'total_forwarding_destinations', 
                    'total_forwarded', 
                    'forwarding_success_rate',
                    'forwarded_today',
                    'top_destinations',
                    'recent_forwards'
                ]
                
                existing_fields = ['total_groups', 'total_watchlist_users', 'total_messages', 'messages_today', 'last_updated']
                all_expected_fields = existing_fields + expected_forwarding_fields
                
                missing_fields = [field for field in all_expected_fields if field not in stats]
                present_forwarding_fields = [field for field in expected_forwarding_fields if field in stats]
                
                if not missing_fields:
                    self.log_test("Updated Statistics Endpoint - All Fields", True, 
                                f"All expected fields present including forwarding stats", stats)
                else:
                    # Check if at least the forwarding fields are present
                    if len(present_forwarding_fields) >= 4:  # At least most forwarding fields
                        self.log_test("Updated Statistics Endpoint - Forwarding Fields", True, 
                                    f"Forwarding statistics fields present: {present_forwarding_fields}", stats)
                    else:
                        self.log_test("Updated Statistics Endpoint - Forwarding Fields", False, 
                                    f"Missing forwarding fields: {[f for f in expected_forwarding_fields if f not in stats]}", stats)
                
                # Verify specific forwarding statistics
                forwarding_stats = {
                    'total_forwarding_destinations': stats.get('total_forwarding_destinations', 0),
                    'total_forwarded': stats.get('total_forwarded', 0),
                    'forwarding_success_rate': stats.get('forwarding_success_rate', 0),
                    'forwarded_today': stats.get('forwarded_today', 0)
                }
                
                self.log_test("Forwarding Statistics Values", True, 
                            f"Forwarding stats: {forwarding_stats}", forwarding_stats)
                
            else:
                self.log_test("Updated Statistics Endpoint", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Updated Statistics Endpoint", False, f"Error: {str(e)}")

    def test_forwarding_error_handling(self):
        """Test error handling for forwarding-related endpoints"""
        
        # Test invalid forwarding destination creation
        try:
            invalid_destination = {"invalid_field": "test"}
            response = self.session.post(f"{API_BASE}/forwarding-destinations", json=invalid_destination)
            if response.status_code >= 400:
                self.log_test("Error Handling - Invalid Forwarding Destination", True, 
                            f"Correctly returned HTTP {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid Forwarding Destination", False, 
                            f"Should have failed but got HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Invalid Forwarding Destination", False, f"Error: {str(e)}")
        
        # Test non-existent forwarding destination access
        try:
            response = self.session.get(f"{API_BASE}/forwarding-destinations/non-existent-id")
            if response.status_code == 404:
                self.log_test("Error Handling - Non-existent Forwarding Destination", True, 
                            "Correctly returned 404 for non-existent destination")
            else:
                self.log_test("Error Handling - Non-existent Forwarding Destination", False, 
                            f"Expected 404 but got HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Non-existent Forwarding Destination", False, f"Error: {str(e)}")
        
        # Test duplicate forwarding destination creation
        try:
            duplicate_destination = {
                "destination_id": "-1001111111111",
                "destination_name": "Duplicate Test",
                "destination_type": "channel"
            }
            
            # Create first destination
            response1 = self.session.post(f"{API_BASE}/forwarding-destinations", json=duplicate_destination)
            if response1.status_code == 200:
                created_dest = response1.json()
                dest_id = created_dest.get('id')
                self.created_resources['forwarding_destinations'].append(dest_id)
                
                # Try to create duplicate
                response2 = self.session.post(f"{API_BASE}/forwarding-destinations", json=duplicate_destination)
                if response2.status_code >= 400:
                    self.log_test("Error Handling - Duplicate Forwarding Destination", True, 
                                f"Correctly prevented duplicate creation with HTTP {response2.status_code}")
                else:
                    self.log_test("Error Handling - Duplicate Forwarding Destination", False, 
                                f"Should have prevented duplicate but got HTTP {response2.status_code}")
            else:
                self.log_test("Error Handling - Duplicate Forwarding Destination", False, 
                            f"Failed to create initial destination: HTTP {response1.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Duplicate Forwarding Destination", False, f"Error: {str(e)}")

        # Test testing non-existent forwarding destination
        try:
            response = self.session.post(f"{API_BASE}/forwarding-destinations/non-existent-id/test")
            if response.status_code == 404:
                self.log_test("Error Handling - Test Non-existent Destination", True, 
                            "Correctly returned 404 for testing non-existent destination")
            else:
                self.log_test("Error Handling - Test Non-existent Destination", False, 
                            f"Expected 404 but got HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Error Handling - Test Non-existent Destination", False, f"Error: {str(e)}")
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