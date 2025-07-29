from fastapi import FastAPI, APIRouter, HTTPException, Request, BackgroundTasks, Depends
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
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import json
import re
import jwt
import bcrypt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: Optional[str] = None  # For creating new org during registration

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    role: UserRole
    organization_id: str
    created_at: datetime
    last_login: Optional[datetime] = None

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    full_name: str
    is_active: bool = True
    role: UserRole = UserRole.VIEWER
    organization_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    email_verified: bool = False

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
    from_group_id: str
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

class MessageLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # Organization ID for multi-tenancy
    message_id: str
    group_id: str
    group_name: str
    user_id: str
    username: str
    user_full_name: Optional[str] = None
    message_text: Optional[str] = None
    message_type: str
    media_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_forwarded: bool = False
    forwarded_count: int = 0  # Number of destinations forwarded to
    matched_keywords: List[str] = []

class BotCommand(BaseModel):
    command: str
    chat_id: str
    user_id: str
    username: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ================== UTILITY FUNCTIONS ==================

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2"""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def check_if_user_monitored(user_id: str, username: str, group_id: str) -> Optional[WatchlistUser]:
    """Check if user is in watchlist for monitoring"""
    query = {
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
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://9ee19252-a7c1-46fc-8e44-703ba38492ab.preview.emergentagent.com")],
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
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://9ee19252-a7c1-46fc-8e44-703ba38492ab.preview.emergentagent.com")],
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
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://9ee19252-a7c1-46fc-8e44-703ba38492ab.preview.emergentagent.com")],
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
                [InlineKeyboardButton("🌐 Open Dashboard", url="https://9ee19252-a7c1-46fc-8e44-703ba38492ab.preview.emergentagent.com")],
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

# ================== API ROUTES ==================

# Group Management Routes
@api_router.post("/groups", response_model=Group)
async def create_group(group: GroupCreate):
    """Add a new group to monitor"""
    try:
        # Check if group already exists
        existing = await db.groups.find_one({"group_id": group.group_id})
        if existing:
            raise HTTPException(status_code=400, detail="Group already exists")
        
        new_group = Group(**group.dict())
        await db.groups.insert_one(new_group.dict())
        return new_group
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create group: {str(e)}")

@api_router.get("/groups", response_model=List[Group])
async def get_groups():
    """Get all monitored groups"""
    groups = await db.groups.find({"is_active": True}).to_list(100)
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
    webhook_url = f"https://9ee19252-a7c1-46fc-8e44-703ba38492ab.preview.emergentagent.com/api/telegram/webhook/{os.environ.get('WEBHOOK_SECRET')}"
    
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

# Test Routes
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

# Include the router in the main app
app.include_router(api_router)

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

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("Starting Telegram Monitor Bot API")
    
    # Test bot connection
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to connect to Telegram bot: {e}")

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
