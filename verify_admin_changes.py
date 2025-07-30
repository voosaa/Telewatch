#!/usr/bin/env python3
"""
Verification Script for Database Administration Tasks
Verifies that database changes were applied correctly.
"""

import asyncio
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'telegram_bot_db')

async def verify_user_plan_change(telegram_id: int, expected_plan: str):
    """Verify that a user's organization plan was changed correctly"""
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        print("=" * 60)
        print("🔍 VERIFICATION: USER SUBSCRIPTION PLAN CHANGE")
        print("=" * 60)
        print(f"Target Telegram ID: {telegram_id}")
        print(f"Expected Plan: {expected_plan}")
        print("=" * 60)
        
        # Find user
        print(f"🔍 Looking up user with telegram_id: {telegram_id}")
        user = await db.users.find_one({"telegram_id": telegram_id})
        
        if not user:
            print(f"❌ VERIFICATION FAILED: User with telegram_id {telegram_id} not found")
            return False
        
        print(f"✅ User found: {user.get('first_name')} {user.get('last_name')} (@{user.get('username')})")
        
        # Get organization
        organization_id = user.get("organization_id")
        if not organization_id:
            print(f"❌ VERIFICATION FAILED: User has no organization_id")
            return False
        
        print(f"🔍 Looking up organization: {organization_id}")
        org = await db.organizations.find_one({"id": organization_id})
        
        if not org:
            print(f"❌ VERIFICATION FAILED: Organization {organization_id} not found")
            return False
        
        print(f"✅ Organization found: {org.get('name')}")
        
        # Check plan
        current_plan = org.get("plan")
        print(f"📋 Current plan: {current_plan}")
        print(f"📋 Expected plan: {expected_plan}")
        
        if current_plan == expected_plan:
            print(f"✅ VERIFICATION SUCCESSFUL!")
            print(f"   User '{user.get('first_name')}' (telegram_id: {telegram_id})")
            print(f"   Organization: '{org.get('name')}'")
            print(f"   Plan: '{current_plan}' ✓")
            print(f"   Last Updated: {org.get('updated_at')}")
            return True
        else:
            print(f"❌ VERIFICATION FAILED!")
            print(f"   Expected plan: {expected_plan}")
            print(f"   Actual plan: {current_plan}")
            return False
            
    except Exception as e:
        print(f"❌ VERIFICATION ERROR: {e}")
        return False
    finally:
        client.close()

async def main():
    """Main verification function"""
    
    # Verify the specific task that was completed
    TARGET_TELEGRAM_ID = 6739704742  # ramon
    EXPECTED_PLAN = "free"
    
    success = await verify_user_plan_change(TARGET_TELEGRAM_ID, EXPECTED_PLAN)
    
    print("=" * 60)
    if success:
        print("🎉 VERIFICATION COMPLETE: All changes verified successfully!")
    else:
        print("❌ VERIFICATION FAILED: Changes were not applied correctly!")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    asyncio.run(main())