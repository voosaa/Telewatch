from fastapi import FastAPI, APIRouter, HTTPException, Request, BackgroundTasks, Depends, Form, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any, Set
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import json
import re
import jwt
import bcrypt
import hashlib
import hmac
import aiofiles
import json
import os
from pathlib import Path
from enum import Enum
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create upload directories for accounts
UPLOAD_DIR = Path("/app/uploads")
SESSIONS_DIR = UPLOAD_DIR / "sessions"
JSON_DIR = UPLOAD_DIR / "json"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)

# JWT Configuration
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = os.environ['JWT_ALGORITHM']
JWT_EXPIRATION_HOURS = int(os.environ['JWT_EXPIRATION_HOURS'])

# Security
security = HTTPBearer()

# Telegram Bot Setup
telegram_token = os.environ['TELEGRAM_TOKEN']
bot = Bot(token=telegram_token)

# Polling state
polling_task = None
last_update_id = 0

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ================== ENUMS & TYPES ==================

class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    VIEWER = "viewer"

class OrganizationPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

# ================== AUTHENTICATION MODELS ==================

class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    organization_name: Optional[str] = None  # For creating new org during registration

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    full_name: str
    photo_url: Optional[str] = None
    is_active: bool
    role: UserRole
    organization_id: str
    created_at: datetime
    last_login: Optional[datetime] = None

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool = True
    role: UserRole = UserRole.VIEWER
    organization_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    
    @property
    def full_name(self) -> str:
        """Generate full name from Telegram first_name and last_name"""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    plan: OrganizationPlan = OrganizationPlan.FREE

class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    plan: OrganizationPlan = OrganizationPlan.FREE
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    settings: Dict[str, Any] = Field(default_factory=dict)
    usage_stats: Dict[str, int] = Field(default_factory=lambda: {
        "total_groups": 0,
        "total_users": 0,
        "total_messages": 0,
        "total_forwarded": 0
    })

class UserInvite(BaseModel):
    email: EmailStr
    role: UserRole
    full_name: str

class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    created_by: str
    name: str  # Display name for the account
    phone_number: Optional[str] = None  # Phone number from JSON
    username: Optional[str] = None  # Username from JSON
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: AccountStatus = AccountStatus.INACTIVE
    is_active: bool = True
    session_file_path: str  # Path to the session file
    json_file_path: str    # Path to the JSON file
    last_activity: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Store JSON file contents

class AccountCreate(BaseModel):
    name: str
    session_file: bytes
    json_file: bytes
    session_filename: str
    json_filename: str

class AccountResponse(BaseModel):
    id: str
    name: str
    phone_number: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: AccountStatus
    is_active: bool
    last_activity: Optional[datetime] = None
    created_at: datetime
    error_message: Optional[str] = None

# ================== PYDANTIC MODELS (Updated with tenant_id) ==================

class GroupCreate(BaseModel):
    group_id: str
    group_name: str
    group_type: str = "group"  # group, supergroup, channel
    invite_link: Optional[str] = None
    description: Optional[str] = None

