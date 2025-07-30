#!/usr/bin/env python3
"""
Database Administration Script for Telegram Monitoring Bot
Handles specific database operations like updating user subscription plans.
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

class DatabaseAdmin:
    def __init__(self):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        
    async def close(self):
        """Close database connection"""
        self.client.close()
    
    async def find_user_by_telegram_id(self, telegram_id: int):
        """Find user by telegram_id"""
        try:
            user = await self.db.users.find_one({"telegram_id": telegram_id})
            return user
        except Exception as e:
            print(f"❌ Error finding user: {e}")
            return None
    
    async def get_organization_by_id(self, organization_id: str):
        """Get organization by ID"""
        try:
            org = await self.db.organizations.find_one({"id": organization_id})
            return org
        except Exception as e:
            print(f"❌ Error getting organization: {e}")
            return None
    
    async def update_organization_plan(self, organization_id: str, new_plan: str):
        """Update organization plan"""
        try:
            result = await self.db.organizations.update_one(
                {"id": organization_id},
                {
                    "$set": {
                        "plan": new_plan,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error updating organization plan: {e}")
            return False
    
    async def change_user_subscription_plan(self, telegram_id: int, new_plan: str):
        """
        Complete workflow to change a user's subscription plan
        
        Args:
            telegram_id: The Telegram ID of the user
            new_plan: The new plan to set ("free", "pro", "enterprise")
        
        Returns:
            dict: Result of the operation with details
        """
        result = {
            "success": False,
            "user_found": False,
            "organization_found": False,
            "plan_updated": False,
            "details": {},
            "errors": []
        }
        
        try:
            print(f"🔍 Step 1: Finding user with telegram_id: {telegram_id}")
            
            # Step 1: Find user
            user = await self.find_user_by_telegram_id(telegram_id)
            if not user:
                result["errors"].append(f"User with telegram_id {telegram_id} not found")
                return result
            
            result["user_found"] = True
            result["details"]["user"] = {
                "id": user.get("id"),
                "telegram_id": user.get("telegram_id"),
                "username": user.get("username"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "organization_id": user.get("organization_id")
            }
            
            print(f"✅ User found: {user.get('first_name')} {user.get('last_name')} (@{user.get('username')})")
            print(f"   Organization ID: {user.get('organization_id')}")
            
            # Step 2: Get organization
            organization_id = user.get("organization_id")
            if not organization_id:
                result["errors"].append("User has no organization_id")
                return result
            
            print(f"🔍 Step 2: Getting organization with ID: {organization_id}")
            
            org = await self.get_organization_by_id(organization_id)
            if not org:
                result["errors"].append(f"Organization with ID {organization_id} not found")
                return result
            
            result["organization_found"] = True
            result["details"]["organization_before"] = {
                "id": org.get("id"),
                "name": org.get("name"),
                "plan": org.get("plan"),
                "updated_at": org.get("updated_at")
            }
            
            print(f"✅ Organization found: {org.get('name')}")
            print(f"   Current plan: {org.get('plan')}")
            
            # Step 3: Update plan
            print(f"🔄 Step 3: Updating organization plan to '{new_plan}'")
            
            plan_updated = await self.update_organization_plan(organization_id, new_plan)
            if not plan_updated:
                result["errors"].append(f"Failed to update organization plan to {new_plan}")
                return result
            
            result["plan_updated"] = True
            
            # Step 4: Verify update
            print(f"✅ Step 4: Verifying plan update")
            
            updated_org = await self.get_organization_by_id(organization_id)
            if updated_org:
                result["details"]["organization_after"] = {
                    "id": updated_org.get("id"),
                    "name": updated_org.get("name"),
                    "plan": updated_org.get("plan"),
                    "updated_at": updated_org.get("updated_at")
                }
                
                if updated_org.get("plan") == new_plan:
                    result["success"] = True
                    print(f"✅ SUCCESS: Organization plan successfully updated to '{new_plan}'")
                else:
                    result["errors"].append(f"Plan verification failed. Expected: {new_plan}, Got: {updated_org.get('plan')}")
            else:
                result["errors"].append("Could not verify plan update - organization not found after update")
            
            return result
            
        except Exception as e:
            result["errors"].append(f"Unexpected error: {str(e)}")
            print(f"❌ Unexpected error: {e}")
            return result

async def main():
    """Main function to execute the user subscription plan change"""
    
    # Task parameters
    TARGET_TELEGRAM_ID = 6739704742  # ramon
    NEW_PLAN = "free"
    
    print("=" * 60)
    print("🔧 DATABASE ADMINISTRATION: UPDATE USER SUBSCRIPTION PLAN")
    print("=" * 60)
    print(f"Target User Telegram ID: {TARGET_TELEGRAM_ID}")
    print(f"New Plan: {NEW_PLAN}")
    print(f"Database: {mongo_url}/{db_name}")
    print("=" * 60)
    
    admin = DatabaseAdmin()
    
    try:
        # Execute the plan change
        result = await admin.change_user_subscription_plan(TARGET_TELEGRAM_ID, NEW_PLAN)
        
        print("\n" + "=" * 60)
        print("📊 OPERATION RESULTS")
        print("=" * 60)
        
        print(f"✅ User Found: {result['user_found']}")
        print(f"✅ Organization Found: {result['organization_found']}")
        print(f"✅ Plan Updated: {result['plan_updated']}")
        print(f"🎯 Overall Success: {result['success']}")
        
        if result["errors"]:
            print(f"\n❌ Errors ({len(result['errors'])}):")
            for error in result["errors"]:
                print(f"   • {error}")
        
        if result["details"]:
            print(f"\n📋 Details:")
            
            if "user" in result["details"]:
                user = result["details"]["user"]
                print(f"   👤 User: {user['first_name']} {user['last_name']} (@{user['username']})")
                print(f"      Telegram ID: {user['telegram_id']}")
                print(f"      User ID: {user['id']}")
                print(f"      Organization ID: {user['organization_id']}")
            
            if "organization_before" in result["details"]:
                org_before = result["details"]["organization_before"]
                print(f"   🏢 Organization (BEFORE): {org_before['name']}")
                print(f"      Plan: {org_before['plan']}")
                print(f"      Last Updated: {org_before['updated_at']}")
            
            if "organization_after" in result["details"]:
                org_after = result["details"]["organization_after"]
                print(f"   🏢 Organization (AFTER): {org_after['name']}")
                print(f"      Plan: {org_after['plan']}")
                print(f"      Last Updated: {org_after['updated_at']}")
        
        print("\n" + "=" * 60)
        
        if result["success"]:
            print("🎉 TASK COMPLETED SUCCESSFULLY!")
            print(f"User 'ramon' (telegram_id: {TARGET_TELEGRAM_ID}) now has '{NEW_PLAN}' plan")
        else:
            print("❌ TASK FAILED!")
            print("Please check the errors above and try again")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("=" * 60)
        
    finally:
        await admin.close()

if __name__ == "__main__":
    asyncio.run(main())