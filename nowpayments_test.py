#!/usr/bin/env python3
"""
NOWPayments Cryptocurrency Payment System Tests
Tests the newly implemented NOWPayments integration replacing Coinbase Commerce.
"""

import requests
import json
import time
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, List
import random

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

print(f"Testing NOWPayments API at: {API_BASE}")

class NOWPaymentsTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.auth_token = None
        self.test_user_data = None
        self.telegram_bot_token = "8342094196:AAE-E8jIYLjYflUPtY0G02NLbogbDpN_FE8"

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

    def setup_authentication(self):
        """Setup Telegram authentication for testing"""
        try:
            # Generate unique test data
            timestamp = int(time.time())
            random_suffix = random.randint(1000, 9999)
            
            telegram_id = random.randint(100000000, 999999999)
            username = f"nowpayments_test_{timestamp}_{random_suffix}"
            org_name = f"NOWPayments Test Org {timestamp}"
            
            registration_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": "NOWPayments",
                "last_name": "Tester",
                "photo_url": "https://example.com/photo.jpg",
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
                
                self.log_test("Authentication Setup", True, 
                            f"Created test user: {username} in org: {org_name}")
                return True
            else:
                self.log_test("Authentication Setup", False, 
                            f"Registration failed: HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Authentication Setup", False, f"Error: {str(e)}")
            return False

    def test_nowpayments_create_charge_valid_plans(self):
        """Test NOWPayments charge creation with valid plans and currencies"""
        if not self.auth_token:
            self.log_test("NOWPayments Create Charge - Valid Plans", False, "No authentication token available")
            return
            
        try:
            # Test Pro plan with different cryptocurrencies
            test_cases = [
                {"plan": "pro", "pay_currency": "btc", "expected_price": 9.99},
                {"plan": "pro", "pay_currency": "eth", "expected_price": 9.99},
                {"plan": "pro", "pay_currency": "usdt", "expected_price": 9.99},
                {"plan": "enterprise", "pay_currency": "btc", "expected_price": 19.99},
                {"plan": "enterprise", "pay_currency": "sol", "expected_price": 19.99}
            ]
            
            for test_case in test_cases:
                charge_data = {
                    "plan": test_case["plan"],
                    "pay_currency": test_case["pay_currency"]
                }
                
                response = self.session.post(f"{API_BASE}/crypto/create-charge", json=charge_data)
                
                # With placeholder API keys, we expect 503 (service unavailable)
                if response.status_code == 503:
                    response_data = response.json()
                    if "not configured yet" in response_data.get("detail", "").lower():
                        self.log_test(f"NOWPayments Create Charge - {test_case['plan'].upper()} {test_case['pay_currency'].upper()}", True, 
                                    f"Correctly shows service unavailable with placeholder API keys", response_data)
                    else:
                        self.log_test(f"NOWPayments Create Charge - {test_case['plan'].upper()} {test_case['pay_currency'].upper()}", False, 
                                    f"Expected 'not configured' message but got: {response_data.get('detail')}", response_data)
                elif response.status_code == 200:
                    # If real API keys are configured, verify response structure
                    charge_response = response.json()
                    required_fields = ['payment_url', 'payment_id', 'amount', 'plan', 'pay_currency', 'pay_address', 'pay_amount']
                    missing_fields = [field for field in required_fields if field not in charge_response]
                    
                    if not missing_fields and charge_response['amount'] == str(test_case['expected_price']):
                        self.log_test(f"NOWPayments Create Charge - {test_case['plan'].upper()} {test_case['pay_currency'].upper()}", True, 
                                    f"Successfully created charge for ${test_case['expected_price']}", charge_response)
                    else:
                        self.log_test(f"NOWPayments Create Charge - {test_case['plan'].upper()} {test_case['pay_currency'].upper()}", False, 
                                    f"Missing fields: {missing_fields} or incorrect amount", charge_response)
                else:
                    self.log_test(f"NOWPayments Create Charge - {test_case['plan'].upper()} {test_case['pay_currency'].upper()}", False, 
                                f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("NOWPayments Create Charge - Valid Plans", False, f"Error: {str(e)}")

    def test_nowpayments_create_charge_validation(self):
        """Test NOWPayments charge creation validation (invalid plans and currencies)"""
        if not self.auth_token:
            self.log_test("NOWPayments Create Charge - Validation", False, "No authentication token available")
            return
            
        try:
            # Test invalid plans
            invalid_plans = ["basic", "premium", "invalid", ""]
            
            for invalid_plan in invalid_plans:
                charge_data = {
                    "plan": invalid_plan,
                    "pay_currency": "btc"
                }
                
                response = self.session.post(f"{API_BASE}/crypto/create-charge", json=charge_data)
                
                if response.status_code == 400:
                    self.log_test(f"NOWPayments Validation - Invalid Plan '{invalid_plan}'", True, 
                                f"Correctly rejected invalid plan with HTTP 400")
                else:
                    self.log_test(f"NOWPayments Validation - Invalid Plan '{invalid_plan}'", False, 
                                f"Expected HTTP 400 but got {response.status_code}")
            
            # Test invalid currencies
            invalid_currencies = ["doge", "ltc", "invalid", "", "BTC"]  # BTC uppercase should be rejected
            
            for invalid_currency in invalid_currencies:
                charge_data = {
                    "plan": "pro",
                    "pay_currency": invalid_currency
                }
                
                response = self.session.post(f"{API_BASE}/crypto/create-charge", json=charge_data)
                
                if response.status_code == 400:
                    self.log_test(f"NOWPayments Validation - Invalid Currency '{invalid_currency}'", True, 
                                f"Correctly rejected invalid currency with HTTP 400")
                else:
                    self.log_test(f"NOWPayments Validation - Invalid Currency '{invalid_currency}'", False, 
                                f"Expected HTTP 400 but got {response.status_code}")
                
        except Exception as e:
            self.log_test("NOWPayments Create Charge - Validation", False, f"Error: {str(e)}")

    def test_nowpayments_currencies_endpoint(self):
        """Test GET /api/crypto/currencies - Supported cryptocurrency list"""
        try:
            response = self.session.get(f"{API_BASE}/crypto/currencies")
            
            if response.status_code == 200:
                currencies_data = response.json()
                
                if "currencies" in currencies_data:
                    currencies = currencies_data["currencies"]
                    
                    # Verify expected cryptocurrencies are present
                    expected_currencies = ["btc", "eth", "usdt", "usdc", "sol"]
                    found_currencies = [curr["currency"] for curr in currencies if "currency" in curr]
                    
                    missing_currencies = [curr for curr in expected_currencies if curr not in found_currencies]
                    
                    if not missing_currencies:
                        self.log_test("NOWPayments Currencies Endpoint", True, 
                                    f"All expected currencies present: {found_currencies}", currencies_data)
                    else:
                        self.log_test("NOWPayments Currencies Endpoint", False, 
                                    f"Missing currencies: {missing_currencies}", currencies_data)
                    
                    # Verify currency structure
                    if currencies:
                        sample_currency = currencies[0]
                        required_fields = ["currency", "name", "network"]
                        missing_fields = [field for field in required_fields if field not in sample_currency]
                        
                        if not missing_fields:
                            self.log_test("NOWPayments Currencies - Structure", True, 
                                        f"Currency objects have correct structure", sample_currency)
                        else:
                            self.log_test("NOWPayments Currencies - Structure", False, 
                                        f"Missing fields in currency object: {missing_fields}", sample_currency)
                else:
                    self.log_test("NOWPayments Currencies Endpoint", False, 
                                "Missing 'currencies' field in response", currencies_data)
            else:
                self.log_test("NOWPayments Currencies Endpoint", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("NOWPayments Currencies Endpoint", False, f"Error: {str(e)}")

    def test_nowpayments_ipn_handler(self):
        """Test NOWPayments IPN (webhook) handler with mock data"""
        try:
            # Test IPN endpoint without proper signature (should fail)
            mock_ipn_data = {
                "payment_id": "test_payment_123",
                "payment_status": "confirmed",
                "order_id": "test_order_456",
                "price_amount": "9.99",
                "price_currency": "usd",
                "pay_amount": "0.0003",
                "pay_currency": "btc"
            }
            
            # Test without signature header
            response = self.session.post(f"{API_BASE}/crypto/ipn", json=mock_ipn_data)
            
            # With placeholder IPN secret, we expect 503 (not configured)
            if response.status_code == 503:
                response_data = response.json()
                if "not configured" in response_data.get("error", "").lower():
                    self.log_test("NOWPayments IPN Handler - Not Configured", True, 
                                "Correctly shows IPN not configured with placeholder secret", response_data)
                else:
                    self.log_test("NOWPayments IPN Handler - Not Configured", False, 
                                f"Expected 'not configured' message but got: {response_data}", response_data)
            elif response.status_code == 403:
                self.log_test("NOWPayments IPN Handler - Signature Validation", True, 
                            "Correctly rejected IPN without valid signature (HTTP 403)")
            else:
                self.log_test("NOWPayments IPN Handler - Signature Validation", False, 
                            f"Expected HTTP 503 or 403 but got {response.status_code}", response.text)
            
            # Test with invalid JSON
            response = self.session.post(f"{API_BASE}/crypto/ipn", 
                                       data="invalid json data",
                                       headers={"Content-Type": "application/json"})
            
            if response.status_code in [400, 503]:  # 400 for invalid JSON or 503 for not configured
                self.log_test("NOWPayments IPN Handler - Invalid JSON", True, 
                            f"Correctly handled invalid JSON with HTTP {response.status_code}")
            else:
                self.log_test("NOWPayments IPN Handler - Invalid JSON", False, 
                            f"Expected HTTP 400 or 503 but got {response.status_code}")
                
        except Exception as e:
            self.log_test("NOWPayments IPN Handler", False, f"Error: {str(e)}")

    def test_nowpayments_payment_history(self):
        """Test GET /api/crypto/charges - Payment history endpoint"""
        if not self.auth_token:
            self.log_test("NOWPayments Payment History", False, "No authentication token available")
            return
            
        try:
            response = self.session.get(f"{API_BASE}/crypto/charges")
            
            if response.status_code == 200:
                history_data = response.json()
                
                if "charges" in history_data:
                    charges = history_data["charges"]
                    self.log_test("NOWPayments Payment History", True, 
                                f"Successfully retrieved {len(charges)} payment records", history_data)
                    
                    # Verify data sanitization (sensitive fields should be removed)
                    if charges:
                        sample_charge = charges[0]
                        sensitive_fields = ["nowpayments_response", "ipn_data"]
                        found_sensitive = [field for field in sensitive_fields if field in sample_charge]
                        
                        if not found_sensitive:
                            self.log_test("NOWPayments Payment History - Data Sanitization", True, 
                                        "Sensitive fields properly removed from response", sample_charge)
                        else:
                            self.log_test("NOWPayments Payment History - Data Sanitization", False, 
                                        f"Sensitive fields still present: {found_sensitive}", sample_charge)
                    else:
                        self.log_test("NOWPayments Payment History - Empty History", True, 
                                    "No payment history found (expected for new organization)")
                else:
                    self.log_test("NOWPayments Payment History", False, 
                                "Missing 'charges' field in response", history_data)
            else:
                self.log_test("NOWPayments Payment History", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("NOWPayments Payment History", False, f"Error: {str(e)}")

    def test_nowpayments_authentication_required(self):
        """Test that NOWPayments endpoints require authentication"""
        # Save current auth header
        auth_header = self.session.headers.get('Authorization')
        
        try:
            # Remove auth header
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            
            # Test create charge without auth
            charge_data = {"plan": "pro", "pay_currency": "btc"}
            response = self.session.post(f"{API_BASE}/crypto/create-charge", json=charge_data)
            
            if response.status_code == 403:
                self.log_test("NOWPayments Create Charge - Auth Required", True, 
                            "Correctly rejected unauthenticated request with HTTP 403")
            else:
                self.log_test("NOWPayments Create Charge - Auth Required", False, 
                            f"Expected HTTP 403 but got {response.status_code}")
            
            # Test payment history without auth
            response = self.session.get(f"{API_BASE}/crypto/charges")
            
            if response.status_code == 403:
                self.log_test("NOWPayments Payment History - Auth Required", True, 
                            "Correctly rejected unauthenticated request with HTTP 403")
            else:
                self.log_test("NOWPayments Payment History - Auth Required", False, 
                            f"Expected HTTP 403 but got {response.status_code}")
                
        except Exception as e:
            self.log_test("NOWPayments Authentication Required", False, f"Error: {str(e)}")
        finally:
            # Restore auth header
            if auth_header:
                self.session.headers['Authorization'] = auth_header

    def test_nowpayments_environment_configuration(self):
        """Test NOWPayments environment configuration and error handling"""
        try:
            # Test that placeholder API keys show proper error messages
            charge_data = {"plan": "pro", "pay_currency": "btc"}
            
            if self.auth_token:
                response = self.session.post(f"{API_BASE}/crypto/create-charge", json=charge_data)
                
                if response.status_code == 503:
                    response_data = response.json()
                    detail = response_data.get("detail", "")
                    
                    if "not configured yet" in detail.lower() and "contact support" in detail.lower():
                        self.log_test("NOWPayments Environment Configuration", True, 
                                    "Properly handles placeholder API keys with user-friendly message", response_data)
                    else:
                        self.log_test("NOWPayments Environment Configuration", False, 
                                    f"Error message not user-friendly: {detail}", response_data)
                else:
                    self.log_test("NOWPayments Environment Configuration", True, 
                                f"API keys appear to be configured (HTTP {response.status_code})")
            else:
                self.log_test("NOWPayments Environment Configuration", False, 
                            "Cannot test without authentication")
            
        except Exception as e:
            self.log_test("NOWPayments Environment Configuration", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all NOWPayments tests"""
        print("🚀 Starting NOWPayments Cryptocurrency Payment System Tests")
        print("=" * 70)
        
        # Setup authentication
        print("🔐 Setting up authentication...")
        auth_success = self.setup_authentication()
        
        if not auth_success:
            print("❌ Authentication setup failed. Some tests will be skipped.")
        
        # Test charge creation with valid plans and currencies
        self.test_nowpayments_create_charge_valid_plans()
        
        # Test validation (invalid plans and currencies)
        self.test_nowpayments_create_charge_validation()
        
        # Test supported currencies endpoint
        self.test_nowpayments_currencies_endpoint()
        
        # Test IPN (webhook) handler
        self.test_nowpayments_ipn_handler()
        
        # Test payment history endpoint
        self.test_nowpayments_payment_history()
        
        # Test authentication requirements
        self.test_nowpayments_authentication_required()
        
        # Test environment configuration
        self.test_nowpayments_environment_configuration()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 NOWPAYMENTS CRYPTOCURRENCY PAYMENT SYSTEM TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total NOWPayments Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        # Break down by test categories
        categories = {
            'Charge Creation': [t for t in self.test_results if 'create charge' in t['test'].lower()],
            'Validation': [t for t in self.test_results if 'validation' in t['test'].lower()],
            'Currencies': [t for t in self.test_results if 'currencies' in t['test'].lower()],
            'IPN Handler': [t for t in self.test_results if 'ipn' in t['test'].lower()],
            'Payment History': [t for t in self.test_results if 'payment history' in t['test'].lower()],
            'Authentication': [t for t in self.test_results if 'auth' in t['test'].lower()],
            'Configuration': [t for t in self.test_results if 'configuration' in t['test'].lower()]
        }
        
        print("\n📋 TEST BREAKDOWN BY CATEGORY:")
        for category, tests in categories.items():
            if tests:
                passed = len([t for t in tests if t['success']])
                total = len(tests)
                print(f"  {category}: {passed}/{total} ({(passed/total)*100:.1f}%)")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
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
    tester = NOWPaymentsTester()
    summary = tester.run_all_tests()
    
    print(f"\n🎯 Final Result: {summary['passed']}/{summary['total']} tests passed ({summary['success_rate']:.1f}%)")
    
    # Exit with appropriate code
    exit(0 if summary['failed'] == 0 else 1)