class Group(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # Organization ID for multi-tenancy
    group_id: str
    group_name: str
    group_type: str
    invite_link: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str  # User ID who created this group

class ForwardingDestinationCreate(BaseModel):
    destination_id: str  # Chat/Channel ID where messages will be forwarded
    destination_name: str
    destination_type: str = "channel"  # channel, group, user
    is_active: bool = True
    description: Optional[str] = None

class ForwardingDestination(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # Organization ID for multi-tenancy
    destination_id: str
    destination_name: str
    destination_type: str
    is_active: bool = True
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0  # Track forwarded messages
    last_forwarded: Optional[datetime] = None
    created_by: str  # User ID who created this destination

class WatchlistUserCreate(BaseModel):
    username: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    group_ids: List[str] = []  # Empty means monitor globally
    keywords: List[str] = []  # Optional keyword filtering
    forwarding_destinations: List[str] = []  # IDs of forwarding destinations

class WatchlistUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # Organization ID for multi-tenancy
    username: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    group_ids: List[str] = []
    keywords: List[str] = []
    forwarding_destinations: List[str] = []  # IDs of forwarding destinations
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str  # User ID who created this user

class ForwardedMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # Organization ID for multi-tenancy
    original_message_id: str
    source_group_id: str
    from_group_id: str  # Keep for backward compatibility
    from_group_name: str
    from_user_id: str
    from_username: str
    from_user_full_name: Optional[str] = None
    message_text: Optional[str] = None
    message_type: str  # text, photo, video, document, etc.
    media_info: Optional[Dict[str, Any]] = None
    forwarded_to_destinations: List[str] = []  # IDs of destinations where forwarded
    forwarded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    matched_keywords: List[str] = []
    forwarding_status: str = "success"  # success, failed, partial
    error_details: Optional[str] = None
    destination_chat_id: Optional[str] = None
    destination_name: Optional[str] = None
    forwarded_by_account: Optional[str] = None
    detected_by_account: Optional[str] = None
    created_by: Optional[str] = None

class MessageLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # Organization ID for multi-tenancy
    message_id: str
    group_id: str
    group_name: str
    user_id: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_full_name: Optional[str] = None
    message_text: Optional[str] = None
    message_date: Optional[datetime] = None
    message_type: str
    media_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_forwarded: bool = False
    forwarded_count: int = 0  # Number of destinations forwarded to
    matched_keywords: List[str] = []
    created_by: Optional[str] = None
    media_type: Optional[str] = None
    file_path: Optional[str] = None
    detected_by_account: Optional[str] = None
    is_edited: bool = False

class BotCommand(BaseModel):
    command: str
    chat_id: str
    user_id: str
    username: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ================== AUTHENTICATION UTILITIES ==================

# Password functions - deprecated for Telegram authentication
# def hash_password(password: str) -> str:
#     """Hash password using bcrypt"""
#     return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# def verify_password(password: str, hashed: str) -> bool:
#     """Verify password against hash"""
#     return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(user_id: str, organization_id: str, role: str) -> str:
    """Create JWT access token"""
    expires = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "exp": expires,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        user_id = payload.get("sub")
        organization_id = payload.get("org")
        role = payload.get("role")
        
        if not user_id or not organization_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Verify user exists and is active
        user_doc = await db.users.find_one({"id": user_id, "is_active": True})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        return {
            "user_id": user_id,
            "organization_id": organization_id,
            "role": UserRole(role),
            "user": User(**user_doc)
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current active user with additional checks"""
    user = current_user["user"]
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")
    return current_user

def require_role(required_roles: List[UserRole]):
    """Decorator to require specific roles"""
    def role_checker(current_user: Dict = Depends(get_current_active_user)) -> Dict[str, Any]:
        if current_user["role"] not in required_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Required roles: {[role.value for role in required_roles]}"
            )
        return current_user
    return role_checker

# Role-based dependencies
require_owner = require_role([UserRole.OWNER])
require_admin = require_role([UserRole.OWNER, UserRole.ADMIN])
require_any_role = require_role([UserRole.OWNER, UserRole.ADMIN, UserRole.VIEWER])

# ================== TELEGRAM AUTHENTICATION FUNCTIONS ==================

def verify_telegram_authentication(auth_data: Dict[str, Any]) -> bool:
    """Verify Telegram Login Widget authentication data"""
    try:
        bot_token = os.environ.get('TELEGRAM_TOKEN')
        if not bot_token:
            raise ValueError("Telegram bot token not configured")
        
        # Create a copy of auth_data without the hash
        check_data = auth_data.copy()
        received_hash = check_data.pop('hash', '')
        
        # Create data check string
        data_check_arr = [f"{key}={value}" for key, value in sorted(check_data.items())]
        data_check_string = '\n'.join(data_check_arr)
        
        # Create secret key from bot token
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        
        # Generate hash
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        # Verify hash matches
        if not hmac.compare_digest(calculated_hash, received_hash):
            return False
        
        # Check if auth_date is not too old (within 24 hours)
        auth_date = int(auth_data.get('auth_date', 0))
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        if current_timestamp - auth_date > 86400:  # 24 hours
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying Telegram authentication: {e}")
        return False

# ================== UTILITY FUNCTIONS (Updated for Multi-tenancy) ==================

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2"""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def check_if_user_monitored(user_id: str, username: str, group_id: str, tenant_id: str) -> Optional[WatchlistUser]:
    """Check if user is in watchlist for monitoring (tenant-specific)"""
    query = {
        "tenant_id": tenant_id,
        "is_active": True,
        "$or": [
            {"username": username.lower()},
            {"user_id": user_id}
        ]
    }
    
    user_doc = await db.watchlist_users.find_one(query)
    if not user_doc:
        return None
    
    user = WatchlistUser(**user_doc)
    
    # Check if user should be monitored in this group (empty group_ids means monitor globally)
    if not user.group_ids or group_id in user.group_ids:
        return user
    
    return None

async def check_keyword_match(message_text: str, keywords: List[str]) -> List[str]:
    """Check if message contains any of the keywords (supports regex)"""
    if not message_text or not keywords:
        return []
    
    matched = []
    for keyword in keywords:
        try:
            if re.search(keyword, message_text, re.IGNORECASE):
                matched.append(keyword)
        except re.error:
            # If regex fails, do simple string matching
            if keyword.lower() in message_text.lower():
                matched.append(keyword)
    
    return matched

async def format_forwarded_message(
    message_text: str, 
    message_type: str,
    username: str,
    group_name: str,
    matched_keywords: List[str],
    timestamp: datetime,
    media_info: Optional[Dict[str, Any]] = None
) -> str:
    """Format message for forwarding with attribution"""
    
    # Format timestamp
    time_str = timestamp.strftime('%Y-%m-%d %H:%M UTC')
    
    # Create header with source attribution
    header = f"🔔 *Monitor Alert*\n"
    header += f"👤 User: @{escape_markdown_v2(username)}\n"
    header += f"📍 Group: {escape_markdown_v2(group_name)}\n"
    header += f"🕐 Time: {escape_markdown_v2(time_str)}\n"
    
    # Add keywords if matched
    if matched_keywords:
        keywords_str = ", ".join(matched_keywords)
        header += f"🔍 Keywords: {escape_markdown_v2(keywords_str)}\n"
    
    header += f"📝 Type: {escape_markdown_v2(message_type.title())}\n"
    header += "─" * 30 + "\n\n"
    
    # Add message content
    if message_text:
        content = escape_markdown_v2(message_text)
    elif message_type != "text":
        content = f"\\[{message_type.upper()} MESSAGE\\]"
        if media_info:
            if message_type == "photo" and "file_size" in media_info:
                content += f"\n📊 Size: {media_info['file_size']} bytes"
            elif message_type == "video" and "duration" in media_info:
                content += f"\n⏱️ Duration: {media_info['duration']}s"
            elif message_type == "document" and "file_name" in media_info:
                content += f"\n📄 File: {escape_markdown_v2(media_info['file_name'])}"
    else:
        content = "\\[No text content\\]"
    
    return header + content

async def forward_message_to_destinations(
    message_text: str,
    message_type: str,
    username: str,
    group_name: str,
    matched_keywords: List[str],
    timestamp: datetime,
    destinations: List[str],
    media_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Forward message to specified destinations"""
    
    forwarding_results = {
        "success_count": 0,
        "failed_count": 0,
        "forwarded_to": [],
        "errors": []
    }
    
    if not destinations:
        return forwarding_results
    
    # Get active forwarding destinations
    dest_docs = await db.forwarding_destinations.find({
        "id": {"$in": destinations},
        "is_active": True
    }).to_list(100)
    
    if not dest_docs:
        forwarding_results["errors"].append("No active forwarding destinations found")
        return forwarding_results
    
    # Format the message for forwarding
    formatted_message = await format_forwarded_message(
        message_text, message_type, username, group_name, 
        matched_keywords, timestamp, media_info
    )
    
    # Forward to each destination
    for dest_doc in dest_docs:
        destination = ForwardingDestination(**dest_doc)
        
        try:
            # Send message to destination
            await bot.send_message(
                chat_id=destination.destination_id,
                text=formatted_message,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
            # Update destination stats
            await db.forwarding_destinations.update_one(
                {"id": destination.id},
                {
                    "$inc": {"message_count": 1},
                    "$set": {"last_forwarded": datetime.now(timezone.utc)}
                }
            )
            
            forwarding_results["success_count"] += 1
            forwarding_results["forwarded_to"].append(destination.destination_name)
            
            logger.info(f"✅ Forwarded message to {destination.destination_name}")
            
        except Exception as e:
            forwarding_results["failed_count"] += 1
            error_msg = f"Failed to forward to {destination.destination_name}: {str(e)}"
            forwarding_results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    return forwarding_results

# ================== TELEGRAM BOT HANDLERS ==================

async def create_main_menu_keyboard():
    """Create the main menu inline keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Status", callback_data="status"),
            InlineKeyboardButton("📁 Groups", callback_data="groups")
        ],
        [
            InlineKeyboardButton("👥 Watchlist", callback_data="watchlist"),
            InlineKeyboardButton("💬 Messages", callback_data="messages")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def create_admin_menu_keyboard():
    """Create admin management keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Group", callback_data="add_group"),
            InlineKeyboardButton("➕ Add User", callback_data="add_user")
        ],
        [
            InlineKeyboardButton("🗑️ Remove Group", callback_data="remove_group"),
            InlineKeyboardButton("🗑️ Remove User", callback_data="remove_user")
        ],
        [
            InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_callback_query(callback_query) -> None:
    """Handle callback queries (button clicks)"""
    try:
        query_id = callback_query.id
        chat_id = str(callback_query.message.chat_id)
        user_id = str(callback_query.from_user.id)
        username = callback_query.from_user.username or ""
        data = callback_query.data
        
        logger.info(f"Callback query from @{username} (ID: {user_id}) in chat {chat_id}: {data}")
        
        # Answer the callback query to remove loading state
        await bot.answer_callback_query(callback_query_id=query_id)
        
        # Handle different callback data
        if data == "status":
            # Get statistics
            total_groups = await db.groups.count_documents({"is_active": True})
            total_users = await db.watchlist_users.count_documents({"is_active": True})
            total_messages = await db.message_logs.count_documents({})
            
            # Format timestamp without backslashes in f-string
            timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            status_text = f"""
*📊 Monitoring Status*

*Active Monitoring:*
• Groups: {total_groups}
• Watchlist Users: {total_users}
• Messages Logged: {total_messages}

*System Status:* ✅ Online

_Last updated: {escape_markdown_v2(timestamp_str)}_
            """
            keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]]
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "groups":
            groups = await db.groups.find({"is_active": True}).to_list(10)
            if not groups:
                groups_text = "*📁 Monitored Groups*\n\nNo groups are currently being monitored\\."
            else:
                groups_list = []
                for group_doc in groups:
                    group = Group(**group_doc)
                    groups_list.append(f"• {escape_markdown_v2(group.group_name)}")
                
                groups_text = f"""
*📁 Monitored Groups* \\({len(groups)}\\)

{chr(10).join(groups_list)}

Click 'Manage Groups' for more options\\.
                """
            
            keyboard = [
                [InlineKeyboardButton("⚙️ Manage Groups", callback_data="admin_menu")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
            ]
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=groups_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "watchlist":
            users = await db.watchlist_users.find({"is_active": True}).to_list(10)
            if not users:
                watchlist_text = "*👥 Watchlist Users*\n\nNo users are currently being monitored\\."
            else:
                users_list = []
                for user_doc in users:
                    user = WatchlistUser(**user_doc)
                    scope = "Global" if not user.group_ids else f"{len(user.group_ids)} groups"
                    users_list.append(f"• @{escape_markdown_v2(user.username)} \\({scope}\\)")
                
                watchlist_text = f"""
*👥 Watchlist Users* \\({len(users)}\\)

{chr(10).join(users_list)}

Click 'Manage Users' for more options\\.
                """
            
            keyboard = [
                [InlineKeyboardButton("⚙️ Manage Users", callback_data="admin_menu")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
            ]
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=watchlist_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "messages":
            recent_messages = await db.message_logs.find().sort("timestamp", -1).limit(5).to_list(5)
            
            if not recent_messages:
                messages_text = "*💬 Recent Messages*\n\nNo messages logged yet\\."
            else:
                messages_list = []
                for msg_doc in recent_messages:
                    msg = MessageLog(**msg_doc)
                    timestamp = msg.timestamp.strftime('%m-%d %H:%M')
                    text_preview = msg.message_text[:30] + "..." if msg.message_text and len(msg.message_text) > 30 else msg.message_text or f"[{msg.message_type}]"
                    messages_list.append(f"• {timestamp} @{escape_markdown_v2(msg.username)}: {escape_markdown_v2(text_preview)}")
                
                messages_text = f"""
*💬 Recent Messages* \\({len(recent_messages)}\\)

{chr(10).join(messages_list)}

Use the web dashboard for detailed search\\.
                """
            
            keyboard = [
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
            ]
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=messages_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "settings":
            settings_text = """
*⚙️ Bot Settings*

*Current Configuration:*
• Webhook: ✅ Active
• Monitoring: ✅ Online
• Database: ✅ Connected

*Web Dashboard:*
Use the dashboard for advanced settings and configuration\\.

*Support:*
Contact support for issues or questions\\.
            """
            
            keyboard = [
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
            ]
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=settings_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "help":
            help_text = """
*ℹ️ Help & Information*

*🤖 About This Bot:*
This bot monitors Telegram groups and tracks messages from specific users based on your watchlist\\.

*📋 Main Features:*
• Monitor multiple Telegram groups
• Track specific users \\(watchlist\\)
• Filter by keywords
• Log all monitored messages
• Web dashboard for management

*🌐 Web Dashboard:*
For full management capabilities, use the web dashboard\\. You can add/remove groups, manage watchlists, search messages, and view detailed analytics\\.

*🔧 Getting Started:*
1\\. Add groups to monitor
2\\. Add users to watchlist
3\\. Configure keywords \\(optional\\)
4\\. Start monitoring\\!
            """
            
            keyboard = [
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")]
            ]
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=help_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "admin_menu":
            admin_text = """
*⚙️ Administration Menu*

*Quick Actions:*
Use the buttons below for basic management, or use the web dashboard for advanced features\\.

*Note:* For detailed configuration, group management, and user watchlists, please use the web dashboard\\.
            """
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=admin_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=await create_admin_menu_keyboard()
            )
            
        elif data == "main_menu":
            welcome_text = """
*🤖 Telegram Monitor Bot*

Welcome to the Telegram Monitoring System\\!

Choose an option below to get started:

*📊 Status* \\- View current monitoring statistics
*📁 Groups* \\- See monitored groups
*👥 Watchlist* \\- View watched users
*💬 Messages* \\- Recent logged messages
*⚙️ Settings* \\- Bot configuration
*ℹ️ Help* \\- Information and support

For full management, use the web dashboard\\.
            """
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=await create_main_menu_keyboard()
            )
            
        elif data.startswith("add_") or data.startswith("remove_"):
            info_text = """
*🌐 Use Web Dashboard*

For adding/removing groups and users, please use the web dashboard where you have full management capabilities:

• Complete group management
• User watchlist configuration  
• Keyword filtering setup
• Message search and analytics
• And much more\\!
            """
            
            keyboard = [
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")]
            ]
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text=info_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        else:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback_query.message.message_id,
                text="Unknown action\\. Please try again\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=await create_main_menu_keyboard()
            )
            
        logger.info(f"✅ Processed callback query '{data}' from {username}")
            
    except Exception as e:
        logger.error(f"❌ Error handling callback query '{data}': {e}", exc_info=True)

async def handle_telegram_message(update: Update) -> None:
    """Process incoming Telegram messages"""
    try:
        logger.info(f"Processing telegram update: {update.update_id}")
        
        # Handle callback queries (button clicks)
        if update.callback_query:
            await handle_callback_query(update.callback_query)
            return
        
        message = update.message
        if not message:
            logger.info("No message in update, skipping")
            return
        
        # Extract message info
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        username = message.from_user.username or ""
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        message_text = message.text or message.caption or ""
        
        logger.info(f"Message from @{username} (ID: {user_id}) in chat {chat_id}: {message_text[:100]}...")
        
        # Determine message type
        message_type = "text"
        media_info = {}
        
        if message.photo:
            message_type = "photo"
            media_info = {"file_id": message.photo[-1].file_id, "file_size": message.photo[-1].file_size}
        elif message.video:
            message_type = "video"
            media_info = {"file_id": message.video.file_id, "file_size": message.video.file_size, "duration": message.video.duration}
        elif message.document:
            message_type = "document"
            media_info = {"file_id": message.document.file_id, "file_name": message.document.file_name, "file_size": message.document.file_size}
        elif message.audio:
            message_type = "audio"
            media_info = {"file_id": message.audio.file_id, "duration": message.audio.duration}
        elif message.voice:
            message_type = "voice"
            media_info = {"file_id": message.voice.file_id, "duration": message.voice.duration}
        elif message.sticker:
            message_type = "sticker"
            media_info = {"file_id": message.sticker.file_id, "emoji": message.sticker.emoji}
        
        # Check if it's a bot command
        if message_text.startswith('/'):
            logger.info(f"Processing bot command: {message_text}")
            await handle_bot_command(message)
            return
        
        # Check if group is monitored
        group_doc = await db.groups.find_one({"group_id": chat_id, "is_active": True})
        if not group_doc:
            logger.info(f"Chat {chat_id} is not in monitored groups, ignoring message")
            return
        
        group = Group(**group_doc)
        logger.info(f"Message in monitored group: {group.group_name}")
        
        # Check if user is in watchlist
        monitored_user = await check_if_user_monitored(user_id, username, chat_id)
        if not monitored_user:
            logger.info(f"User @{username} is not in watchlist, ignoring message")
            return
        
        logger.info(f"Message from monitored user @{username} detected!")
        
        # Check keyword matching if specified
        matched_keywords = []
        if monitored_user.keywords:
            matched_keywords = await check_keyword_match(message_text, monitored_user.keywords)
            if not matched_keywords:
                logger.info(f"No keyword matches found for user @{username}, ignoring message")
                return  # No keyword match, don't forward
        
        logger.info(f"Message will be logged with keywords: {matched_keywords}")
        
        # Log the message
        message_log = MessageLog(
            message_id=str(message.message_id),
            group_id=chat_id,
            group_name=group.group_name,
            user_id=user_id,
            username=username,
            user_full_name=full_name,
            message_text=message_text,
            message_type=message_type,
            media_info=media_info,
            matched_keywords=matched_keywords
        )
        
        await db.message_logs.insert_one(message_log.dict())
        
        # Forward the message to configured destinations
        forwarding_results = await forward_message_to_destinations(
            message_text=message_text,
            message_type=message_type,
            username=username,
            group_name=group.group_name,
            matched_keywords=matched_keywords,
            timestamp=datetime.now(timezone.utc),
            destinations=monitored_user.forwarding_destinations,
            media_info=media_info
        )
        
        # Update message log with forwarding results
        await db.message_logs.update_one(
            {"id": message_log.id},
            {
                "$set": {
                    "is_forwarded": forwarding_results["success_count"] > 0,
                    "forwarded_count": forwarding_results["success_count"]
                }
            }
        )
        
        # Create forwarded message record if successful
        if forwarding_results["success_count"] > 0:
            forwarded_message = ForwardedMessage(
                original_message_id=str(message.message_id),
                from_group_id=chat_id,
                from_group_name=group.group_name,
                from_user_id=user_id,
                from_username=username,
                from_user_full_name=full_name,
                message_text=message_text,
                message_type=message_type,
                media_info=media_info,
                forwarded_to_destinations=monitored_user.forwarding_destinations,
                matched_keywords=matched_keywords,
                forwarding_status="success" if forwarding_results["failed_count"] == 0 else "partial",
                error_details="; ".join(forwarding_results["errors"]) if forwarding_results["errors"] else None
            )
            
            await db.forwarded_messages.insert_one(forwarded_message.dict())
        
        # Log success with forwarding info
        if forwarding_results["success_count"] > 0:
            destinations_str = ", ".join(forwarding_results["forwarded_to"])
            logger.info(f"✅ Successfully logged and forwarded message from {username} to {forwarding_results['success_count']} destinations: {destinations_str}")
        else:
            logger.info(f"✅ Successfully logged message from monitored user {username} in group {group.group_name} (no forwarding destinations configured)")
        
        if forwarding_results["errors"]:
            logger.warning(f"⚠️ Forwarding errors: {'; '.join(forwarding_results['errors'])}")
        
    except Exception as e:
        logger.error(f"❌ Error handling Telegram message: {e}", exc_info=True)

async def handle_bot_command(message) -> None:
    """Handle bot commands"""
    try:
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        username = message.from_user.username or ""
        command_text = message.text
        
        logger.info(f"Processing command '{command_text}' from @{username} (ID: {user_id}) in chat {chat_id}")
        
        # Log the command
        bot_command = BotCommand(
            command=command_text,
            chat_id=chat_id,
            user_id=user_id,
            username=username
        )
        await db.bot_commands.insert_one(bot_command.dict())
        
        # Handle different commands - now primarily /start to show the main menu
        if command_text in ['/start', '/menu', '/help']:
            welcome_text = """
*🤖 Telegram Monitor Bot*

Welcome to the Telegram Monitoring System\\!

Choose an option below to get started:

*📊 Status* \\- View current monitoring statistics
*📁 Groups* \\- See monitored groups
*👥 Watchlist* \\- View watched users
*💬 Messages* \\- Recent logged messages
*⚙️ Settings* \\- Bot configuration
*ℹ️ Help* \\- Information and support

For full management, use the web dashboard\\.
            """
            
            await bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=await create_main_menu_keyboard()
            )
            logger.info(f"✅ Sent main menu to {username}")
        
        else:
            # For any other command, show the main menu
            await bot.send_message(
                chat_id=chat_id,
                text="Use the buttons below to navigate the bot\\. For full management, use the web dashboard\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=await create_main_menu_keyboard()
            )
            logger.info(f"✅ Sent main menu for unknown command to {username}")
    
    except Exception as e:
        logger.error(f"❌ Error handling bot command '{command_text}': {e}", exc_info=True)

# ================== UPDATED API ROUTES (With Multi-tenancy) ==================

# Group Management Routes (Updated)
@api_router.post("/groups", response_model=Group)
async def create_group(group: GroupCreate, current_user: Dict = Depends(require_admin)):
    """Add a new group to monitor (Admin/Owner only)"""
    try:
        # Check if group already exists for this tenant
        existing = await db.groups.find_one({
            "tenant_id": current_user["organization_id"],
            "group_id": group.group_id
        })
        if existing:
            raise HTTPException(status_code=400, detail="Group already exists")
        
        new_group = Group(
            tenant_id=current_user["organization_id"],
            created_by=current_user["user_id"],
            **group.dict()
        )
        await db.groups.insert_one(new_group.dict())
        return new_group
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create group: {str(e)}")

@api_router.get("/groups", response_model=List[Group])
async def get_groups(current_user: Dict = Depends(get_current_active_user)):
    """Get all monitored groups for current organization"""
    groups = await db.groups.find({
        "tenant_id": current_user["organization_id"],
        "is_active": True
    }).to_list(100)
    return [Group(**group) for group in groups]

@api_router.get("/groups/{group_id}", response_model=Group)
async def get_group(group_id: str):
    """Get specific group details"""
    group = await db.groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return Group(**group)

@api_router.put("/groups/{group_id}", response_model=Group)
async def update_group(group_id: str, group_update: GroupCreate):
    """Update group details"""
    group = await db.groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    update_data = group_update.dict()
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.groups.update_one({"id": group_id}, {"$set": update_data})
    updated_group = await db.groups.find_one({"id": group_id})
    return Group(**updated_group)

@api_router.delete("/groups/{group_id}")
async def delete_group(group_id: str):
    """Remove group from monitoring"""
    result = await db.groups.update_one(
        {"id": group_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"message": "Group removed from monitoring"}

# Watchlist Management Routes
@api_router.post("/watchlist", response_model=WatchlistUser)
async def create_watchlist_user(user: WatchlistUserCreate):
    """Add user to watchlist"""
    try:
        # Check if user already exists
        existing = await db.watchlist_users.find_one({"username": user.username.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="User already in watchlist")
        
        new_user = WatchlistUser(**user.dict())
        new_user.username = new_user.username.lower()
        await db.watchlist_users.insert_one(new_user.dict())
        return new_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add user: {str(e)}")

@api_router.get("/watchlist", response_model=List[WatchlistUser])
async def get_watchlist_users():
    """Get all watchlist users"""
    users = await db.watchlist_users.find({"is_active": True}).to_list(100)
    return [WatchlistUser(**user) for user in users]

@api_router.get("/watchlist/{user_id}", response_model=WatchlistUser)
async def get_watchlist_user(user_id: str):
    """Get specific watchlist user"""
    user = await db.watchlist_users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return WatchlistUser(**user)

@api_router.put("/watchlist/{user_id}", response_model=WatchlistUser)
async def update_watchlist_user(user_id: str, user_update: WatchlistUserCreate):
    """Update watchlist user"""
    user = await db.watchlist_users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict()
    update_data["username"] = update_data["username"].lower()
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.watchlist_users.update_one({"id": user_id}, {"$set": update_data})
    updated_user = await db.watchlist_users.find_one({"id": user_id})
    return WatchlistUser(**updated_user)

@api_router.delete("/watchlist/{user_id}")
async def delete_watchlist_user(user_id: str):
    """Remove user from watchlist"""
    result = await db.watchlist_users.update_one(
        {"id": user_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User removed from watchlist"}

# Forwarding Destinations Routes
@api_router.post("/forwarding-destinations", response_model=ForwardingDestination)
async def create_forwarding_destination(destination: ForwardingDestinationCreate):
    """Add a new forwarding destination"""
    try:
        # Check if destination already exists
        existing = await db.forwarding_destinations.find_one({"destination_id": destination.destination_id})
        if existing:
            raise HTTPException(status_code=400, detail="Forwarding destination already exists")
        
        new_destination = ForwardingDestination(**destination.dict())
        await db.forwarding_destinations.insert_one(new_destination.dict())
        return new_destination
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create forwarding destination: {str(e)}")

@api_router.get("/forwarding-destinations", response_model=List[ForwardingDestination])
async def get_forwarding_destinations():
    """Get all forwarding destinations"""
    destinations = await db.forwarding_destinations.find({"is_active": True}).to_list(100)
    return [ForwardingDestination(**dest) for dest in destinations]

@api_router.get("/forwarding-destinations/{destination_id}", response_model=ForwardingDestination)
async def get_forwarding_destination(destination_id: str):
    """Get specific forwarding destination"""
    destination = await db.forwarding_destinations.find_one({"id": destination_id})
    if not destination:
        raise HTTPException(status_code=404, detail="Forwarding destination not found")
    return ForwardingDestination(**destination)

@api_router.put("/forwarding-destinations/{destination_id}", response_model=ForwardingDestination)
async def update_forwarding_destination(destination_id: str, destination_update: ForwardingDestinationCreate):
    """Update forwarding destination"""
    destination = await db.forwarding_destinations.find_one({"id": destination_id})
    if not destination:
        raise HTTPException(status_code=404, detail="Forwarding destination not found")
    
    update_data = destination_update.dict()
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.forwarding_destinations.update_one({"id": destination_id}, {"$set": update_data})
    updated_destination = await db.forwarding_destinations.find_one({"id": destination_id})
    return ForwardingDestination(**updated_destination)

@api_router.delete("/forwarding-destinations/{destination_id}")
async def delete_forwarding_destination(destination_id: str):
    """Remove forwarding destination"""
    result = await db.forwarding_destinations.update_one(
        {"id": destination_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Forwarding destination not found")
    return {"message": "Forwarding destination removed"}

@api_router.post("/forwarding-destinations/{destination_id}/test")
async def test_forwarding_destination(destination_id: str):
    """Test a forwarding destination by sending a test message"""
    destination = await db.forwarding_destinations.find_one({"id": destination_id})
    if not destination:
        raise HTTPException(status_code=404, detail="Forwarding destination not found")
    
    dest_obj = ForwardingDestination(**destination)
    
    try:
        test_message = f"""
🧪 *Test Message*

This is a test message from your Telegram Monitor Bot\\.

*Destination:* {escape_markdown_v2(dest_obj.destination_name)}
*Type:* {escape_markdown_v2(dest_obj.destination_type.title())}
*Time:* {escape_markdown_v2(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))}

If you see this message, the forwarding destination is working correctly\\! ✅
        """
        
        await bot.send_message(
            chat_id=dest_obj.destination_id,
            text=test_message,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
        return {"status": "success", "message": "Test message sent successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test message: {str(e)}")

# Forwarded Messages Routes
@api_router.get("/forwarded-messages", response_model=List[ForwardedMessage])
async def get_forwarded_messages(
    limit: int = 50,
    skip: int = 0,
    username: Optional[str] = None,
    destination_id: Optional[str] = None
):
    """Get forwarded messages with filtering"""
    query = {}
    if username:
        query["from_username"] = {"$regex": username, "$options": "i"}
    if destination_id:
        query["forwarded_to_destinations"] = {"$in": [destination_id]}
    
    messages = await db.forwarded_messages.find(query).sort("forwarded_at", -1).skip(skip).limit(limit).to_list(limit)
    return [ForwardedMessage(**msg) for msg in messages]

# Message Logs Routes
@api_router.get("/messages", response_model=List[MessageLog])
async def get_message_logs(
    limit: int = 50,
    skip: int = 0,
    group_id: Optional[str] = None,
    username: Optional[str] = None,
    message_type: Optional[str] = None
):
    """Get message logs with filtering"""
    query = {}
    if group_id:
        query["group_id"] = group_id
    if username:
        query["username"] = {"$regex": username, "$options": "i"}
    if message_type:
        query["message_type"] = message_type
    
    messages = await db.message_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    return [MessageLog(**msg) for msg in messages]

@api_router.get("/messages/search")
async def search_messages(
    q: str,
    limit: int = 50,
    skip: int = 0
):
    """Search messages by text content"""
    query = {
        "$or": [
            {"message_text": {"$regex": q, "$options": "i"}},
            {"username": {"$regex": q, "$options": "i"}},
            {"group_name": {"$regex": q, "$options": "i"}}
        ]
    }
    
    messages = await db.message_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.message_logs.count_documents(query)
    
    return {
        "messages": [MessageLog(**msg) for msg in messages],
        "total": total,
        "limit": limit,
        "skip": skip
    }

# Statistics Routes
@api_router.get("/stats")
async def get_statistics():
    """Get system statistics"""
    stats = {
        "total_groups": await db.groups.count_documents({"is_active": True}),
        "total_watchlist_users": await db.watchlist_users.count_documents({"is_active": True}),
        "total_forwarding_destinations": await db.forwarding_destinations.count_documents({"is_active": True}),
        "total_messages": await db.message_logs.count_documents({}),
        "total_forwarded": await db.message_logs.count_documents({"is_forwarded": True}),
        "forwarding_success_rate": 0,
        "messages_today": await db.message_logs.count_documents({
            "timestamp": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
        }),
        "forwarded_today": await db.forwarded_messages.count_documents({
            "forwarded_at": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
        }),
        "last_updated": datetime.now(timezone.utc)
    }
    
    # Calculate forwarding success rate
    if stats["total_messages"] > 0:
        stats["forwarding_success_rate"] = round((stats["total_forwarded"] / stats["total_messages"]) * 100, 1)
    
    # Get top active users
    pipeline = [
        {"$group": {"_id": "$username", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_users = await db.message_logs.aggregate(pipeline).to_list(10)
    stats["top_users"] = top_users
    
    # Get message types distribution
    pipeline = [
        {"$group": {"_id": "$message_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    message_types = await db.message_logs.aggregate(pipeline).to_list(10)
    stats["message_types"] = message_types
    
    # Get forwarding destinations statistics
    pipeline = [
        {"$match": {"is_active": True}},
        {"$project": {"destination_name": 1, "message_count": 1, "last_forwarded": 1}},
        {"$sort": {"message_count": -1}},
        {"$limit": 10}
    ]
    top_destinations = await db.forwarding_destinations.aggregate(pipeline).to_list(10)
    stats["top_destinations"] = top_destinations
    
    # Get recent forwarding activity
    recent_forwards = await db.forwarded_messages.find().sort("forwarded_at", -1).limit(5).to_list(5)
    stats["recent_forwards"] = [
        {
            "username": msg["from_username"],
            "group_name": msg["from_group_name"],
            "forwarded_at": msg["forwarded_at"],
            "destination_count": len(msg["forwarded_to_destinations"])
        }
        for msg in recent_forwards
    ]
    
    return stats

# Telegram polling function
async def start_polling():
    """Start polling for Telegram updates as a fallback"""
    global last_update_id, polling_task
    
    try:
        logger.info("Starting Telegram polling...")
        while True:
            try:
                updates = await bot.get_updates(offset=last_update_id + 1, timeout=30)
                
                for update in updates:
                    try:
                        last_update_id = update.update_id
                        logger.info(f"Processing update {update.update_id} from polling")
                        await handle_telegram_message(update)
                    except Exception as e:
                        logger.error(f"Error processing polling update {update.update_id}: {e}")
                        
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
                
    except asyncio.CancelledError:
        logger.info("Polling task cancelled")
    except Exception as e:
        logger.error(f"Polling task failed: {e}")

# Telegram Webhook Route
@api_router.post("/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request, background_tasks: BackgroundTasks):
    """Handle Telegram webhook updates"""
    logger.info(f"Webhook called with secret: {secret[:10]}...")
    
    if secret != os.environ.get('WEBHOOK_SECRET'):
        logger.warning(f"Invalid webhook secret provided: {secret[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    try:
        update_data = await request.json()
        logger.info(f"Received webhook data: {json.dumps(update_data, indent=2)}")
        
        update = Update.de_json(update_data, bot)
        logger.info(f"Parsed update: {update.update_id}")
        
        # Process in background to avoid blocking
        background_tasks.add_task(handle_telegram_message, update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

# Control Routes for Bot Management
@api_router.post("/telegram/start-polling")
async def start_bot_polling():
    """Start polling mode (useful for development)"""
    global polling_task
    
    if polling_task and not polling_task.done():
        return {"status": "already_running", "message": "Polling is already active"}
    
    # Stop webhook first
    try:
        await bot.delete_webhook()
        logger.info("Webhook deleted, starting polling mode")
        
        polling_task = asyncio.create_task(start_polling())
        return {"status": "started", "message": "Polling mode started"}
    except Exception as e:
        logger.error(f"Failed to start polling: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start polling: {str(e)}")

@api_router.post("/telegram/stop-polling")
async def stop_bot_polling():
    """Stop polling mode"""
    global polling_task
    
    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        
        return {"status": "stopped", "message": "Polling mode stopped"}
    
    return {"status": "not_running", "message": "Polling was not active"}

@api_router.post("/telegram/set-webhook")
async def set_webhook():
    """Set webhook for production mode"""
    webhook_url = f"https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com/api/telegram/webhook/{os.environ.get('WEBHOOK_SECRET')}"
    
    try:
        # Stop polling if running
        global polling_task
        if polling_task and not polling_task.done():
            polling_task.cancel()
        
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
        
        return {"status": "success", "webhook_url": webhook_url}
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set webhook: {str(e)}")

# ================== AUTHENTICATION ROUTES ==================

@api_router.post("/auth/telegram", response_model=TokenResponse)
async def telegram_auth(auth_data: TelegramAuthData):
    """Authenticate user with Telegram Login Widget"""
    try:
        # Verify Telegram authentication data
        auth_dict = auth_data.dict()
        if not verify_telegram_authentication(auth_dict):
            raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")
        
        # Check if user already exists
        existing_user = await db.users.find_one({"telegram_id": auth_data.id})
        
        if existing_user:
            # User exists, log them in
            user = User(**existing_user)
            
            # Update last login and user info from Telegram
            update_data = {
                "last_login": datetime.now(timezone.utc),
                "username": auth_data.username,
                "first_name": auth_data.first_name,
                "last_name": auth_data.last_name,
                "photo_url": auth_data.photo_url,
                "updated_at": datetime.now(timezone.utc)
            }
            
            await db.users.update_one({"id": user.id}, {"$set": update_data})
            
            # Create access token
            access_token = create_access_token(user.id, user.organization_id, user.role.value)
            
            # Return response with updated user data
            user_response = UserResponse(
                id=user.id,
                telegram_id=user.telegram_id,
                username=auth_data.username,
                first_name=auth_data.first_name,
                last_name=auth_data.last_name,
                full_name=user.full_name,
                photo_url=auth_data.photo_url,
                is_active=user.is_active,
                role=user.role,
                organization_id=user.organization_id,
                created_at=user.created_at,
                last_login=datetime.now(timezone.utc)
            )
            
            return TokenResponse(
                access_token=access_token,
                expires_in=JWT_EXPIRATION_HOURS * 3600,
                user=user_response
            )
        else:
            # New user, needs to complete registration with organization
            raise HTTPException(status_code=404, detail="User not found. Please complete registration first.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@api_router.post("/auth/register", response_model=TokenResponse)
async def register_telegram_user(user_data: UserCreate):
    """Register a new user with Telegram data and create organization"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"telegram_id": user_data.telegram_id})
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this Telegram ID already exists")
        
        # Create organization if provided
        organization_id = None
        if user_data.organization_name:
            # Check if organization name is taken
            existing_org = await db.organizations.find_one({"name": user_data.organization_name})
            if existing_org:
                raise HTTPException(status_code=400, detail="Organization name already taken")
            
            # Create new organization  
            full_name = user_data.last_name and f"{user_data.first_name} {user_data.last_name}" or user_data.first_name
            organization = Organization(
                name=user_data.organization_name,
                description=f"Organization for {full_name}"
            )
            await db.organizations.insert_one(organization.dict())
            organization_id = organization.id
        else:
            raise HTTPException(status_code=400, detail="Organization name is required")
        
        # Create user
        user = User(
            telegram_id=user_data.telegram_id,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            photo_url=user_data.photo_url,
            role=UserRole.OWNER,  # First user in org is owner
            organization_id=organization_id
        )
        
        await db.users.insert_one(user.dict())
        
        # Create access token
        access_token = create_access_token(user.id, organization_id, user.role.value)
        
        # Return response
        user_response = UserResponse(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            photo_url=user.photo_url,
            is_active=user.is_active,
            role=user.role,
            organization_id=user.organization_id,
            created_at=user.created_at
        )
        
        return TokenResponse(
            access_token=access_token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user=user_response
        )
        
    except Exception as e:
        if "already exists" in str(e) or "already taken" in str(e) or "required" in str(e):
            raise e
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@api_router.post("/auth/login", response_model=TokenResponse)
async def login_user(user_credentials: UserLogin):
    """Legacy login endpoint - deprecated in favor of Telegram auth"""
    raise HTTPException(status_code=410, detail="Email/password login has been replaced with Telegram authentication. Please use Telegram Login Widget.")

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_active_user)):
    """Get current user information"""
    user = current_user["user"]
    return UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        photo_url=user.photo_url,
        is_active=user.is_active,
        role=user.role,
        organization_id=user.organization_id,
        created_at=user.created_at,
        last_login=user.last_login
    )

