#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Subscription Management
Tests organization plan management functionality.
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

print(f"Testing subscription management API at: {API_BASE}")

class SubscriptionManagementTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_resources = {
            'users': [],
            'organizations': []
        }
        self.auth_token = None
        self.test_user_data = None

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

    def setup_authentication(self):
        """Setup authentication for testing protected endpoints"""
        import random
        import time
        
        # Create unique test user and organization
        timestamp = int(time.time())
        random_suffix = random.randint(1000, 9999)
        
        self.test_user_data = {
            "email": f"testuser_{timestamp}_{random_suffix}@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User for Subscription Management",
            "organization_name": f"Test Organization {timestamp}"
        }
        
        try:
            # Register user
            response = self.session.post(f"{API_BASE}/auth/register", json=self.test_user_data)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get('access_token')
                user_info = auth_data.get('user')
                
                # Set authorization header for future requests
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                
                self.log_test("Authentication Setup", True, 
                            f"Created user: {user_info.get('email')} in org: {self.test_user_data['organization_name']}", 
                            {"user_id": user_info.get('id'), "org_id": user_info.get('organization_id')})
                
                # Store for cleanup
                self.created_resources['users'].append(user_info.get('id'))
                self.created_resources['organizations'].append(user_info.get('organization_id'))
                
                return True
            else:
                self.log_test("Authentication Setup", False, f"Registration failed: HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Authentication Setup", False, f"Error: {str(e)}")
            return False

    def test_organization_current_get(self):
        """Test GET /api/organizations/current - Should return organization with plan field"""
        try:
            response = self.session.get(f"{API_BASE}/organizations/current")
            
            if response.status_code == 200:
                org_data = response.json()
                
                # Check required fields
                required_fields = ['id', 'name', 'plan', 'is_active', 'created_at']
                missing_fields = [field for field in required_fields if field not in org_data]
                
                if not missing_fields:
                    # Verify plan field has valid value
                    plan = org_data.get('plan')
                    valid_plans = ['free', 'pro', 'enterprise']
                    
                    if plan in valid_plans:
                        self.log_test("GET Current Organization", True, 
                                    f"Organization retrieved with plan: {plan}", org_data)
                    else:
                        self.log_test("GET Current Organization", False, 
                                    f"Invalid plan value: {plan}. Expected one of: {valid_plans}", org_data)
                else:
                    self.log_test("GET Current Organization", False, 
                                f"Missing required fields: {missing_fields}", org_data)
            else:
                self.log_test("GET Current Organization", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("GET Current Organization", False, f"Error: {str(e)}")

    def test_organization_plan_updates(self):
        """Test updating organization plan from free to pro to enterprise and back"""
        
        # Test plan updates in sequence
        plan_sequence = [
            ("pro", "Upgrade from free to pro"),
            ("enterprise", "Upgrade from pro to enterprise"), 
            ("free", "Downgrade from enterprise to free"),
            ("pro", "Upgrade from free to pro again")
        ]
        
        for target_plan, description in plan_sequence:
            try:
                update_data = {
                    "name": self.test_user_data['organization_name'],
                    "description": f"Updated organization - {description}",
                    "plan": target_plan
                }
                
                response = self.session.put(f"{API_BASE}/organizations/current", json=update_data)
                
                if response.status_code == 200:
                    updated_org = response.json()
                    actual_plan = updated_org.get('plan')
                    
                    if actual_plan == target_plan:
                        self.log_test(f"Update Organization Plan to {target_plan.upper()}", True, 
                                    f"{description} successful", updated_org)
                    else:
                        self.log_test(f"Update Organization Plan to {target_plan.upper()}", False, 
                                    f"Plan not updated correctly. Expected: {target_plan}, Got: {actual_plan}", updated_org)
                else:
                    self.log_test(f"Update Organization Plan to {target_plan.upper()}", False, 
                                f"HTTP {response.status_code}", response.text)
                    
            except Exception as e:
                self.log_test(f"Update Organization Plan to {target_plan.upper()}", False, f"Error: {str(e)}")

    def test_organization_plan_validation(self):
        """Test that only valid plan values are accepted and invalid ones are rejected"""
        
        # Test invalid plan values
        invalid_plans = ["basic", "premium", "invalid", "FREE", "PRO", "ENTERPRISE", ""]
        
        for invalid_plan in invalid_plans:
            try:
                update_data = {
                    "name": self.test_user_data['organization_name'],
                    "description": "Testing invalid plan validation",
                    "plan": invalid_plan
                }
                
                response = self.session.put(f"{API_BASE}/organizations/current", json=update_data)
                
                if response.status_code >= 400:  # Should be rejected
                    self.log_test(f"Plan Validation - Reject '{invalid_plan}'", True, 
                                f"Correctly rejected invalid plan with HTTP {response.status_code}")
                else:
                    self.log_test(f"Plan Validation - Reject '{invalid_plan}'", False, 
                                f"Should have rejected invalid plan but got HTTP {response.status_code}", response.json())
                    
            except Exception as e:
                self.log_test(f"Plan Validation - Reject '{invalid_plan}'", False, f"Error: {str(e)}")

    def test_organization_authentication_required(self):
        """Test that organization endpoints require authentication"""
        
        # Save current auth header
        auth_header = self.session.headers.get('Authorization')
        
        try:
            # Remove auth header
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            
            # Test GET without auth
            response = self.session.get(f"{API_BASE}/organizations/current")
            if response.status_code == 403:
                self.log_test("Organization GET - Auth Required", True, 
                            "Correctly rejected unauthenticated request with HTTP 403")
            else:
                self.log_test("Organization GET - Auth Required", False, 
                            f"Expected HTTP 403 but got {response.status_code}")
            
            # Test PUT without auth
            update_data = {
                "name": "Test Org",
                "description": "Test",
                "plan": "pro"
            }
            response = self.session.put(f"{API_BASE}/organizations/current", json=update_data)
            if response.status_code == 403:
                self.log_test("Organization PUT - Auth Required", True, 
                            "Correctly rejected unauthenticated request with HTTP 403")
            else:
                self.log_test("Organization PUT - Auth Required", False, 
                            f"Expected HTTP 403 but got {response.status_code}")
                
        except Exception as e:
            self.log_test("Organization Authentication Required", False, f"Error: {str(e)}")
        finally:
            # Restore auth header
            if auth_header:
                self.session.headers['Authorization'] = auth_header

    def test_organization_admin_permissions(self):
        """Test that organization updates require admin/owner permissions"""
        
        # This test assumes the current user is an owner (created during registration)
        # In a full test suite, we would create a viewer user and test with that
        
        try:
            # Test that owner can update organization
            update_data = {
                "name": f"{self.test_user_data['organization_name']} - Admin Test",
                "description": "Testing admin permissions",
                "plan": "pro"
            }
            
            response = self.session.put(f"{API_BASE}/organizations/current", json=update_data)
            
            if response.status_code == 200:
                self.log_test("Organization Update - Owner Permission", True, 
                            "Owner successfully updated organization", response.json())
            else:
                self.log_test("Organization Update - Owner Permission", False, 
                            f"Owner should be able to update organization but got HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Organization Admin Permissions", False, f"Error: {str(e)}")

    def test_organization_data_integrity(self):
        """Test that organization data integrity is maintained after plan updates"""
        
        try:
            # Get initial organization state
            response = self.session.get(f"{API_BASE}/organizations/current")
            if response.status_code != 200:
                self.log_test("Organization Data Integrity", False, "Could not get initial organization state")
                return
            
            initial_org = response.json()
            initial_id = initial_org.get('id')
            initial_name = initial_org.get('name')
            initial_created_at = initial_org.get('created_at')
            
            # Update plan multiple times
            plans_to_test = ['pro', 'enterprise', 'free']
            
            for plan in plans_to_test:
                update_data = {
                    "name": initial_name,
                    "description": f"Data integrity test - plan {plan}",
                    "plan": plan
                }
                
                response = self.session.put(f"{API_BASE}/organizations/current", json=update_data)
                if response.status_code != 200:
                    self.log_test("Organization Data Integrity", False, 
                                f"Failed to update to plan {plan}")
                    return
                
                updated_org = response.json()
                
                # Verify critical fields remain unchanged
                if (updated_org.get('id') != initial_id or 
                    updated_org.get('created_at') != initial_created_at):
                    self.log_test("Organization Data Integrity", False, 
                                f"Critical fields changed during plan update to {plan}", 
                                {"initial": initial_org, "updated": updated_org})
                    return
                
                # Verify plan was updated correctly
                if updated_org.get('plan') != plan:
                    self.log_test("Organization Data Integrity", False, 
                                f"Plan not updated correctly to {plan}")
                    return
            
            self.log_test("Organization Data Integrity", True, 
                        "Organization data integrity maintained through all plan updates", 
                        {"tested_plans": plans_to_test})
                
        except Exception as e:
            self.log_test("Organization Data Integrity", False, f"Error: {str(e)}")

    def test_subscription_management_comprehensive(self):
        """Comprehensive test of subscription management functionality"""
        
        try:
            # Test complete workflow
            workflow_steps = [
                ("Get initial organization", "GET", f"{API_BASE}/organizations/current", None),
                ("Update to Pro plan", "PUT", f"{API_BASE}/organizations/current", {
                    "name": self.test_user_data['organization_name'],
                    "description": "Upgraded to Pro plan",
                    "plan": "pro"
                }),
                ("Verify Pro plan", "GET", f"{API_BASE}/organizations/current", None),
                ("Update to Enterprise plan", "PUT", f"{API_BASE}/organizations/current", {
                    "name": self.test_user_data['organization_name'], 
                    "description": "Upgraded to Enterprise plan",
                    "plan": "enterprise"
                }),
                ("Verify Enterprise plan", "GET", f"{API_BASE}/organizations/current", None),
                ("Downgrade to Free plan", "PUT", f"{API_BASE}/organizations/current", {
                    "name": self.test_user_data['organization_name'],
                    "description": "Downgraded to Free plan", 
                    "plan": "free"
                }),
                ("Verify Free plan", "GET", f"{API_BASE}/organizations/current", None)
            ]
            
            workflow_results = []
            
            for step_name, method, url, data in workflow_steps:
                if method == "GET":
                    response = self.session.get(url)
                elif method == "PUT":
                    response = self.session.put(url, json=data)
                
                if response.status_code == 200:
                    result_data = response.json()
                    workflow_results.append({
                        "step": step_name,
                        "success": True,
                        "plan": result_data.get('plan'),
                        "data": result_data
                    })
                else:
                    workflow_results.append({
                        "step": step_name,
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "response": response.text
                    })
                    break
            
            # Check if all steps succeeded
            all_success = all(step["success"] for step in workflow_results)
            
            if all_success:
                # Verify plan progression
                expected_plans = [None, "pro", "pro", "enterprise", "enterprise", "free", "free"]
                actual_plans = [step.get("plan") for step in workflow_results]
                
                plans_match = True
                for i, expected in enumerate(expected_plans):
                    if expected and actual_plans[i] != expected:
                        plans_match = False
                        break
                
                if plans_match:
                    self.log_test("Subscription Management Comprehensive Workflow", True, 
                                "Complete subscription management workflow successful", workflow_results)
                else:
                    self.log_test("Subscription Management Comprehensive Workflow", False, 
                                f"Plan progression incorrect. Expected: {expected_plans}, Got: {actual_plans}", workflow_results)
            else:
                failed_step = next(step for step in workflow_results if not step["success"])
                self.log_test("Subscription Management Comprehensive Workflow", False, 
                            f"Workflow failed at step: {failed_step['step']}", workflow_results)
                
        except Exception as e:
            self.log_test("Subscription Management Comprehensive Workflow", False, f"Error: {str(e)}")

    def cleanup_auth_resources(self):
        """Clean up authentication-related test resources"""
        print("\n🧹 Cleaning up authentication resources...")
        
        # Note: In a real scenario, we might want to clean up users and organizations
        # For now, we'll just log that cleanup would happen here
        if self.created_resources['users']:
            print(f"ℹ️  Created {len(self.created_resources['users'])} test users (cleanup not implemented)")
        
        if self.created_resources['organizations']:
            print(f"ℹ️  Created {len(self.created_resources['organizations'])} test organizations (cleanup not implemented)")
        
        # Remove auth header
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
            print("✅ Removed authentication header")

    def run_all_tests(self):
        """Run all subscription management tests"""
        print("🚀 Starting Subscription Management Backend API Tests")
        print("=" * 60)
        
        # Setup authentication first
        if not self.setup_authentication():
            print("❌ Authentication setup failed. Cannot proceed with tests.")
            return
        
        # Run subscription management tests
        self.test_organization_current_get()
        self.test_organization_plan_updates()
        self.test_organization_plan_validation()
        self.test_organization_authentication_required()
        self.test_organization_admin_permissions()
        self.test_organization_data_integrity()
        self.test_subscription_management_comprehensive()
        
        # Cleanup
        self.cleanup_auth_resources()
        
        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 SUBSCRIPTION MANAGEMENT TEST SUMMARY")
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
    tester = SubscriptionManagementTester()
    try:
        summary = tester.run_all_tests()
        # Exit with appropriate code
        exit(0 if summary and summary['failed'] == 0 else 1)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        exit(1)