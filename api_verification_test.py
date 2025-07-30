#!/usr/bin/env python3
"""
API Verification Test for Database Administration Changes
Tests that the backend API correctly reflects the database changes.
"""

import requests
import json
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

if not backend_url:
    raise Exception("Could not find REACT_APP_BACKEND_URL in frontend/.env")

API_BASE = f"{backend_url}/api"

class APIVerificationTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.telegram_bot_token = "8342094196:AAE-E8jIYLjYflUPtY0G02NLbogbDpN_FE8"
        self.auth_token = None

    def generate_telegram_auth_data(self, telegram_id: int, first_name: str, last_name: str = None, username: str = None):
        """Generate valid Telegram authentication data"""
        auth_date = int(datetime.now(timezone.utc).timestamp())
        
        auth_data = {
            'id': telegram_id,
            'first_name': first_name,
            'auth_date': auth_date
        }
        
        if last_name:
            auth_data['last_name'] = last_name
        if username:
            auth_data['username'] = username
        
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

    def authenticate_as_user(self, telegram_id: int, first_name: str, last_name: str = None, username: str = None):
        """Authenticate as a specific user via Telegram auth"""
        try:
            auth_data = self.generate_telegram_auth_data(telegram_id, first_name, last_name, username)
            
            response = self.session.post(f"{API_BASE}/auth/telegram", json=auth_data)
            
            if response.status_code == 200:
                auth_response = response.json()
                self.auth_token = auth_response.get('access_token')
                
                # Set authorization header
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                
                print(f"✅ Successfully authenticated as {first_name} (telegram_id: {telegram_id})")
                return True
            else:
                print(f"❌ Authentication failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def verify_organization_plan_via_api(self, expected_plan: str):
        """Verify organization plan through the API"""
        try:
            response = self.session.get(f"{API_BASE}/organizations/current")
            
            if response.status_code == 200:
                org_data = response.json()
                current_plan = org_data.get('plan')
                
                print(f"📋 API Response - Organization: {org_data.get('name')}")
                print(f"📋 API Response - Current Plan: {current_plan}")
                print(f"📋 Expected Plan: {expected_plan}")
                
                if current_plan == expected_plan:
                    print(f"✅ API VERIFICATION SUCCESSFUL!")
                    print(f"   Organization plan correctly shows: {current_plan}")
                    return True
                else:
                    print(f"❌ API VERIFICATION FAILED!")
                    print(f"   Expected: {expected_plan}, Got: {current_plan}")
                    return False
            else:
                print(f"❌ API request failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API verification error: {e}")
            return False

async def main():
    """Main API verification function"""
    
    print("=" * 60)
    print("🔍 API VERIFICATION: USER SUBSCRIPTION PLAN CHANGE")
    print("=" * 60)
    print(f"API Base URL: {API_BASE}")
    print("=" * 60)
    
    tester = APIVerificationTester()
    
    # Target user details (from the database admin task)
    TARGET_TELEGRAM_ID = 6739704742
    USER_FIRST_NAME = "Ramon"
    USER_LAST_NAME = "6739704742"
    USERNAME = "Snooper_beast"
    EXPECTED_PLAN = "free"
    
    try:
        # Step 1: Authenticate as the target user
        print(f"🔐 Step 1: Authenticating as user (telegram_id: {TARGET_TELEGRAM_ID})")
        auth_success = tester.authenticate_as_user(TARGET_TELEGRAM_ID, USER_FIRST_NAME, USER_LAST_NAME, USERNAME)
        
        if not auth_success:
            print("❌ Cannot proceed without authentication")
            return False
        
        # Step 2: Verify organization plan via API
        print(f"🔍 Step 2: Verifying organization plan via API")
        api_verification_success = tester.verify_organization_plan_via_api(EXPECTED_PLAN)
        
        print("=" * 60)
        if api_verification_success:
            print("🎉 API VERIFICATION COMPLETE: Backend API correctly reflects the database changes!")
            print(f"✅ User 'ramon' (telegram_id: {TARGET_TELEGRAM_ID}) organization plan is '{EXPECTED_PLAN}'")
        else:
            print("❌ API VERIFICATION FAILED: Backend API does not reflect the database changes!")
        print("=" * 60)
        
        return api_verification_success
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())