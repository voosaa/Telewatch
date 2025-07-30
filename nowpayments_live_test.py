#!/usr/bin/env python3
"""
NOWPayments Live API Testing Script
Tests the NOWPayments cryptocurrency payment system with LIVE API credentials.
"""

import requests
import json
import time
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, List
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

print(f"🚀 Testing NOWPayments Live API at: {API_BASE}")
print("=" * 80)

class NOWPaymentsLiveTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.auth_token = None
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
        """Setup authentication using Telegram registration"""
        import random
        import time
        
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
        
        try:
            response = self.session.post(f"{API_BASE}/auth/register", json=registration_data)
            
            if response.status_code == 200:
                auth_response = response.json()
                self.auth_token = auth_response['access_token']
                
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

    def test_live_api_connection(self):
        """Test GET /api/crypto/currencies with live NOWPayments API"""
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
                        self.log_test("🌐 Live API Connection - Currencies", True, 
                                    f"✅ Successfully connected to NOWPayments API! Found {len(currencies)} currencies including: {found_currencies[:10]}", 
                                    {"total_currencies": len(currencies), "sample": currencies[:3]})
                    else:
                        self.log_test("🌐 Live API Connection - Currencies", False, 
                                    f"Connected to API but missing expected currencies: {missing_currencies}", currencies_data)
                    
                    # Verify currency structure
                    if currencies:
                        sample_currency = currencies[0]
                        required_fields = ["currency", "name", "network"]
                        missing_fields = [field for field in required_fields if field not in sample_currency]
                        
                        if not missing_fields:
                            self.log_test("🌐 Live API - Currency Structure", True, 
                                        f"✅ Currency objects have correct structure", sample_currency)
                        else:
                            self.log_test("🌐 Live API - Currency Structure", False, 
                                        f"Missing fields in currency object: {missing_fields}", sample_currency)
                else:
                    self.log_test("🌐 Live API Connection - Currencies", False, 
                                "Missing 'currencies' field in response", currencies_data)
            elif response.status_code == 503:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                if "not configured" in str(response_data).lower():
                    self.log_test("🌐 Live API Connection - Currencies", False, 
                                "❌ NOWPayments API still shows 'not configured' - API keys may not be properly set", response_data)
                else:
                    self.log_test("🌐 Live API Connection - Currencies", False, 
                                f"Service unavailable: HTTP {response.status_code}", response_data)
            else:
                self.log_test("🌐 Live API Connection - Currencies", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("🌐 Live API Connection - Currencies", False, f"Error: {str(e)}")

    def test_live_payment_creation(self):
        """Test POST /api/crypto/create-charge with live NOWPayments API"""
        if not self.auth_token:
            self.log_test("💰 Live Payment Creation", False, "No authentication token available")
            return
            
        try:
            # Test Pro plan with different cryptocurrencies
            test_cases = [
                {"plan": "pro", "pay_currency": "btc", "expected_price": 9.99, "description": "Pro Plan with Bitcoin"},
                {"plan": "pro", "pay_currency": "eth", "expected_price": 9.99, "description": "Pro Plan with Ethereum"},
                {"plan": "pro", "pay_currency": "usdt", "expected_price": 9.99, "description": "Pro Plan with USDT"},
                {"plan": "enterprise", "pay_currency": "btc", "expected_price": 19.99, "description": "Enterprise Plan with Bitcoin"},
                {"plan": "enterprise", "pay_currency": "sol", "expected_price": 19.99, "description": "Enterprise Plan with Solana"}
            ]
            
            for test_case in test_cases:
                charge_data = {
                    "plan": test_case["plan"],
                    "pay_currency": test_case["pay_currency"]
                }
                
                response = self.session.post(f"{API_BASE}/crypto/create-charge", json=charge_data)
                
                if response.status_code == 200:
                    # Real API response - verify structure
                    charge_response = response.json()
                    required_fields = ['payment_url', 'payment_id', 'amount', 'plan', 'pay_currency']
                    missing_fields = [field for field in required_fields if field not in charge_response]
                    
                    if not missing_fields and str(charge_response['amount']) == str(test_case['expected_price']):
                        self.log_test(f"💰 Live Payment Creation - {test_case['description']}", True, 
                                    f"✅ Successfully created REAL payment charge for ${test_case['expected_price']} in {test_case['pay_currency'].upper()}! Payment URL: {charge_response.get('payment_url', 'N/A')[:50]}...", 
                                    {
                                        "payment_id": charge_response.get('payment_id'),
                                        "amount": charge_response.get('amount'),
                                        "currency": charge_response.get('pay_currency'),
                                        "payment_url_preview": charge_response.get('payment_url', '')[:100]
                                    })
                    else:
                        self.log_test(f"💰 Live Payment Creation - {test_case['description']}", False, 
                                    f"Missing fields: {missing_fields} or incorrect amount. Expected: ${test_case['expected_price']}, Got: ${charge_response.get('amount')}", charge_response)
                elif response.status_code == 503:
                    response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    if "not configured" in str(response_data).lower():
                        self.log_test(f"💰 Live Payment Creation - {test_case['description']}", False, 
                                    "❌ NOWPayments API still shows 'not configured' - API keys may not be properly set", response_data)
                    else:
                        self.log_test(f"💰 Live Payment Creation - {test_case['description']}", False, 
                                    f"Service unavailable: HTTP {response.status_code}", response_data)
                else:
                    self.log_test(f"💰 Live Payment Creation - {test_case['description']}", False, 
                                f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("💰 Live Payment Creation", False, f"Error: {str(e)}")

    def test_live_ipn_configuration(self):
        """Test POST /api/crypto/ipn endpoint with live IPN secret"""
        try:
            # Test IPN endpoint with mock data
            mock_ipn_data = {
                "payment_id": "live_test_payment_123",
                "payment_status": "confirmed",
                "order_id": "live_test_order_456",
                "price_amount": "9.99",
                "price_currency": "usd",
                "pay_amount": "0.0003",
                "pay_currency": "btc",
                "outcome_amount": "0.0003",
                "outcome_currency": "btc"
            }
            
            # Test without signature header (should fail with proper validation)
            response = self.session.post(f"{API_BASE}/crypto/ipn", json=mock_ipn_data)
            
            if response.status_code == 403:
                self.log_test("🔐 Live IPN Configuration - Signature Validation", True, 
                            "✅ IPN endpoint properly validates signatures (rejected unsigned request with HTTP 403)")
            elif response.status_code == 503:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                if "not configured" in str(response_data).lower():
                    self.log_test("🔐 Live IPN Configuration - Signature Validation", False, 
                                "❌ IPN secret still shows 'not configured' - IPN secret may not be properly set", response_data)
                else:
                    self.log_test("🔐 Live IPN Configuration - Signature Validation", False, 
                                f"Service unavailable: HTTP {response.status_code}", response_data)
            else:
                self.log_test("🔐 Live IPN Configuration - Signature Validation", False, 
                            f"Expected HTTP 403 or 503 but got {response.status_code}", response.text)
            
            # Test with invalid JSON
            response = self.session.post(f"{API_BASE}/crypto/ipn", 
                                       data="invalid json data",
                                       headers={"Content-Type": "application/json"})
            
            if response.status_code in [400, 403, 503]:
                self.log_test("🔐 Live IPN Configuration - Invalid JSON Handling", True, 
                            f"✅ IPN endpoint properly handles invalid JSON with HTTP {response.status_code}")
            else:
                self.log_test("🔐 Live IPN Configuration - Invalid JSON Handling", False, 
                            f"Expected HTTP 400, 403, or 503 but got {response.status_code}")
                
        except Exception as e:
            self.log_test("🔐 Live IPN Configuration", False, f"Error: {str(e)}")

    def test_payment_validation(self):
        """Test payment validation with invalid plans and currencies"""
        if not self.auth_token:
            self.log_test("🔍 Payment Validation", False, "No authentication token available")
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
                    self.log_test(f"🔍 Payment Validation - Invalid Plan '{invalid_plan}'", True, 
                                f"✅ Correctly rejected invalid plan with HTTP 400")
                elif response.status_code == 422:
                    self.log_test(f"🔍 Payment Validation - Invalid Plan '{invalid_plan}'", True, 
                                f"✅ Correctly rejected invalid plan with HTTP 422 (validation error)")
                else:
                    self.log_test(f"🔍 Payment Validation - Invalid Plan '{invalid_plan}'", False, 
                                f"Expected HTTP 400/422 but got {response.status_code}")
            
            # Test invalid currencies
            invalid_currencies = ["doge", "ltc", "invalid", "", "BTC"]  # BTC uppercase should be rejected
            
            for invalid_currency in invalid_currencies:
                charge_data = {
                    "plan": "pro",
                    "pay_currency": invalid_currency
                }
                
                response = self.session.post(f"{API_BASE}/crypto/create-charge", json=charge_data)
                
                if response.status_code in [400, 422]:
                    self.log_test(f"🔍 Payment Validation - Invalid Currency '{invalid_currency}'", True, 
                                f"✅ Correctly rejected invalid currency with HTTP {response.status_code}")
                else:
                    self.log_test(f"🔍 Payment Validation - Invalid Currency '{invalid_currency}'", False, 
                                f"Expected HTTP 400/422 but got {response.status_code}")
                
        except Exception as e:
            self.log_test("🔍 Payment Validation", False, f"Error: {str(e)}")

    def test_payment_history(self):
        """Test GET /api/crypto/charges - Payment history endpoint"""
        if not self.auth_token:
            self.log_test("📊 Payment History", False, "No authentication token available")
            return
            
        try:
            response = self.session.get(f"{API_BASE}/crypto/charges")
            
            if response.status_code == 200:
                charges = response.json()
                self.log_test("📊 Payment History", True, 
                            f"✅ Successfully retrieved payment history with {len(charges)} charges", 
                            {"charge_count": len(charges), "sample": charges[:2] if charges else "No charges yet"})
                
                # Verify response structure if charges exist
                if charges:
                    charge = charges[0]
                    # Verify sensitive fields are removed
                    sensitive_fields = ['nowpayments_response', 'ipn_data']
                    found_sensitive = [field for field in sensitive_fields if field in charge]
                    
                    if not found_sensitive:
                        self.log_test("📊 Payment History - Data Sanitization", True, 
                                    "✅ Sensitive fields properly removed from payment history responses")
                    else:
                        self.log_test("📊 Payment History - Data Sanitization", False, 
                                    f"Sensitive fields found in response: {found_sensitive}")
                else:
                    self.log_test("📊 Payment History - Empty Response", True, 
                                "✅ No payment charges found (expected for new organization)")
                    
            else:
                self.log_test("📊 Payment History", False, 
                            f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("📊 Payment History", False, f"Error: {str(e)}")

    def test_authentication_security(self):
        """Test that crypto endpoints require authentication"""
        # Save current auth header
        auth_header = self.session.headers.get('Authorization')
        
        try:
            # Remove auth header
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            
            # Test endpoints without auth
            endpoints_to_test = [
                ("POST", f"{API_BASE}/crypto/create-charge", {"plan": "pro", "pay_currency": "btc"}),
                ("GET", f"{API_BASE}/crypto/charges", None)
            ]
            
            for method, url, data in endpoints_to_test:
                if method == "POST":
                    response = self.session.post(url, json=data)
                else:
                    response = self.session.get(url)
                
                if response.status_code == 403:
                    self.log_test(f"🔒 Authentication Security - {method} {url.split('/')[-1]}", True, 
                                "✅ Correctly rejected unauthenticated request with HTTP 403")
                else:
                    self.log_test(f"🔒 Authentication Security - {method} {url.split('/')[-1]}", False, 
                                f"Expected HTTP 403 but got {response.status_code}")
                
        except Exception as e:
            self.log_test("🔒 Authentication Security", False, f"Error: {str(e)}")
        finally:
            # Restore auth header
            if auth_header:
                self.session.headers['Authorization'] = auth_header

    def test_production_readiness(self):
        """Test overall production readiness indicators"""
        try:
            # Test that the system is no longer showing "not configured" errors
            response = self.session.get(f"{API_BASE}/crypto/currencies")
            
            if response.status_code == 200:
                self.log_test("🚀 Production Readiness - API Configuration", True, 
                            "✅ NOWPayments API is properly configured and responding")
            elif response.status_code == 503:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                if "not configured" in str(response_data).lower():
                    self.log_test("🚀 Production Readiness - API Configuration", False, 
                                "❌ System still shows 'not configured' - API keys may not be active")
                else:
                    self.log_test("🚀 Production Readiness - API Configuration", False, 
                                f"Service unavailable: {response_data}")
            else:
                self.log_test("🚀 Production Readiness - API Configuration", False, 
                            f"Unexpected response: HTTP {response.status_code}")
            
            # Test environment configuration
            backend_env_path = Path("/app/backend/.env")
            if backend_env_path.exists():
                with open(backend_env_path, 'r') as f:
                    env_content = f.read()
                    
                    # Check for live credentials
                    has_api_key = "NOWPAYMENTS_API_KEY=" in env_content and "N9BG2RQ-TSX4PCC-J6PNTQP-MRPM6NF" in env_content
                    has_ipn_secret = "NOWPAYMENTS_IPN_SECRET=" in env_content and "6fde78fb-814c-407f-b456-a4717dbc1a29" in env_content
                    is_production = "NOWPAYMENTS_SANDBOX=false" in env_content
                    
                    if has_api_key and has_ipn_secret and is_production:
                        self.log_test("🚀 Production Readiness - Environment Configuration", True, 
                                    "✅ Live NOWPayments credentials properly configured in production mode")
                    else:
                        issues = []
                        if not has_api_key:
                            issues.append("API key not found")
                        if not has_ipn_secret:
                            issues.append("IPN secret not found")
                        if not is_production:
                            issues.append("Not in production mode")
                        
                        self.log_test("🚀 Production Readiness - Environment Configuration", False, 
                                    f"Configuration issues: {', '.join(issues)}")
            else:
                self.log_test("🚀 Production Readiness - Environment Configuration", False, 
                            "Backend .env file not found")
                
        except Exception as e:
            self.log_test("🚀 Production Readiness", False, f"Error: {str(e)}")

    def run_comprehensive_live_tests(self):
        """Run all live NOWPayments tests"""
        print("🌟 NOWPAYMENTS LIVE API TESTING WITH REAL CREDENTIALS")
        print("=" * 80)
        print("⚠️  IMPORTANT: Testing with LIVE NOWPayments API credentials")
        print("⚠️  API Key: N9BG2RQ-TSX4PCC-J6PNTQP-MRPM6NF")
        print("⚠️  IPN Secret: 6fde78fb-814c-407f-b456-a4717dbc1a29")
        print("⚠️  Mode: PRODUCTION (Sandbox: false)")
        print("=" * 80)
        print()
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Failed to setup authentication. Aborting tests.")
            return
        
        print("🔥 CRITICAL TESTING PRIORITIES:")
        print("=" * 50)
        
        # 1. Live API Connection Test
        print("1️⃣ LIVE API CONNECTION TEST:")
        self.test_live_api_connection()
        
        # 2. Payment Creation Test
        print("2️⃣ PAYMENT CREATION TEST:")
        self.test_live_payment_creation()
        
        # 3. IPN Configuration Test
        print("3️⃣ IPN CONFIGURATION TEST:")
        self.test_live_ipn_configuration()
        
        # 4. Error Handling Verification
        print("4️⃣ ERROR HANDLING VERIFICATION:")
        self.test_payment_validation()
        
        # 5. Production Readiness Check
        print("5️⃣ PRODUCTION READINESS CHECK:")
        self.test_production_readiness()
        self.test_payment_history()
        self.test_authentication_security()
        
        # Print comprehensive summary
        self.print_final_summary()

    def print_final_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🎯 NOWPAYMENTS LIVE API TEST RESULTS SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests/total_tests)*100 if total_tests > 0 else 0
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"🎯 Success Rate: {success_rate:.1f}%")
        print()
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! NOWPayments system is ready for production!")
        elif success_rate >= 75:
            print("✅ GOOD! NOWPayments system is mostly ready with minor issues.")
        elif success_rate >= 50:
            print("⚠️  MODERATE! NOWPayments system has some issues that need attention.")
        else:
            print("❌ CRITICAL! NOWPayments system has major issues that must be fixed.")
        
        print()
        print("🔍 DETAILED RESULTS:")
        print("-" * 50)
        
        # Group results by category
        categories = {
            "🌐 Live API Connection": [],
            "💰 Payment Creation": [],
            "🔐 IPN Configuration": [],
            "🔍 Validation": [],
            "📊 Payment History": [],
            "🔒 Security": [],
            "🚀 Production Readiness": []
        }
        
        for result in self.test_results:
            test_name = result['test']
            categorized = False
            
            for category in categories:
                if any(keyword in test_name.lower() for keyword in category.lower().split()[1:]):
                    categories[category].append(result)
                    categorized = True
                    break
            
            if not categorized:
                if "🔧 Other" not in categories:
                    categories["🔧 Other"] = []
                categories["🔧 Other"].append(result)
        
        for category, results in categories.items():
            if results:
                print(f"\n{category}:")
                for result in results:
                    status = "✅" if result['success'] else "❌"
                    print(f"  {status} {result['test']}")
                    if not result['success'] and result['details']:
                        print(f"      → {result['details']}")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS SUMMARY:")
            print("-" * 30)
            for result in self.test_results:
                if not result['success']:
                    print(f"• {result['test']}: {result['details']}")
        
        print("\n" + "=" * 80)
        print("🎯 EXPECTED OUTCOMES VERIFICATION:")
        print("=" * 80)
        
        # Check expected outcomes
        outcomes = {
            "All 'service unavailable' errors resolved": any("Live API Connection" in r['test'] and r['success'] for r in self.test_results),
            "Real cryptocurrency data fetched": any("Live API Connection" in r['test'] and r['success'] for r in self.test_results),
            "Payment creation generates actual URLs": any("Payment Creation" in r['test'] and r['success'] for r in self.test_results),
            "System ready for real payments": success_rate >= 80
        }
        
        for outcome, achieved in outcomes.items():
            status = "✅" if achieved else "❌"
            print(f"{status} {outcome}")
        
        print("\n" + "=" * 80)
        
        if success_rate >= 80:
            print("🚀 CONCLUSION: NOWPayments cryptocurrency payment system is LIVE and ready for real user payments!")
        else:
            print("⚠️  CONCLUSION: NOWPayments system needs attention before going live with real payments.")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = NOWPaymentsLiveTester()
    try:
        tester.run_comprehensive_live_tests()
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        exit(1)