# ================== ORGANIZATION MANAGEMENT ROUTES ==================

@api_router.get("/organizations/current")
async def get_current_organization(current_user: Dict = Depends(get_current_active_user)):
    """Get current user's organization"""
    org_doc = await db.organizations.find_one({"id": current_user["organization_id"]})
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")
    return Organization(**org_doc)

@api_router.put("/organizations/current")
async def update_current_organization(
    org_update: OrganizationCreate,
    current_user: Dict = Depends(require_admin)
):
    """Update current organization (Admin/Owner only)"""
    result = await db.organizations.update_one(
        {"id": current_user["organization_id"]},
        {"$set": {
            "name": org_update.name,
            "description": org_update.description,
            "plan": org_update.plan,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    updated_org = await db.organizations.find_one({"id": current_user["organization_id"]})
    return Organization(**updated_org)

# ================== USER MANAGEMENT ROUTES ==================

@api_router.get("/users", response_model=List[UserResponse])
async def list_organization_users(current_user: Dict = Depends(get_current_active_user)):
    """List all users in current organization"""
    users = await db.users.find({
        "organization_id": current_user["organization_id"],
        "is_active": True
    }).to_list(100)
    
    return [
        UserResponse(
            id=user["id"],
            telegram_id=user["telegram_id"],
            username=user.get("username"),
            first_name=user["first_name"],
            last_name=user.get("last_name"),
            full_name=user.get("last_name") and f"{user['first_name']} {user['last_name']}" or user["first_name"],
            photo_url=user.get("photo_url"),
            is_active=user["is_active"],
            role=UserRole(user["role"]),
            organization_id=user["organization_id"],
            created_at=user["created_at"],
            last_login=user.get("last_login")
        )
        for user in users
    ]

@api_router.post("/users/invite", response_model=UserResponse)
async def invite_user(
    invite_data: UserInvite,
    current_user: Dict = Depends(require_admin)
):
    """Invite a new user to the organization (Admin/Owner only) - Telegram-based system"""
    # For Telegram-based authentication, we cannot create users without their Telegram data
    # This endpoint now serves as a placeholder for future invite system
    raise HTTPException(
        status_code=501, 
        detail="User invitation system not implemented for Telegram authentication. Users must register themselves using Telegram Login Widget."
    )

@api_router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    current_user: Dict = Depends(require_owner)
):
    """Update user role (Owner only)"""
    # Can't change own role
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    result = await db.users.update_one(
        {
            "id": user_id,
            "organization_id": current_user["organization_id"],
            "is_active": True
        },  
        {"$set": {"role": new_role.value, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User role updated to {new_role.value}"}

@api_router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Deactivate user (Admin/Owner only)"""
    # Can't deactivate self
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    result = await db.users.update_one(
        {
            "id": user_id,
            "organization_id": current_user["organization_id"]
        },
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deactivated successfully"}

# ================== ACCOUNT MANAGEMENT ROUTES ==================

@api_router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(current_user: Dict = Depends(get_current_active_user)):
    """List all accounts in current organization"""
    accounts = await db.accounts.find({
        "organization_id": current_user["organization_id"],
        "is_active": True
    }).to_list(100)
    
    return [
        AccountResponse(
            id=account["id"],
            name=account["name"],
            phone_number=account.get("phone_number"),
            username=account.get("username"),
            first_name=account.get("first_name"),
            last_name=account.get("last_name"),
            status=AccountStatus(account["status"]),
            is_active=account["is_active"],
            last_activity=account.get("last_activity"),
            created_at=account["created_at"],
            error_message=account.get("error_message")
        )
        for account in accounts
    ]

@api_router.post("/accounts/upload", response_model=AccountResponse)
async def upload_account(
    name: str = Form(...),
    session_file: UploadFile = File(...),
    json_file: UploadFile = File(...),
    current_user: Dict = Depends(require_admin)
):
    """Upload account session and JSON files (Admin/Owner only)"""
    try:
        # Validate file extensions
        if not session_file.filename.endswith('.session'):
            raise HTTPException(status_code=400, detail="Session file must have .session extension")
        
        if not json_file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="JSON file must have .json extension")
        
        # Generate unique filenames
        account_id = str(uuid.uuid4())
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        session_filename = f"{current_user['organization_id']}_{account_id}_{timestamp}.session"
        json_filename = f"{current_user['organization_id']}_{account_id}_{timestamp}.json"
        
        session_path = SESSIONS_DIR / session_filename
        json_path = JSON_DIR / json_filename
        
        # Save session file
        async with aiofiles.open(session_path, 'wb') as f:
            content = await session_file.read()
            await f.write(content)
        
        # Save and parse JSON file
        json_content = await json_file.read()
        json_data = json.loads(json_content.decode('utf-8'))
        
        async with aiofiles.open(json_path, 'wb') as f:
            await f.write(json_content)
        
        # Extract account info from JSON
        phone_number = json_data.get('phone_number')
        username = json_data.get('username')
        first_name = json_data.get('first_name')
        last_name = json_data.get('last_name')
        
        # Create account record
        account = Account(
            id=account_id,
            organization_id=current_user["organization_id"],
            created_by=current_user["user_id"],
            name=name,
            phone_number=phone_number,
            username=username,
            first_name=first_name,
            last_name=last_name,
            status=AccountStatus.INACTIVE,
            session_file_path=str(session_path),
            json_file_path=str(json_path),
            metadata=json_data
        )
        
        await db.accounts.insert_one(account.dict())
        
        return AccountResponse(
            id=account.id,
            name=account.name,
            phone_number=account.phone_number,
            username=account.username,
            first_name=account.first_name,
            last_name=account.last_name,
            status=account.status,
            is_active=account.is_active,
            last_activity=account.last_activity,
            created_at=account.created_at,
            error_message=account.error_message
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file format")
    except Exception as e:
        # Cleanup files if account creation failed
        if session_path.exists():
            session_path.unlink()
        if json_path.exists():
            json_path.unlink()
        
        logger.error(f"Account upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Account upload failed: {str(e)}")

@api_router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Delete account and associated files (Admin/Owner only)"""
    try:
        # Find account
        account = await db.accounts.find_one({
            "id": account_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Delete files
        session_path = Path(account["session_file_path"])
        json_path = Path(account["json_file_path"])
        
        if session_path.exists():
            session_path.unlink()
        if json_path.exists():
            json_path.unlink()
        
        # Delete account record
        await db.accounts.delete_one({
            "id": account_id,
            "organization_id": current_user["organization_id"]
        })
        
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Account deletion failed: {str(e)}")

@api_router.post("/accounts/{account_id}/activate")
async def activate_account(
    account_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Activate account for monitoring (Admin/Owner only)"""
    try:
        # Find account
        account = await db.accounts.find_one({
            "id": account_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Update account status
        await db.accounts.update_one(
            {"id": account_id, "organization_id": current_user["organization_id"]},
            {
                "$set": {
                    "status": AccountStatus.ACTIVE.value,
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": None
                }
            }
        )
        
        return {"message": "Account activated successfully"}
        
    except Exception as e:
        logger.error(f"Account activation failed: {e}")
        
        # Update account with error
        await db.accounts.update_one(
            {"id": account_id, "organization_id": current_user["organization_id"]},
            {
                "$set": {
                    "status": AccountStatus.ERROR.value,
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": str(e)
                }
            }
        )
        
        raise HTTPException(status_code=500, detail=f"Account activation failed: {str(e)}")

@api_router.post("/accounts/{account_id}/deactivate")
async def deactivate_account(
    account_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Deactivate account monitoring (Admin/Owner only)"""
    try:
        result = await db.accounts.update_one(
            {"id": account_id, "organization_id": current_user["organization_id"]},
            {
                "$set": {
                    "status": AccountStatus.INACTIVE.value,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return {"message": "Account deactivated successfully"}
        
    except Exception as e:
        logger.error(f"Account deactivation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Account deactivation failed: {str(e)}")

# ================== TEST ROUTES ==================
@api_router.get("/")
async def root():
    return {"message": "Telegram Monitor Bot API", "version": "1.0.0"}

@api_router.post("/test/bot")
async def test_bot():
    """Test Telegram bot connection"""
    try:
        bot_info = await bot.get_me()
        return {
            "status": "success",
            "bot_info": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "is_bot": bot_info.is_bot
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bot connection failed: {str(e)}")

# Include the router in the main app - moved to end after all routes are defined

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def migrate_database_for_multitenancy():
    """Migrate existing data to support multi-tenancy"""
    logger.info("Running multi-tenancy database migration...")
    
    try:
        # Create a default organization for existing data
        default_org_id = "00000000-0000-0000-0000-000000000000"
        default_user_id = "00000000-0000-0000-0000-000000000001"
        
        # Check if default org exists
        existing_org = await db.organizations.find_one({"id": default_org_id})
        if not existing_org:
            default_org = Organization(
                id=default_org_id,
                name="Legacy Organization",
                description="Default organization for existing data",
                plan=OrganizationPlan.FREE
            )
            await db.organizations.insert_one(default_org.dict())
            logger.info("Created default organization for legacy data")
        
        # Migrate groups without tenant_id
        groups_updated = await db.groups.update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {
                "tenant_id": default_org_id,
                "created_by": default_user_id
            }}
        )
        if groups_updated.modified_count > 0:
            logger.info(f"Migrated {groups_updated.modified_count} groups to multi-tenancy")
        
        # Migrate watchlist_users without tenant_id
        users_updated = await db.watchlist_users.update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {
                "tenant_id": default_org_id,
                "created_by": default_user_id
            }}
        )
        if users_updated.modified_count > 0:
            logger.info(f"Migrated {users_updated.modified_count} watchlist users to multi-tenancy")
        
        # Migrate forwarding_destinations without tenant_id
        destinations_updated = await db.forwarding_destinations.update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {
                "tenant_id": default_org_id,
                "created_by": default_user_id
            }}
        )
        if destinations_updated.modified_count > 0:
            logger.info(f"Migrated {destinations_updated.modified_count} forwarding destinations to multi-tenancy")
        
        # Migrate message_logs without tenant_id
        messages_updated = await db.message_logs.update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {"tenant_id": default_org_id}}
        )
        if messages_updated.modified_count > 0:
            logger.info(f"Migrated {messages_updated.modified_count} message logs to multi-tenancy")
        
        # Migrate forwarded_messages without tenant_id
        forwarded_updated = await db.forwarded_messages.update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {"tenant_id": default_org_id}}
        )
        if forwarded_updated.modified_count > 0:
            logger.info(f"Migrated {forwarded_updated.modified_count} forwarded messages to multi-tenancy")
        
        logger.info("Multi-tenancy database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        # Don't fail startup, but log the error

# ================== TELETHON USER ACCOUNT MONITORING SYSTEM ==================

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from concurrent.futures import ThreadPoolExecutor

class UserAccountManager:
    """Manages multiple Telethon user account clients for monitoring"""
    
    def __init__(self):
        self.active_clients: Dict[str, TelegramClient] = {}
        self.client_sessions: Dict[str, dict] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.account_groups: Dict[str, Set[int]] = {}  # account_id -> set of group IDs
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    async def initialize_account_client(self, account_id: str, session_file_path: str, json_file_path: str):
        """Initialize Telethon client from uploaded session files"""
        try:
            # Read account metadata
            async with aiofiles.open(json_file_path, 'r') as f:
                content = await f.read()
                account_data = json.loads(content)
            
            # Get API credentials from environment
            api_id = int(os.environ.get('TELEGRAM_API_ID', '0'))
            api_hash = os.environ.get('TELEGRAM_API_HASH', '')
            
            if not api_id or not api_hash:
                logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment")
                return False
            
            # Read session file
            async with aiofiles.open(session_file_path, 'rb') as f:
                session_data = await f.read()
            
            # Convert binary session to string session (if needed)
            # For now, we'll assume the session file is compatible
            session_name = f"account_{account_id}"
            
            # Create client
            client = TelegramClient(
                session_file_path.replace('.session', ''),
                api_id,
                api_hash,
                device_model=account_data.get('device_model', 'TelegramMonitor'),
                app_version=account_data.get('app_version', '1.0.0')
            )
            
            # Connect and verify
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error(f"Account {account_id} session is not authorized")
                await client.disconnect()
                return False
            
            # Get user info
            me = await client.get_me()
            logger.info(f"Connected user account: {me.first_name} (@{me.username}) - ID: {me.id}")
            
            # Store client and metadata
            self.active_clients[account_id] = client
            self.client_sessions[account_id] = {
                'account_data': account_data,
                'user_info': {
                    'id': me.id,
                    'first_name': me.first_name,
                    'last_name': me.last_name,
                    'username': me.username,
                    'phone': me.phone
                }
            }
            
            # Update account status in database
            await db.accounts.update_one(
                {"id": account_id},
                {
                    "$set": {
                        "status": AccountStatus.ACTIVE.value,
                        "last_activity": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "error_message": None
                    }
                }
            )
            
            # Discover groups this account is member of
            await self.discover_account_groups(account_id)
            
            # Start monitoring
            await self.start_account_monitoring(account_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize account {account_id}: {e}")
            
            # Update account with error status
            await db.accounts.update_one(
                {"id": account_id},
                {
                    "$set": {
                        "status": AccountStatus.ERROR.value,
                        "updated_at": datetime.now(timezone.utc),
                        "error_message": str(e)
                    }
                }
            )
            return False
    
    async def discover_account_groups(self, account_id: str):
        """Discover all groups this account is a member of"""
        try:
            client = self.active_clients.get(account_id)
            if not client:
                return
            
            group_ids = set()
            
            # Get all dialogs (chats)
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    group_ids.add(dialog.id)
                    
                    # Check if this group is in our monitored groups
                    existing_group = await db.groups.find_one({
                        "group_id": str(dialog.id),
                        "is_active": True
                    })
                    
                    if not existing_group:
                        # Auto-add discovered groups for this account's organization
                        account_doc = await db.accounts.find_one({"id": account_id})
                        if account_doc:
                            group = Group(
                                group_id=str(dialog.id),
                                group_name=dialog.name or f"Group {dialog.id}",
                                group_type="group",
                                description=f"Auto-discovered from account {account_doc['name']}",
                                tenant_id=account_doc['organization_id'],
                                created_by=account_doc['created_by']
                            )
                            await db.groups.insert_one(group.dict())
                            logger.info(f"Auto-discovered group: {dialog.name} (ID: {dialog.id})")
            
            self.account_groups[account_id] = group_ids
            logger.info(f"Account {account_id} is member of {len(group_ids)} groups/channels")
            
        except Exception as e:
            logger.error(f"Failed to discover groups for account {account_id}: {e}")
    
    async def start_account_monitoring(self, account_id: str):
        """Start monitoring messages for this account"""
        try:
            client = self.active_clients.get(account_id)
            if not client:
                return
            
            # Set up event handlers for new messages
            @client.on(events.NewMessage)
            async def handle_new_message(event):
                await self.process_user_account_message(account_id, event)
            
            # Set up event handlers for message edits
            @client.on(events.MessageEdited)
            async def handle_edited_message(event):
                await self.process_user_account_message(account_id, event, is_edit=True)
            
            logger.info(f"Started monitoring for account {account_id}")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring for account {account_id}: {e}")
    
    async def process_user_account_message(self, account_id: str, event, is_edit=False):
        """Process messages from user accounts (replaces bot message processing)"""
        start_time = datetime.now(timezone.utc)
        
        try:
            message = event.message
            chat = await event.get_chat()
            sender = await event.get_sender()
            
            # Skip if not from a group/channel we're monitoring
            if not (chat.megagroup or chat.broadcast or hasattr(chat, 'participants_count')):
                return
            
            # Get account info
            account_doc = await db.accounts.find_one({"id": account_id})
            if not account_doc:
                return
            
            organization_id = account_doc['organization_id']
            
            # Check if this group is being monitored
            group_doc = await db.groups.find_one({
                "group_id": str(chat.id),
                "tenant_id": organization_id,
                "is_active": True
            })
            
            if not group_doc:
                return
            
            # Extract message data
            message_data = {
                'message_id': str(message.id),
                'group_id': str(chat.id),
                'group_name': getattr(chat, 'title', '') or getattr(chat, 'name', ''),
                'user_id': str(sender.id) if sender else 'Unknown',
                'username': getattr(sender, 'username', '') if sender else '',
                'first_name': getattr(sender, 'first_name', '') if sender else '',
                'last_name': getattr(sender, 'last_name', '') if sender else '',
                'message_text': message.text or '',
                'message_date': message.date,
                'is_edited': is_edit,
                'detected_by_account': account_id,
                'media_type': None,
                'file_path': None
            }
            
            # Handle media
            if message.media:
                media_type = self.get_media_type(message.media)
                message_data['media_type'] = media_type
                
                # Download media if configured
                if media_type and group_doc.get('download_media', False):
                    try:
                        file_path = await self.download_media(message, account_id, organization_id)
                        message_data['file_path'] = file_path
                    except Exception as e:
                        logger.error(f"Failed to download media: {e}")
            
            # Check watchlist filters
            should_process = await self.check_watchlist_filters(message_data, organization_id)
            
            if should_process:
                # Store message
                message_log = MessageLog(
                    message_id=message_data['message_id'],
                    group_id=message_data['group_id'],
                    group_name=message_data['group_name'],
                    user_id=message_data['user_id'],
                    username=message_data['username'],
                    first_name=message_data['first_name'],
                    last_name=message_data['last_name'],
                    message_text=message_data['message_text'],
                    message_date=message_data['message_date'],
                    tenant_id=organization_id,
                    created_by=account_doc['created_by'],
                    media_type=message_data['media_type'],
                    file_path=message_data['file_path'],
                    detected_by_account=account_id,
                    is_edited=is_edit
                )
                
                await db.message_logs.insert_one(message_log.dict())
                
                # Process forwarding with load balancing
                await self.process_message_forwarding_with_load_balancing(message_data, organization_id, account_id)
                
                # Update account activity
                await db.accounts.update_one(
                    {"id": account_id},
                    {
                        "$set": {
                            "last_activity": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
            
            # Record processing performance
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            load_balancer.record_message_processed(account_id, processing_time)
            
        except Exception as e:
            logger.error(f"Error processing message from account {account_id}: {e}")
    
    async def process_message_forwarding_with_load_balancing(self, message_data: dict, organization_id: str, detected_by_account: str):
        """Enhanced message forwarding with load balancing across accounts"""
        try:
            # Get forwarding destinations for this organization
            destinations = await db.forwarding_destinations.find({
                "tenant_id": organization_id,
                "is_active": True
            }).to_list(100)
            
            for destination in destinations:
                # Check if this message should be forwarded based on filters
                should_forward = True
                
                # Group filter
                if destination.get('source_groups') and message_data['group_id'] not in destination['source_groups']:
                    should_forward = False
                
                # User filter
                if should_forward and destination.get('user_filters'):
                    user_match = False
                    for user_filter in destination['user_filters']:
                        if (user_filter.get('user_id') == message_data['user_id'] or
                            user_filter.get('username') == message_data['username']):
                            user_match = True
                            break
                    if not user_match:
                        should_forward = False
                
                if should_forward:
                    # Use load balancer to select best account for forwarding
                    available_accounts = list(self.active_clients.keys())
                    best_account = load_balancer.get_best_account_for_forwarding(available_accounts)
                    
                    if best_account:
                        await self.forward_message_to_destination(message_data, destination, best_account)
                    else:
                        logger.warning("No available accounts for message forwarding")
            
        except Exception as e:
            logger.error(f"Error processing message forwarding with load balancing: {e}")
    
    async def forward_message_to_destination(self, message_data: dict, destination: dict, forwarding_account_id: str):
        """Enhanced message forwarding with better formatting and error handling"""
        try:
            client = self.active_clients.get(forwarding_account_id)
            if not client:
                logger.error(f"Forwarding account {forwarding_account_id} not available")
                return
            
            # Format forwarded message with more details
            forward_text = "🔍 **Monitored Message Alert**\n"
            forward_text += "=" * 30 + "\n\n"
            forward_text += f"📱 **Source Group:** {message_data['group_name']}\n"
            forward_text += f"👤 **User:** {message_data['first_name']} {message_data['last_name']}"
            
            if message_data['username']:
                forward_text += f" (@{message_data['username']})"
            forward_text += f"\n🆔 **User ID:** {message_data['user_id']}\n"
            forward_text += f"⏰ **Time:** {message_data['message_date'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            forward_text += f"🔍 **Detected by:** Account {forwarding_account_id}\n"
            
            if message_data['media_type']:
                forward_text += f"📎 **Media:** {message_data['media_type'].title()}\n"
            
            if message_data['is_edited']:
                forward_text += "✏️ **Message was edited**\n"
            
            forward_text += "\n" + "=" * 30 + "\n"
            forward_text += "💬 **Message Content:**\n\n"
            forward_text += message_data['message_text'] or "*No text content*"
            
            # Add rate limiting check
            rate_limit_key = f"forward_{destination['destination_id']}_{datetime.now().strftime('%Y%m%d%H%M')}"
            
            # Send to destination
            await client.send_message(
                entity=int(destination['destination_id']),
                message=forward_text
            )
            
            # Log forwarded message with enhanced data
            forwarded_log = ForwardedMessage(
                original_message_id=message_data['message_id'],
                source_group_id=message_data['group_id'],
                from_group_id=message_data['group_id'],  # For backward compatibility
                from_group_name=message_data['group_name'],
                from_user_id=message_data['user_id'],
                from_username=message_data['username'],
                from_user_full_name=f"{message_data['first_name']} {message_data['last_name']}".strip(),
                message_text=message_data['message_text'],
                message_type=message_data['media_type'] or 'text',
                media_info={'media_type': message_data['media_type']} if message_data['media_type'] else None,
                destination_chat_id=destination['destination_id'],
                destination_name=destination['destination_name'],
                forwarded_at=datetime.now(timezone.utc),
                tenant_id=destination['tenant_id'],
                created_by=destination['created_by'],
                forwarded_by_account=forwarding_account_id,
                detected_by_account=message_data['detected_by_account']
            )
            
            await db.forwarded_messages.insert_one(forwarded_log.dict())
            
            logger.debug(f"Message forwarded to {destination['destination_name']} via account {forwarding_account_id}")
            
        except Exception as e:
            logger.error(f"Error forwarding message via account {forwarding_account_id}: {e}")
            
            # Try with fallback account if available
            available_accounts = [aid for aid in self.active_clients.keys() if aid != forwarding_account_id]
            if available_accounts:
                fallback_account = available_accounts[0]
                logger.info(f"Retrying forward with fallback account {fallback_account}")
                await self.forward_message_to_destination(message_data, destination, fallback_account)
    async def check_watchlist_filters(self, message_data: dict, organization_id: str) -> bool:
        """Check if message matches watchlist filters"""
        try:
            # Get active watchlist users for this organization
            watchlist_users = await db.watchlist_users.find({
                "tenant_id": organization_id,
                "is_active": True
            }).to_list(100)
            
            for watchlist_user in watchlist_users:
                # Check user match
                user_matches = False
                
                if watchlist_user.get('user_id') == message_data['user_id']:
                    user_matches = True
                elif watchlist_user.get('username') and message_data['username']:
                    if watchlist_user['username'].lower() == message_data['username'].lower():
                        user_matches = True
                
                if user_matches:
                    # Check keywords if specified
                    keywords = watchlist_user.get('keywords', [])
                    if keywords:
                        message_text = message_data['message_text'].lower()
                        for keyword in keywords:
                            if keyword.lower() in message_text:
                                return True
                    else:
                        # No keyword filters, user match is enough
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking watchlist filters: {e}")
            return False
    
    def get_media_type(self, media) -> str:
        """Determine media type from Telethon media object"""
        try:
            from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
            
            if isinstance(media, MessageMediaPhoto):
                return 'photo'
            elif isinstance(media, MessageMediaDocument):
                if media.document.mime_type.startswith('video/'):
                    return 'video'
                elif media.document.mime_type.startswith('audio/'):
                    return 'audio'
                else:
                    return 'document'
            else:
                return 'other'
        except:
            return 'unknown'
    
    async def download_media(self, message, account_id: str, organization_id: str) -> str:
        """Download media from message"""
        try:
            # Create media directory
            media_dir = UPLOAD_DIR / "media" / organization_id / account_id
            media_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file
            file_path = await message.download_media(file=str(media_dir))
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None
    
    async def disconnect_account(self, account_id: str):
        """Disconnect and cleanup account client"""
        try:
            if account_id in self.active_clients:
                client = self.active_clients[account_id]
                await client.disconnect()
                del self.active_clients[account_id]
            
            if account_id in self.client_sessions:
                del self.client_sessions[account_id]
            
            if account_id in self.monitoring_tasks:
                task = self.monitoring_tasks[account_id]
                if not task.done():
                    task.cancel()
                del self.monitoring_tasks[account_id]
            
            if account_id in self.account_groups:
                del self.account_groups[account_id]
            
            # Update database status
            await db.accounts.update_one(
                {"id": account_id},
                {
                    "$set": {
                        "status": AccountStatus.INACTIVE.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            logger.info(f"Disconnected account {account_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting account {account_id}: {e}")
    
    async def get_account_status(self, account_id: str) -> dict:
        """Get detailed status of an account"""
        try:
            client = self.active_clients.get(account_id)
            if not client:
                return {"status": "inactive", "connected": False}
            
            is_connected = client.is_connected()
            user_info = self.client_sessions.get(account_id, {}).get('user_info', {})
            groups_count = len(self.account_groups.get(account_id, set()))
            
            return {
                "status": "active",
                "connected": is_connected,
                "user_info": user_info,
                "groups_count": groups_count,
                "last_seen": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Error getting account status {account_id}: {e}")
            return {"status": "error", "error": str(e)}

# Global account manager instance
account_manager = UserAccountManager()

# ================== PHASE 2: MULTI-ACCOUNT COORDINATION ==================

class AccountHealthMonitor:
    """Monitors health and performance of user accounts"""
    
    def __init__(self, account_manager: UserAccountManager):
        self.account_manager = account_manager
        self.health_stats: Dict[str, dict] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.health_check_interval = 300  # 5 minutes
        
    async def start_health_monitoring(self):
        """Start continuous health monitoring"""
        self.monitoring_task = asyncio.create_task(self._health_monitoring_loop())
        logger.info("Started account health monitoring")
        
    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped account health monitoring")
        
    async def _health_monitoring_loop(self):
        """Continuous health monitoring loop"""
        while True:
            try:
                await self._check_all_accounts_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
                
    async def _check_all_accounts_health(self):
        """Check health of all active accounts"""
        try:
            for account_id, client in self.account_manager.active_clients.items():
                await self._check_account_health(account_id, client)
        except Exception as e:
            logger.error(f"Error checking accounts health: {e}")
            
    async def _check_account_health(self, account_id: str, client: TelegramClient):
        """Check health of a specific account"""
        try:
            health_data = {
                'account_id': account_id,
                'timestamp': datetime.now(timezone.utc),
                'connected': False,
                'authorized': False,
                'response_time': None,
                'error_count': 0,
                'last_activity': None,
                'groups_accessible': 0
            }
            
            start_time = datetime.now(timezone.utc)
            
            # Check connection
            if client.is_connected():
                health_data['connected'] = True
                
                # Check authorization
                try:
                    health_data['authorized'] = await client.is_user_authorized()
                    
                    if health_data['authorized']:
                        # Test API response time
                        me = await client.get_me()
                        end_time = datetime.now(timezone.utc)
                        health_data['response_time'] = (end_time - start_time).total_seconds()
                        
                        # Check accessible groups
                        accessible_groups = 0
                        async for dialog in client.iter_dialogs(limit=10):
                            if dialog.is_group or dialog.is_channel:
                                accessible_groups += 1
                        health_data['groups_accessible'] = accessible_groups
                        
                except Exception as e:
                    logger.warning(f"Health check failed for account {account_id}: {e}")
                    health_data['error_count'] = 1
            
            # Update health stats
            self.health_stats[account_id] = health_data
            
            # Update database with health status
            await db.accounts.update_one(
                {"id": account_id},
                {
                    "$set": {
                        "last_health_check": datetime.now(timezone.utc),
                        "health_status": "healthy" if health_data['connected'] and health_data['authorized'] else "unhealthy",
                        "response_time": health_data['response_time'],
                        "groups_accessible": health_data['groups_accessible']
                    }
                }
            )
            
            # Auto-recovery for unhealthy accounts
            if not health_data['connected'] or not health_data['authorized']:
                await self._attempt_account_recovery(account_id)
                
        except Exception as e:
            logger.error(f"Error checking health for account {account_id}: {e}")
            
    async def _attempt_account_recovery(self, account_id: str):
        """Attempt to recover an unhealthy account"""
        try:
            logger.info(f"Attempting recovery for account {account_id}")
            
            # Get account info
            account_doc = await db.accounts.find_one({"id": account_id})
            if not account_doc:
                return
            
            # Disconnect current client if exists
            await self.account_manager.disconnect_account(account_id)
            
            # Wait a bit before reconnection
            await asyncio.sleep(10)
            
            # Attempt reconnection
            success = await self.account_manager.initialize_account_client(
                account_id,
                account_doc['session_file_path'],
                account_doc['json_file_path']
            )
            
            if success:
                logger.info(f"Successfully recovered account {account_id}")
            else:
                logger.warning(f"Failed to recover account {account_id}")
                
        except Exception as e:
            logger.error(f"Error during account recovery {account_id}: {e}")
    
    def get_health_summary(self) -> dict:
        """Get overall health summary"""
        try:
            total_accounts = len(self.health_stats)
            healthy_accounts = sum(1 for stats in self.health_stats.values() 
                                 if stats['connected'] and stats['authorized'])
            
            avg_response_time = None
            response_times = [stats['response_time'] for stats in self.health_stats.values() 
                            if stats['response_time'] is not None]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
            
            return {
                'total_accounts': total_accounts,
                'healthy_accounts': healthy_accounts,
                'unhealthy_accounts': total_accounts - healthy_accounts,
                'health_percentage': (healthy_accounts / total_accounts * 100) if total_accounts > 0 else 0,
                'average_response_time': avg_response_time,
                'last_check': max([stats['timestamp'] for stats in self.health_stats.values()]) if self.health_stats else None
            }
        except Exception as e:
            logger.error(f"Error getting health summary: {e}")
            return {'error': str(e)}

class AccountLoadBalancer:
    """Load balances message processing across multiple accounts"""
    
    def __init__(self, account_manager: UserAccountManager):
        self.account_manager = account_manager
        self.account_loads: Dict[str, int] = {}  # account_id -> message count
        self.account_performance: Dict[str, dict] = {}  # account_id -> performance metrics
        
    def record_message_processed(self, account_id: str, processing_time: float):
        """Record that an account processed a message"""
        try:
            self.account_loads[account_id] = self.account_loads.get(account_id, 0) + 1
            
            if account_id not in self.account_performance:
                self.account_performance[account_id] = {
                    'total_messages': 0,
                    'total_processing_time': 0,
                    'average_processing_time': 0,
                    'last_activity': datetime.now(timezone.utc)
                }
            
            perf = self.account_performance[account_id]
            perf['total_messages'] += 1
            perf['total_processing_time'] += processing_time
            perf['average_processing_time'] = perf['total_processing_time'] / perf['total_messages']
            perf['last_activity'] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error recording message processing for {account_id}: {e}")
    
    def get_best_account_for_forwarding(self, available_accounts: List[str]) -> Optional[str]:
        """Select the best account for forwarding based on load and performance"""
        try:
            if not available_accounts:
                return None
            
            best_account = None
            best_score = float('inf')
            
            for account_id in available_accounts:
                # Check if account is healthy
                if account_id not in self.account_manager.active_clients:
                    continue
                
                # Calculate load score (lower is better)
                current_load = self.account_loads.get(account_id, 0)
                avg_processing_time = self.account_performance.get(account_id, {}).get('average_processing_time', 1.0)
                
                # Score = load * processing_time (lower is better)
                score = current_load * avg_processing_time
                
                if score < best_score:
                    best_score = score
                    best_account = account_id
            
            return best_account
            
        except Exception as e:
            logger.error(f"Error selecting best account for forwarding: {e}")
            return available_accounts[0] if available_accounts else None
    
    def reset_load_counters(self):
        """Reset load counters (called periodically)"""
        self.account_loads.clear()
        logger.debug("Reset account load counters")
    
    def get_load_summary(self) -> dict:
        """Get load balancing summary"""
        try:
            return {
                'account_loads': self.account_loads.copy(),
                'account_performance': self.account_performance.copy(),
                'total_messages_processed': sum(self.account_loads.values())
            }
        except Exception as e:
            logger.error(f"Error getting load summary: {e}")
            return {'error': str(e)}

# ================== PHASE 3: ENHANCED FEATURES & ANALYTICS ==================

class GroupAutoDiscovery:
    """Auto-discovery and management of groups from user accounts"""
    
    def __init__(self, account_manager: UserAccountManager):
        self.account_manager = account_manager
        
    async def discover_all_groups_for_organization(self, organization_id: str) -> dict:
        """Discover all groups across all accounts for an organization"""
        try:
            # Get all accounts for this organization
            accounts = await db.accounts.find({
                "organization_id": organization_id,
                "status": AccountStatus.ACTIVE.value,
                "is_active": True
            }).to_list(100)
            
            discovered_groups = {}
            total_groups = 0
            
            for account in accounts:
                account_id = account['id']
                if account_id in self.account_manager.active_clients:
                    client = self.account_manager.active_clients[account_id]
                    
                    account_groups = []
                    async for dialog in client.iter_dialogs():
                        if dialog.is_group or dialog.is_channel:
                            group_info = {
                                'group_id': str(dialog.id),
                                'name': dialog.name or f"Group {dialog.id}",
                                'type': 'channel' if dialog.is_channel else 'group',
                                'participants_count': getattr(dialog.entity, 'participants_count', 0),
                                'discovered_by': account['name']
                            }
                            account_groups.append(group_info)
                            
                            # Check if group is already in database
                            existing = await db.groups.find_one({
                                "group_id": str(dialog.id),
                                "tenant_id": organization_id
                            })
                            
                            if not existing:
                                # Add to database
                                group = Group(
                                    group_id=str(dialog.id),
                                    group_name=dialog.name or f"Group {dialog.id}",
                                    group_type='channel' if dialog.is_channel else 'group',
                                    tenant_id=organization_id,
                                    created_by=account['created_by']
                                )
                                await db.groups.insert_one(group.dict())
                    
                    discovered_groups[account_id] = account_groups
                    total_groups += len(account_groups)
            
            return {
                'organization_id': organization_id,
                'total_accounts': len(accounts),
                'total_groups_discovered': total_groups,
                'groups_by_account': discovered_groups
            }
            
        except Exception as e:
            logger.error(f"Error during group discovery: {e}")
            return {'error': str(e)}

class AdvancedFiltering:
    """Advanced filtering system for per-account message processing"""
    
    @staticmethod
    async def create_account_filter(organization_id: str, account_id: str, filter_config: dict):
        """Create advanced filter for specific account"""
        try:
            filter_data = {
                'id': str(uuid.uuid4()),
                'organization_id': organization_id,
                'account_id': account_id,
                'name': filter_config.get('name', 'Unnamed Filter'),
                'description': filter_config.get('description', ''),
                'conditions': filter_config.get('conditions', []),
                'actions': filter_config.get('actions', []),
                'is_active': filter_config.get('is_active', True),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            await db.account_filters.insert_one(filter_data)
            return filter_data
            
        except Exception as e:
            logger.error(f"Error creating account filter: {e}")
            return None
    
    @staticmethod
    async def apply_account_filters(message_data: dict, account_id: str, organization_id: str) -> dict:
        """Apply advanced filters to message for specific account"""
        try:
            # Get filters for this account
            filters = await db.account_filters.find({
                'organization_id': organization_id,
                'account_id': account_id,
                'is_active': True
            }).to_list(100)
            
            filter_results = {
                'should_process': True,
                'matched_filters': [],
                'actions_to_perform': [],
                'filter_scores': {}
            }
            
            for filter_obj in filters:
                conditions = filter_obj.get('conditions', [])
                matched = True
                
                # Evaluate conditions
                for condition in conditions:
                    condition_type = condition.get('type')
                    condition_value = condition.get('value')
                    condition_operator = condition.get('operator', 'contains')
                    
                    if condition_type == 'message_text':
                        if condition_operator == 'contains':
                            matched = matched and (condition_value.lower() in message_data['message_text'].lower())
                        elif condition_operator == 'equals':
                            matched = matched and (condition_value.lower() == message_data['message_text'].lower())
                        elif condition_operator == 'regex':
                            import re
                            matched = matched and bool(re.search(condition_value, message_data['message_text'], re.IGNORECASE))
                    
                    elif condition_type == 'user_id':
                        matched = matched and (condition_value == message_data['user_id'])
                    
                    elif condition_type == 'username':
                        matched = matched and (condition_value.lower() == message_data.get('username', '').lower())
                    
                    elif condition_type == 'group_id':
                        matched = matched and (condition_value == message_data['group_id'])
                    
                    elif condition_type == 'media_type':
                        matched = matched and (condition_value == message_data.get('media_type'))
                    
                    elif condition_type == 'time_range':
                        # Time-based filtering
                        current_hour = datetime.now(timezone.utc).hour
                        start_hour = condition.get('start_hour', 0)
                        end_hour = condition.get('end_hour', 23)
                        matched = matched and (start_hour <= current_hour <= end_hour)
                
                if matched:
                    filter_results['matched_filters'].append(filter_obj['name'])
                    
                    # Add actions to perform
                    actions = filter_obj.get('actions', [])
                    for action in actions:
                        if action not in filter_results['actions_to_perform']:
                            filter_results['actions_to_perform'].append(action)
                    
                    # Calculate filter score (for priority)
                    score = len(conditions) * 10  # Base score
                    filter_results['filter_scores'][filter_obj['name']] = score
            
            return filter_results
            
        except Exception as e:
            logger.error(f"Error applying account filters: {e}")
            return {'should_process': True, 'matched_filters': [], 'actions_to_perform': []}

class AccountAnalytics:
    """Analytics and reporting for account performance"""
    
    @staticmethod
    async def get_account_performance_report(organization_id: str, account_id: str = None, days: int = 30) -> dict:
        """Generate comprehensive account performance report"""
        try:
            # Date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Build query
            base_query = {
                "tenant_id": organization_id,
                "created_at": {"$gte": start_date, "$lte": end_date}
            }
            
            if account_id:
                base_query["detected_by_account"] = account_id
            
            # Get message statistics
            message_stats = await db.message_logs.aggregate([
                {"$match": base_query},
                {"$group": {
                    "_id": "$detected_by_account",
                    "total_messages": {"$sum": 1},
                    "unique_groups": {"$addToSet": "$group_id"},
                    "unique_users": {"$addToSet": "$user_id"},
                    "media_messages": {"$sum": {"$cond": [{"$ne": ["$media_type", None]}, 1, 0]}},
                    "edited_messages": {"$sum": {"$cond": ["$is_edited", 1, 0]}}
                }},
                {"$project": {
                    "account_id": "$_id",
                    "total_messages": 1,
                    "unique_groups_count": {"$size": "$unique_groups"},
                    "unique_users_count": {"$size": "$unique_users"},
                    "media_messages": 1,
                    "edited_messages": 1,
                    "text_messages": {"$subtract": ["$total_messages", "$media_messages"]}
                }}
            ]).to_list(100)
            
            # Get forwarding statistics
            forwarding_stats = await db.forwarded_messages.aggregate([
                {"$match": {
                    "tenant_id": organization_id,
                    "created_at": {"$gte": start_date, "$lte": end_date}
                }},
                {"$group": {
                    "_id": "$forwarded_by_account",
                    "total_forwarded": {"$sum": 1},
                    "unique_destinations": {"$addToSet": "$destination_chat_id"}
                }},
                {"$project": {
                    "account_id": "$_id",
                    "total_forwarded": 1,
                    "unique_destinations_count": {"$size": "$unique_destinations"}
                }}
            ]).to_list(100)
            
            # Combine statistics
            account_reports = {}
            
            # Add message stats
            for stat in message_stats:
                account_id = stat['account_id']
                account_reports[account_id] = stat
                
            # Add forwarding stats
            for stat in forwarding_stats:
                account_id = stat['account_id']
                if account_id in account_reports:
                    account_reports[account_id].update(stat)
                else:
                    account_reports[account_id] = stat
            
            # Get account health data
            for account_id in account_reports.keys():
                account_doc = await db.accounts.find_one({"id": account_id})
                if account_doc:
                    account_reports[account_id].update({
                        'account_name': account_doc['name'],
                        'status': account_doc.get('status', 'unknown'),
                        'health_status': account_doc.get('health_status', 'unknown'),
                        'last_activity': account_doc.get('last_activity'),
                        'response_time': account_doc.get('response_time'),
                        'groups_accessible': account_doc.get('groups_accessible', 0)
                    })
            
            return {
                'organization_id': organization_id,
                'report_period': f"{days} days",
                'start_date': start_date,
                'end_date': end_date,
                'account_reports': account_reports,
                'summary': {
                    'total_accounts': len(account_reports),
                    'total_messages_detected': sum(report.get('total_messages', 0) for report in account_reports.values()),
                    'total_messages_forwarded': sum(report.get('total_forwarded', 0) for report in account_reports.values()),
                    'total_unique_groups': len(set().union(*[report.get('unique_groups', []) for report in message_stats])),
                    'total_unique_users': len(set().union(*[report.get('unique_users', []) for report in message_stats]))
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
    
    @staticmethod
    async def get_organization_dashboard_stats(organization_id: str) -> dict:
        """Get real-time dashboard statistics for organization"""
        try:
            # Get current date ranges
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            month_start = today_start - timedelta(days=30)
            
            # Parallel queries for performance
            queries = await asyncio.gather(
                # Today's messages
                db.message_logs.count_documents({
                    "tenant_id": organization_id,
                    "created_at": {"$gte": today_start}
                }),
                # This week's messages
                db.message_logs.count_documents({
                    "tenant_id": organization_id,
                    "created_at": {"$gte": week_start}
                }),
                # This month's messages
                db.message_logs.count_documents({
                    "tenant_id": organization_id,
                    "created_at": {"$gte": month_start}
                }),
                # Active accounts
                db.accounts.count_documents({
                    "organization_id": organization_id,
                    "status": AccountStatus.ACTIVE.value,
                    "is_active": True
                }),
                # Total groups being monitored
                db.groups.count_documents({
                    "tenant_id": organization_id,
                    "is_active": True
                }),
                # Today's forwarded messages
                db.forwarded_messages.count_documents({
                    "tenant_id": organization_id,
                    "created_at": {"$gte": today_start}
                })
            )
            
            return {
                'organization_id': organization_id,
                'timestamp': now,
                'messages_today': queries[0],
                'messages_this_week': queries[1],
                'messages_this_month': queries[2],
                'active_accounts': queries[3],
                'monitored_groups': queries[4],
                'forwarded_today': queries[5],
                'forwarding_rate': (queries[5] / queries[0] * 100) if queries[0] > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {'error': str(e)}

# Global instances for Phase 2 (maintained for compatibility)
health_monitor = AccountHealthMonitor(account_manager)
load_balancer = AccountLoadBalancer(account_manager)

# ================== TELEGRAM BOT COMMAND HANDLERS ==================

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        user = update.effective_user
        logger.info(f"Start command from user: {user.id} (@{user.username})")
        
        # Check if user is registered in our system
        user_doc = await db.users.find_one({"telegram_id": user.id})
        
        if user_doc:
            # User exists, show main menu
            keyboard = [
                [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
                [InlineKeyboardButton("👥 Accounts", callback_data="accounts"),
                 InlineKeyboardButton("🔍 Groups", callback_data="groups")],
                [InlineKeyboardButton("👁️ Watchlist", callback_data="watchlist"),
                 InlineKeyboardButton("📤 Forwarding", callback_data="forwarding")],
                [InlineKeyboardButton("📈 Analytics", callback_data="analytics"),
                 InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_msg = f"👋 Welcome back, {user.first_name}!\n\n"
            welcome_msg += "🤖 **Telegram Monitor Bot**\n"
            welcome_msg += "Multi-Account Session Monitoring System\n\n"
            welcome_msg += "Choose an option below:"
            
            await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # User not registered, show registration info
            welcome_msg = "👋 Welcome to **Telegram Monitor Bot**!\n\n"
            welcome_msg += "🚀 This is a multi-account session-based monitoring system.\n\n"
            welcome_msg += "To get started:\n"
            welcome_msg += "1. Visit our web dashboard to register\n"
            welcome_msg += "2. Create your organization account\n"
            welcome_msg += "3. Upload your Telegram account sessions\n\n"
            welcome_msg += "🌐 **Web Dashboard:** Access via Telegram Login Widget\n"
            welcome_msg += "📱 **Bot Commands:** Use /help for available commands"
            
            keyboard = [
                [InlineKeyboardButton("🌐 Web Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    try:
        help_msg = "❓ **Help - Telegram Monitor Bot**\n\n"
        help_msg += "**Available Commands:**\n"
        help_msg += "• /start - Main menu\n"
        help_msg += "• /status - System status\n"
        help_msg += "• /accounts - Account management\n"
        help_msg += "• /groups - Group management\n"
        help_msg += "• /analytics - View analytics\n"
        help_msg += "• /help - Show this help\n\n"
        help_msg += "**Features:**\n"
        help_msg += "🔹 Multi-account monitoring\n"
        help_msg += "🔹 Stealth group monitoring\n"
        help_msg += "🔹 Advanced message filtering\n"
        help_msg += "🔹 Real-time forwarding\n"
        help_msg += "🔹 Comprehensive analytics\n\n"
        help_msg += "**Web Dashboard:**\n"
        help_msg += "For full features, use our web interface with Telegram authentication."
        
        keyboard = [
            [InlineKeyboardButton("🌐 Open Web Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_msg, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        user = update.effective_user
        
        # Check if user is registered
        user_doc = await db.users.find_one({"telegram_id": user.id})
        
        if not user_doc:
            await update.message.reply_text("❌ You need to register first. Use /start to get started.")
            return
        
        # Get organization stats
        org_id = user_doc["organization_id"]
        
        # Get system health
        health_summary = health_monitor.get_health_summary()
        
        # Get dashboard stats
        dashboard_stats = await analytics.get_organization_dashboard_stats(org_id)
        
        status_msg = "📊 **System Status**\n\n"
        
        # Account health
        if 'error' not in health_summary:
            status_msg += f"🤖 **Accounts:** {health_summary['healthy_accounts']}/{health_summary['total_accounts']} healthy "
            status_msg += f"({health_summary['health_percentage']:.1f}%)\n"
        else:
            status_msg += "🤖 **Accounts:** Status unavailable\n"
        
        # Today's activity  
        if 'error' not in dashboard_stats:
            status_msg += f"📨 **Today's Messages:** {dashboard_stats['messages_today']}\n"
            status_msg += f"📤 **Forwarded Today:** {dashboard_stats['forwarded_today']}\n"
            status_msg += f"👥 **Active Accounts:** {dashboard_stats['active_accounts']}\n"
            status_msg += f"🔍 **Monitored Groups:** {dashboard_stats['monitored_groups']}\n"
        else:
            status_msg += "📊 **Activity Stats:** Unavailable\n"
        
        status_msg += f"\n⏰ **Last Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
        
        keyboard = [
            [InlineKeyboardButton("📊 Detailed Analytics", callback_data="analytics")],
            [InlineKeyboardButton("👥 Account Status", callback_data="accounts")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(status_msg, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await update.message.reply_text("❌ An error occurred while fetching status.")

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /accounts command"""
    try:
        user = update.effective_user
        
        # Check if user is registered
        user_doc = await db.users.find_one({"telegram_id": user.id})
        
        if not user_doc:
            await update.message.reply_text("❌ You need to register first. Use /start to get started.")
            return
        
        # Get accounts for user's organization
        accounts = await db.accounts.find({
            "organization_id": user_doc["organization_id"],
            "is_active": True
        }).to_list(10)
        
        if not accounts:
            msg = "👥 **Account Management**\n\n"
            msg += "❌ No accounts configured yet.\n\n"
            msg += "To add accounts:\n"
            msg += "1. Go to the web dashboard\n"
            msg += "2. Upload session + JSON files\n"
            msg += "3. Activate accounts for monitoring"
            
            keyboard = [
                [InlineKeyboardButton("🌐 Web Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
        else:
            msg = f"👥 **Account Management** ({len(accounts)} accounts)\n\n"
            
            for i, account in enumerate(accounts[:5]):  # Show max 5 accounts
                status_emoji = "✅" if account["status"] == "active" else "⏸️" if account["status"] == "inactive" else "❌"
                msg += f"{status_emoji} **{account['name']}**\n"
                msg += f"   Status: {account['status'].title()}\n"
                if account.get('username'):
                    msg += f"   @{account['username']}\n"
                if account.get('last_activity'):
                    msg += f"   Last Active: {account['last_activity'].strftime('%H:%M %d/%m')}\n"
                msg += "\n"
            
            if len(accounts) > 5:
                msg += f"... and {len(accounts) - 5} more accounts\n\n"
            
            msg += "Use web dashboard for full account management."
            
            keyboard = [
                [InlineKeyboardButton("🌐 Manage Accounts", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="accounts"),
                 InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in accounts command: {e}")
        await update.message.reply_text("❌ An error occurred while fetching accounts.")

async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /groups command"""
    try:
        user = update.effective_user
        
        # Check if user is registered
        user_doc = await db.users.find_one({"telegram_id": user.id})
        
        if not user_doc:
            await update.message.reply_text("❌ You need to register first. Use /start to get started.")
            return
        
        # Get groups for user's organization
        groups = await db.groups.find({
            "tenant_id": user_doc["organization_id"],
            "is_active": True
        }).to_list(10)
        
        if not groups:
            msg = "🔍 **Group Management**\n\n"
            msg += "❌ No groups found.\n\n"
            msg += "Groups are automatically discovered when you:\n"
            msg += "1. Upload account sessions\n"
            msg += "2. Activate accounts\n"
            msg += "3. Use group discovery feature"
        else:
            msg = f"🔍 **Monitored Groups** ({len(groups)} groups)\n\n"
            
            for i, group in enumerate(groups[:5]):  # Show max 5 groups
                monitoring_emoji = "👁️" if group.get("monitoring_enabled", True) else "⏸️"
                msg += f"{monitoring_emoji} **{group['name']}**\n"
                msg += f"   ID: `{group['group_id']}`\n"
                if group.get('auto_discovered'):
                    msg += "   🤖 Auto-discovered\n"
                msg += "\n"
            
            if len(groups) > 5:
                msg += f"... and {len(groups) - 5} more groups\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🌐 Manage Groups", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
            [InlineKeyboardButton("🔍 Discover Groups", callback_data="discover_groups")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in groups command: {e}")
        await update.message.reply_text("❌ An error occurred while fetching groups.")

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analytics command"""
    try:
        user = update.effective_user
        
        # Check if user is registered
        user_doc = await db.users.find_one({"telegram_id": user.id})
        
        if not user_doc:
            await update.message.reply_text("❌ You need to register first. Use /start to get started.")
            return
        
        # Get analytics data
        org_id = user_doc["organization_id"]
        dashboard_stats = await analytics.get_organization_dashboard_stats(org_id)
        
        if 'error' in dashboard_stats:
            msg = "📈 **Analytics**\n\n❌ Unable to load analytics data."
        else:
            msg = "📈 **Analytics Overview**\n\n"
            msg += f"📊 **Today:** {dashboard_stats['messages_today']} messages\n"
            msg += f"📅 **This Week:** {dashboard_stats['messages_this_week']} messages\n"
            msg += f"📆 **This Month:** {dashboard_stats['messages_this_month']} messages\n\n"
            msg += f"📤 **Forwarded Today:** {dashboard_stats['forwarded_today']}\n"
            msg += f"📊 **Forward Rate:** {dashboard_stats['forwarding_rate']:.1f}%\n\n"
            msg += f"🤖 **Active Accounts:** {dashboard_stats['active_accounts']}\n"
            msg += f"👥 **Monitored Groups:** {dashboard_stats['monitored_groups']}\n"
        
        keyboard = [
            [InlineKeyboardButton("🌐 Detailed Analytics", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="analytics"),
             InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in analytics command: {e}")
        await update.message.reply_text("❌ An error occurred while fetching analytics.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        callback_data = query.data
        
        logger.info(f"Button callback: {callback_data} from user {user.id}")
        
        if callback_data == "main_menu":
            # Return to main menu
            await start_command(update, context)
            return
        elif callback_data == "help":
            await help_command(update, context)
            return
        elif callback_data == "dashboard":
            msg = "📊 **Dashboard**\n\nFor the complete dashboard with real-time data, charts, and detailed analytics, please use the web interface."
            keyboard = [
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        elif callback_data == "accounts":
            await accounts_command(update, context)
            return
        elif callback_data == "groups":
            await groups_command(update, context)
            return
        elif callback_data == "analytics":
            await analytics_command(update, context)
            return
        elif callback_data == "discover_groups":
            # Trigger group discovery
            user_doc = await db.users.find_one({"telegram_id": user.id})
            if user_doc:
                try:
                    discovery_result = await group_discovery.discover_all_groups_for_organization(
                        user_doc["organization_id"]
                    )
                    
                    if 'error' in discovery_result:
                        msg = "❌ Group discovery failed. Please try again later."
                    else:
                        total_groups = discovery_result.get('total_groups_discovered', 0)
                        msg = f"🔍 **Group Discovery Complete**\n\n"
                        msg += f"Found {total_groups} groups across your accounts.\n"
                        msg += "Check the web dashboard for details."
                    
                except Exception as e:
                    logger.error(f"Group discovery error: {e}")
                    msg = "❌ Group discovery failed. Please try again later."
            else:
                msg = "❌ User not found. Please use /start first."
            
            keyboard = [
                [InlineKeyboardButton("🌐 View Groups", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # Handle other callbacks
            msg = f"🔧 **{callback_data.title()}**\n\nThis feature requires the web dashboard for full functionality."
            keyboard = [
                [InlineKeyboardButton("🌐 Open Web Dashboard", url="https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        try:
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
        except:
            pass

# ================== TELEGRAM BOT APPLICATION SETUP ==================

# Bot application instance
bot_application = None

async def setup_bot_handlers():
    """Setup bot command handlers"""
    try:
        global bot_application
        
        # Create application
        bot_application = Application.builder().token(os.environ.get('TELEGRAM_TOKEN')).build()
        
        # Add command handlers
        bot_application.add_handler(CommandHandler("start", start_command))
        bot_application.add_handler(CommandHandler("help", help_command))
        bot_application.add_handler(CommandHandler("status", status_command))
        bot_application.add_handler(CommandHandler("accounts", accounts_command))
        bot_application.add_handler(CommandHandler("groups", groups_command))
        bot_application.add_handler(CommandHandler("analytics", analytics_command))
        
        # Add callback query handler
        bot_application.add_handler(CallbackQueryHandler(button_callback))
        
        # Initialize the application
        await bot_application.initialize()
        await bot_application.start()
        
        # Set webhook for production
        webhook_url = f"https://763383c1-6086-4244-aa7d-b55ea6e1d91b.preview.emergentagent.com/api/telegram/webhook/{os.environ.get('WEBHOOK_SECRET')}"
        await bot.set_webhook(url=webhook_url)
        
        logger.info(f"✅ Telegram bot handlers setup complete and webhook set to: {webhook_url}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to setup bot handlers: {e}")
        return False

async def cleanup_bot_handlers():
    """Cleanup bot handlers on shutdown"""
    try:
        global bot_application
        if bot_application:
            await bot_application.stop()
            await bot_application.shutdown()
            logger.info("✅ Telegram bot handlers cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up bot handlers: {e}")

# Global instances for Phase 3
group_discovery = GroupAutoDiscovery(account_manager)
analytics = AccountAnalytics()

# ================== ENHANCED API ENDPOINTS FOR ANALYTICS ==================

@api_router.get("/analytics/dashboard")
async def get_dashboard_analytics(current_user: Dict = Depends(get_current_active_user)):
    """Get real-time dashboard analytics for organization"""
    try:
        stats = await analytics.get_organization_dashboard_stats(current_user["organization_id"])
        return stats
    except Exception as e:
        logger.error(f"Error getting dashboard analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@api_router.get("/analytics/accounts")
async def get_account_analytics(
    days: int = 30,
    account_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_active_user)
):
    """Get detailed account performance analytics"""
    try:
        report = await analytics.get_account_performance_report(
            current_user["organization_id"],
            account_id,
            days
        )
        return report
    except Exception as e:
        logger.error(f"Error getting account analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account analytics: {str(e)}")

@api_router.get("/accounts/health")
async def get_accounts_health_summary(current_user: Dict = Depends(get_current_active_user)):
    """Get health summary of all accounts"""
    try:
        summary = health_monitor.get_health_summary()
        load_summary = load_balancer.get_load_summary()
        
        return {
            'health': summary,
            'load_balancing': load_summary,
            'organization_id': current_user["organization_id"]
        }
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}")

@api_router.post("/groups/discover")
async def discover_groups(current_user: Dict = Depends(require_admin)):
    """Discover groups from all active accounts (Admin/Owner only)"""
    try:
        discovery_result = await group_discovery.discover_all_groups_for_organization(
            current_user["organization_id"]
        )
        return discovery_result
    except Exception as e:
        logger.error(f"Error during group discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Group discovery failed: {str(e)}")

@api_router.post("/accounts/{account_id}/filters")
async def create_account_filter(
    account_id: str,
    filter_config: Dict[str, Any],
    current_user: Dict = Depends(require_admin)
):
    """Create advanced filter for specific account (Admin/Owner only)"""
    try:
        # Verify account belongs to user's organization
        account = await db.accounts.find_one({
            "id": account_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        filter_obj = await AdvancedFiltering.create_account_filter(
            current_user["organization_id"],
            account_id,
            filter_config
        )
        
        if filter_obj:
            return filter_obj
        else:
            raise HTTPException(status_code=500, detail="Failed to create filter")
        
    except Exception as e:
        logger.error(f"Error creating account filter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create account filter: {str(e)}")

@api_router.get("/accounts/{account_id}/filters")
async def get_account_filters(
    account_id: str,
    current_user: Dict = Depends(get_current_active_user)
):
    """Get all filters for specific account"""
    try:
        # Verify account belongs to user's organization
        account = await db.accounts.find_one({
            "id": account_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        filters = await db.account_filters.find({
            'organization_id': current_user["organization_id"],
            'account_id': account_id
        }).to_list(100)
        
        return filters
        
    except Exception as e:
        logger.error(f"Error getting account filters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account filters: {str(e)}")

async def initialize_active_accounts():
    """Initialize all active accounts on startup"""
    try:
        # Get all active accounts from database
        active_accounts = await db.accounts.find({
            "status": AccountStatus.ACTIVE.value,
            "is_active": True
        }).to_list(100)
        
        logger.info(f"Initializing {len(active_accounts)} active accounts...")
        
        for account in active_accounts:
            try:
                success = await account_manager.initialize_account_client(
                    account['id'],
                    account['session_file_path'],
                    account['json_file_path']
                )
                
                if success:
                    logger.info(f"Initialized account: {account['name']}")
                else:
                    logger.error(f"Failed to initialize account: {account['name']}")
                    
            except Exception as e:
                logger.error(f"Error initializing account {account['name']}: {e}")
        
        logger.info("Account initialization complete")
        
    except Exception as e:
        logger.error(f"Error during account initialization: {e}")

# ================== UPDATED ACCOUNT MANAGEMENT ROUTES ==================

@api_router.post("/accounts/{account_id}/activate")
async def activate_account(
    account_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Activate account for monitoring (Admin/Owner only)"""
    try:
        # Find account
        account = await db.accounts.find_one({
            "id": account_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Initialize Telethon client
        success = await account_manager.initialize_account_client(
            account_id,
            account['session_file_path'],
            account['json_file_path']
        )
        
        if success:
            return {"message": "Account activated and monitoring started successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to activate account")
        
    except Exception as e:
        logger.error(f"Account activation failed: {e}")
        
        # Update account with error
        await db.accounts.update_one(
            {"id": account_id, "organization_id": current_user["organization_id"]},
            {
                "$set": {
                    "status": AccountStatus.ERROR.value,
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": str(e)
                }
            }
        )
        
        raise HTTPException(status_code=500, detail=f"Account activation failed: {str(e)}")

@api_router.post("/accounts/{account_id}/deactivate")
async def deactivate_account(
    account_id: str,
    current_user: Dict = Depends(require_admin)
):
    """Deactivate account monitoring (Admin/Owner only)"""
    try:
        # Disconnect account client
        await account_manager.disconnect_account(account_id)
        
        return {"message": "Account deactivated successfully"}
        
    except Exception as e:
        logger.error(f"Account deactivation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Account deactivation failed: {str(e)}")

@api_router.get("/accounts/{account_id}/status")
async def get_account_status(
    account_id: str,
    current_user: Dict = Depends(get_current_active_user)
):
    """Get detailed account status"""
    try:
        # Verify account belongs to user's organization
        account = await db.accounts.find_one({
            "id": account_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        status = await account_manager.get_account_status(account_id)
        return status
        
    except Exception as e:
        logger.error(f"Error getting account status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account status: {str(e)}")

# ================== CRYPTOCURRENCY PAYMENT SYSTEM (NOWPAYMENTS) ==================

class CryptoChargeRequest(BaseModel):
    plan: str  # "pro" or "enterprise"
    pay_currency: str = "btc"  # Default to BTC, can be btc, eth, usdc, sol

class CryptoChargeResponse(BaseModel):
    payment_url: str
    payment_id: str
    amount: str
    plan: str
    pay_currency: str
    pay_address: str
    pay_amount: float

@api_router.post("/crypto/create-charge", response_model=CryptoChargeResponse)
async def create_crypto_charge(
    charge_request: CryptoChargeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create cryptocurrency payment charge via NOWPayments"""
    try:
        # Validate plan
        if charge_request.plan not in ["pro", "enterprise"]:
            raise HTTPException(status_code=400, detail="Invalid plan. Must be 'pro' or 'enterprise'")
        
        # Validate cryptocurrency
        supported_currencies = ["btc", "eth", "usdc", "sol"]  # Removed USDT temporarily
        if charge_request.pay_currency.lower() not in supported_currencies:
            raise HTTPException(status_code=400, detail=f"Unsupported cryptocurrency. Supported: {supported_currencies}")
        
        # Get plan pricing
        subscription_plans = json.loads(os.environ.get('SUBSCRIPTION_PLANS', '{"pro": 9.99, "enterprise": 19.99}'))
        plan_price = subscription_plans.get(charge_request.plan)
        
        if not plan_price:
            raise HTTPException(status_code=400, detail="Plan pricing not configured")
        
        # Check if user already has this plan or higher
        user_org = await db.organizations.find_one({"id": current_user["organization_id"]})
        current_plan = user_org.get("plan", "free")
        
        # Prevent downgrade
        plan_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
        if plan_hierarchy.get(current_plan, 0) >= plan_hierarchy.get(charge_request.plan, 0):
            raise HTTPException(status_code=400, detail=f"You already have {current_plan} plan or higher")
        
        # Get NOWPayments API key
        nowpayments_api_key = os.environ.get('NOWPAYMENTS_API_KEY')
        if not nowpayments_api_key or nowpayments_api_key == "your_nowpayments_api_key_here":
            raise HTTPException(status_code=503, detail="Cryptocurrency payments are not configured yet. Please contact support.")
        
        # Generate unique order ID
        order_id = f"{current_user['organization_id']}_{charge_request.plan}_{int(datetime.utcnow().timestamp())}"
        
        # Prepare payment data for NOWPayments
        api_headers = {
            "x-api-key": nowpayments_api_key,
            "Content-Type": "application/json"
        }
        
        # Get estimated payment amount in crypto
        estimate_response = requests.get(
            "https://api.nowpayments.io/v1/estimate",
            params={
                "amount": plan_price,
                "currency_from": "usd",
                "currency_to": charge_request.pay_currency.lower()
            },
            headers=api_headers,
            timeout=30
        )
        
        if estimate_response.status_code != 200:
            logger.error(f"NOWPayments estimate API Error: {estimate_response.status_code} - {estimate_response.text}")
            raise HTTPException(status_code=502, detail="Failed to estimate payment amount. Please try again.")
        
        estimate_data = estimate_response.json()
        estimated_amount = float(estimate_data.get("estimated_amount", 0))
        
        # Create payment via NOWPayments API
        payment_data = {
            "price_amount": plan_price,
            "price_currency": "usd",
            "pay_currency": charge_request.pay_currency.lower(),
            "order_id": order_id,
            "order_description": f"Telegram Monitor {charge_request.plan.capitalize()} Plan Upgrade",
            "ipn_callback_url": f"{os.environ.get('BACKEND_URL', 'http://localhost:8001')}/api/crypto/ipn",
            "success_url": f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/subscription?status=success",
            "cancel_url": f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/subscription?status=cancelled"
        }
        
        response = requests.post(
            "https://api.nowpayments.io/v1/payment",
            headers=api_headers,
            json=payment_data,
            timeout=30
        )
        
        if response.status_code != 201:
            logger.error(f"NOWPayments API Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=502, detail="Failed to create payment. Please try again.")
        
        payment_response = response.json()
        
        # Store pending charge in database
        pending_charge = {
            "id": str(uuid.uuid4()),
            "payment_id": payment_response.get("payment_id"),  # Fixed: NOWPayments uses payment_id
            "order_id": order_id,
            "user_id": current_user["id"],
            "organization_id": current_user["organization_id"],
            "plan": charge_request.plan,
            "price_amount": str(plan_price),
            "price_currency": "USD",
            "pay_currency": charge_request.pay_currency.lower(),
            "pay_amount": estimated_amount,
            "pay_address": payment_response.get("pay_address"),
            "status": "waiting",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=2),  # NOWPayments default expiry
            "payment_url": payment_response.get("payment_url"),
            "nowpayments_response": payment_response
        }
        
        await db.crypto_charges.insert_one(pending_charge)
        
        # Log the charge creation
        logger.info(f"Created NOWPayments charge {payment_response.get('payment_id')} for user {current_user['id']} - {charge_request.plan} plan (${plan_price}) - {charge_request.pay_currency.upper()}")
        
        return CryptoChargeResponse(
            payment_url=payment_response.get("payment_url"),
            payment_id=payment_response.get("payment_id"),  # Fixed: Use payment_id from NOWPayments
            amount=str(plan_price),
            plan=charge_request.plan,
            pay_currency=charge_request.pay_currency.lower(),
            pay_address=payment_response.get("pay_address"),
            pay_amount=estimated_amount
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating NOWPayments charge: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment charge")

@api_router.post("/crypto/ipn")
async def handle_crypto_ipn(request: Request):
    """Handle NOWPayments IPN (Instant Payment Notifications)"""
    try:
        # Get IPN secret
        ipn_secret = os.environ.get('NOWPAYMENTS_IPN_SECRET')
        if not ipn_secret or ipn_secret == "your_nowpayments_ipn_secret_here":
            logger.error("NOWPayments IPN secret not configured")
            return JSONResponse(status_code=503, content={"error": "IPN not configured"})
        
        # Get request body and signature
        body = await request.body()
        signature = request.headers.get("x-nowpayments-sig", "")
        
        # Parse IPN payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in IPN payload")
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
        
        # Verify IPN signature
        sorted_payload = dict(sorted(payload.items()))
        query_string = "&".join([f"{k}={v}" for k, v in sorted_payload.items()])
        
        expected_signature = hmac.new(
            ipn_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid IPN signature received")
            return JSONResponse(status_code=403, content={"error": "Invalid signature"})
        
        # Extract payment data
        payment_id = payload.get("payment_id")
        payment_status = payload.get("payment_status")
        order_id = payload.get("order_id")
        
        logger.info(f"Received NOWPayments IPN: {payment_id} - {payment_status}")
        
        # Find pending charge in database
        pending_charge = await db.crypto_charges.find_one({
            "$or": [
                {"payment_id": payment_id},
                {"order_id": order_id}
            ]
        })
        
        if not pending_charge:
            logger.warning(f"No pending charge found for payment {payment_id} / order {order_id}")
            return JSONResponse(status_code=404, content={"error": "Payment not found"})
        
        # Handle payment confirmation
        if payment_status in ["confirmed", "finished"]:
            # Update organization plan
            await db.organizations.update_one(
                {"id": pending_charge["organization_id"]},
                {
                    "$set": {
                        "plan": pending_charge["plan"],
                        "updated_at": datetime.utcnow(),
                        "payment_method": "cryptocurrency_nowpayments",
                        "last_payment_date": datetime.utcnow()
                    }
                }
            )
            
            # Update charge status
            await db.crypto_charges.update_one(
                {"payment_id": payment_id},
                {
                    "$set": {
                        "status": payment_status,
                        "confirmed_at": datetime.utcnow(),
                        "ipn_data": payload
                    }
                }
            )
            
            # Log successful payment
            logger.info(f"✅ NOWPayments confirmed: User {pending_charge['user_id']} upgraded to {pending_charge['plan']} plan (${pending_charge['price_amount']}) via {pending_charge['pay_currency'].upper()}")
            
            return JSONResponse(status_code=200, content={"message": "Payment processed successfully"})
        
        # Handle payment failure or other statuses
        elif payment_status in ["failed", "refunded", "expired"]:
            # Update charge status
            await db.crypto_charges.update_one(
                {"payment_id": payment_id},
                {
                    "$set": {
                        "status": payment_status,
                        "failed_at": datetime.utcnow(),
                        "ipn_data": payload
                    }
                }
            )
            
            logger.warning(f"❌ NOWPayments failed: Payment {payment_id} - {payment_status}")
            
            return JSONResponse(status_code=200, content={"message": "Payment failure recorded"})
        
        # Handle partial payments or waiting status
        else:
            # Update charge with current status
            await db.crypto_charges.update_one(
                {"payment_id": payment_id},
                {
                    "$set": {
                        "status": payment_status,
                        "last_update": datetime.utcnow(),
                        "ipn_data": payload
                    }
                }
            )
            
            logger.info(f"📊 NOWPayments status update: Payment {payment_id} - {payment_status}")
            
            return JSONResponse(status_code=200, content={"message": "Status updated"})
        
    except Exception as e:
        logger.error(f"Error handling NOWPayments IPN: {e}")
        return JSONResponse(status_code=500, content={"error": "IPN processing failed"})

@api_router.get("/crypto/charges")
async def get_crypto_charges(current_user: dict = Depends(get_current_user)):
    """Get user's cryptocurrency payment history"""
    try:
        charges = await db.crypto_charges.find({
            "organization_id": current_user["organization_id"]
        }).sort("created_at", -1).to_list(50)
        
        # Clean up sensitive data
        for charge in charges:
            charge.pop("nowpayments_response", None)
            charge.pop("ipn_data", None)
            charge["_id"] = str(charge["_id"])
        
        return {"charges": charges}
        
    except Exception as e:
        logger.error(f"Error getting crypto charges: {e}")
        raise HTTPException(status_code=500, detail="Failed to get payment history")

@api_router.get("/crypto/currencies")
async def get_supported_currencies():
    """Get list of supported cryptocurrencies"""
    try:
        # Get NOWPayments API key
        nowpayments_api_key = os.environ.get('NOWPAYMENTS_API_KEY')
        if not nowpayments_api_key or nowpayments_api_key == "your_nowpayments_api_key_here":
            # Return default supported currencies if API not configured
            return {
                "currencies": [
                    {"currency": "btc", "name": "Bitcoin", "network": "BTC"},
                    {"currency": "eth", "name": "Ethereum", "network": "ETH"},
                    {"currency": "usdc", "name": "USD Coin", "network": "ETH"},
                    {"currency": "sol", "name": "Solana", "network": "SOL"}
                ]
            }
        
        # Fetch available currencies from NOWPayments
        api_headers = {
            "x-api-key": nowpayments_api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://api.nowpayments.io/v1/currencies",
            headers=api_headers,
            timeout=30
        )
        
        if response.status_code == 200:
            all_currencies = response.json().get("currencies", [])
            # Filter to our supported cryptocurrencies
            supported = ["btc", "eth", "usdc", "sol"]
            filtered_currencies = [
                {"currency": curr.lower(), "name": curr.upper(), "network": curr.upper()}
                for curr in all_currencies if curr.lower() in supported
            ]
            return {"currencies": filtered_currencies}
        else:
            # Fallback to default list
            return {
                "currencies": [
                    {"currency": "btc", "name": "Bitcoin", "network": "BTC"},
                    {"currency": "eth", "name": "Ethereum", "network": "ETH"},
                    {"currency": "usdc", "name": "USD Coin", "network": "ETH"},
                    {"currency": "sol", "name": "Solana", "network": "SOL"}
                ]
            }
        
    except Exception as e:
        logger.error(f"Error getting supported currencies: {e}")
        # Return default currencies on error
        return {
            "currencies": [
                {"currency": "btc", "name": "Bitcoin", "network": "BTC"},
                {"currency": "eth", "name": "Ethereum", "network": "ETH"},
                {"currency": "usdc", "name": "USD Coin", "network": "ETH"},
                {"currency": "sol", "name": "Solana", "network": "SOL"}
            ]
        }

# ================== ENHANCED STARTUP EVENT HANDLERS ==================

# Include the router in the main app after all routes are defined
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Telegram Monitor Bot API - Multi-Account Session Monitoring System")
    logger.info("Running multi-tenancy database migration...")
    await migrate_database_for_multitenancy()
    
    # Initialize bot (still available for admin commands)
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username}")
        
        # Setup bot command handlers
        handler_success = await setup_bot_handlers()
        if handler_success:
            logger.info("✅ Telegram bot command handlers initialized")
        else:
            logger.error("❌ Failed to initialize bot command handlers")
    except Exception as e:
        logger.error(f"Bot connection failed: {e}")
    
    # Initialize active user accounts
    await initialize_active_accounts()
    
    # Start health monitoring
    await health_monitor.start_health_monitoring()
    
    # Initialize load balancer periodic reset task
    asyncio.create_task(periodic_load_reset())
    
    logger.info("🚀 Multi-Account Session Monitoring System ready!")
    
async def periodic_load_reset():
    """Periodically reset load balancer counters"""
    while True:
        try:
            await asyncio.sleep(3600)  # Reset every hour
            load_balancer.reset_load_counters()
            logger.debug("Load balancer counters reset")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic load reset: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Telegram Monitor Bot API")
    
    # Stop health monitoring
    await health_monitor.stop_health_monitoring()
    
    # Cleanup bot handlers
    await cleanup_bot_handlers()
    
    # Disconnect all active accounts
    for account_id in list(account_manager.active_clients.keys()):
        await account_manager.disconnect_account(account_id)
    
    await shutdown_db_client()
    logger.info("Shutdown complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )
