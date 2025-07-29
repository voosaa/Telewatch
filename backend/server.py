from fastapi import FastAPI, APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio
import json
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

# ================== PYDANTIC MODELS ==================

class GroupCreate(BaseModel):
    group_id: str
    group_name: str
    group_type: str = "group"  # group, supergroup, channel
    invite_link: Optional[str] = None
    description: Optional[str] = None

class Group(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    group_id: str
    group_name: str
    group_type: str
    invite_link: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WatchlistUserCreate(BaseModel):
    username: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    group_ids: List[str] = []  # Empty means monitor globally
    keywords: List[str] = []  # Optional keyword filtering

class WatchlistUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    group_ids: List[str] = []
    keywords: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ForwardedMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_message_id: str
    from_group_id: str
    from_group_name: str
    from_user_id: str
    from_username: str
    from_user_full_name: Optional[str] = None
    message_text: Optional[str] = None
    message_type: str  # text, photo, video, document, etc.
    media_info: Optional[Dict[str, Any]] = None
    forward_to_groups: List[str] = []
    forwarded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    matched_keywords: List[str] = []

class MessageLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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

# ================== TELEGRAM BOT HANDLERS ==================

async def handle_telegram_message(update: Update) -> None:
    """Process incoming Telegram messages"""
    try:
        message = update.message
        if not message:
            return
        
        # Extract message info
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        username = message.from_user.username or ""
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        message_text = message.text or message.caption or ""
        
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
            await handle_bot_command(message)
            return
        
        # Check if group is monitored
        group_doc = await db.groups.find_one({"group_id": chat_id, "is_active": True})
        if not group_doc:
            return
        
        group = Group(**group_doc)
        
        # Check if user is in watchlist
        monitored_user = await check_if_user_monitored(user_id, username, chat_id)
        if not monitored_user:
            return
        
        # Check keyword matching if specified
        matched_keywords = []
        if monitored_user.keywords:
            matched_keywords = await check_keyword_match(message_text, monitored_user.keywords)
            if not matched_keywords:
                return  # No keyword match, don't forward
        
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
        
        # Forward the message (for now, we'll implement this later)
        # This would forward to designated channels/groups
        
        logging.info(f"Logged message from monitored user {username} in group {group.group_name}")
        
    except Exception as e:
        logging.error(f"Error handling Telegram message: {e}")

async def handle_bot_command(message) -> None:
    """Handle bot commands"""
    try:
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        username = message.from_user.username or ""
        command_text = message.text
        
        # Log the command
        bot_command = BotCommand(
            command=command_text,
            chat_id=chat_id,
            user_id=user_id,
            username=username
        )
        await db.bot_commands.insert_one(bot_command.dict())
        
        # Handle different commands
        if command_text == '/start':
            welcome_text = """
*🤖 Telegram Monitor Bot*

Welcome to the Telegram Monitoring System\\!

*Available Commands:*
/help \\- Show available commands
/status \\- Show monitoring status
/groups \\- List monitored groups
/watchlist \\- Show watchlist users

*Admin Commands:*
/addgroup \\- Add a group to monitor
/adduser \\- Add user to watchlist
/settings \\- Bot settings

For full management, use the web dashboard\\.
            """
            await bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        elif command_text == '/help':
            help_text = """
*📋 Available Commands:*

*Information:*
/status \\- Current monitoring status
/groups \\- List all monitored groups
/watchlist \\- Show users being monitored

*Management:*
/addgroup \\- Add new group to monitor
/removegroup \\- Remove group from monitoring
/adduser \\- Add user to watchlist
/removeuser \\- Remove user from watchlist

*Settings:*
/settings \\- Configure bot settings
/logs \\- View recent activity logs

Use the web dashboard for advanced management\\.
            """
            await bot.send_message(
                chat_id=chat_id,
                text=help_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        elif command_text == '/status':
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
            await bot.send_message(
                chat_id=chat_id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        elif command_text == '/groups':
            groups = await db.groups.find({"is_active": True}).to_list(50)
            if not groups:
                groups_text = "*📁 Monitored Groups*\n\nNo groups are currently being monitored\\."
            else:
                groups_list = []
                for group_doc in groups:
                    group = Group(**group_doc)
                    groups_list.append(f"• {escape_markdown_v2(group.group_name)} \\(`{group.group_id}`\\)")
                
                groups_text = f"""
*📁 Monitored Groups* \\({len(groups)}\\)

{chr(10).join(groups_list)}

Use /addgroup to add more groups\\.
                """
            
            await bot.send_message(
                chat_id=chat_id,
                text=groups_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        elif command_text == '/watchlist':
            users = await db.watchlist_users.find({"is_active": True}).to_list(50)
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

Use /adduser to add more users\\.
                """
            
            await bot.send_message(
                chat_id=chat_id,
                text=watchlist_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="Unknown command\\. Use /help to see available commands\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    
    except Exception as e:
        logging.error(f"Error handling bot command: {e}")

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
        "total_messages": await db.message_logs.count_documents({}),
        "total_forwarded": await db.message_logs.count_documents({"is_forwarded": True}),
        "messages_today": await db.message_logs.count_documents({
            "timestamp": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
        }),
        "last_updated": datetime.now(timezone.utc)
    }
    
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
    
    return stats

# Telegram Webhook Route
@api_router.post("/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request, background_tasks: BackgroundTasks):
    """Handle Telegram webhook updates"""
    if secret != os.environ.get('WEBHOOK_SECRET'):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, bot)
        
        # Process in background to avoid blocking
        background_tasks.add_task(handle_telegram_message, update)
        
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

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
