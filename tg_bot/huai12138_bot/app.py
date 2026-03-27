import logging
import httpx
import json
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from dotenv import load_dotenv

# ========== Import HA Module ==========
import ha

# ========== Load Environment Variables ==========
load_dotenv()

# ========== Logging Configuration (WARNING level) ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ========== Telegram Configuration ==========
token = os.getenv("BOT_TOKEN")
admin_id = os.getenv("ADMIN_ID")
target_url = os.getenv("URL")
webhook_host = os.getenv("WEBHOOK_HOST")

if not token or not admin_id or not webhook_host:
    raise ValueError("Please set BOT_TOKEN, ADMIN_ID and WEBHOOK_HOST in .env file")

# ========== Block/White Lists ==========
block_file_path = "blocked_users.json"
blocked_users = set()
whitelist_file_path = "whitelist.json"
whitelist_users = set()

def load_blocked_users():
    global blocked_users
    if os.path.exists(block_file_path):
        try:
            with open(block_file_path, "r", encoding="utf-8") as f:
                blocked_users = set(json.load(f))
        except Exception as e:
            logging.error(f"Error loading blocked users: {e}")

def save_blocked_users():
    try:
        with open(block_file_path, "w", encoding="utf-8") as f:
            json.dump(list(blocked_users), f)
    except Exception as e:
        logging.error(f"Error saving blocked users: {e}")

load_blocked_users()

def load_whitelist_users():
    global whitelist_users
    if os.path.exists(whitelist_file_path):
        try:
            with open(whitelist_file_path, "r", encoding="utf-8") as f:
                whitelist_users = set(json.load(f))
        except Exception as e:
            logging.error(f"Error loading whitelist users: {e}")

def save_whitelist_users():
    try:
        with open(whitelist_file_path, "w", encoding="utf-8") as f:
            json.dump(list(whitelist_users), f)
    except Exception as e:
        logging.error(f"Error saving whitelist users: {e}")

load_whitelist_users()

# ========== Constants and Strategies ==========
MAX_MSG_LEN = 15
CHAT_CACHE_TTL = 60

# ========== Ban Strategy Functions ==========
def strategy_non_text(message):
    if not message.text:
        return "Non-text message"
    return None

def strategy_too_long(message):
    if message.text and len(message.text) > MAX_MSG_LEN:
        return f"Message too long: {len(message.text)} chars"
    return None

BAN_STRATEGIES = [strategy_non_text, strategy_too_long]

# ========== List Mutex Helpers ==========
def add_to_blocklist(user_id: str):
    if user_id in whitelist_users:
        whitelist_users.remove(user_id)
        save_whitelist_users()
    blocked_users.add(user_id)
    save_blocked_users()

def add_to_whitelist(user_id: str):
    if user_id in blocked_users:
        blocked_users.remove(user_id)
        save_blocked_users()
    whitelist_users.add(user_id)
    save_whitelist_users()

# ========== Unified Ban Notification Utilities ==========
def _render_ban_notice(user_id, name, username, reason):
    lines = ["Banned user"]
    if name or username:
        if username:
            uname = f"@{username}"
            if name:
                lines.append(f"Name: {name} ({uname})")
            else:
                lines.append(f"Name: {uname}")
        else:
            lines.append(f"Name: {name}")
    lines.append(f"User ID: {user_id}")
    if reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines)

def _render_unban_notice(user_id, name, username, reason):
    lines = ["Unbanned user"]
    if name or username:
        if username:
            uname = f"@{username}"
            if name:
                lines.append(f"Name: {name} ({uname})")
            else:
                lines.append(f"Name: {uname}")
        else:
            lines.append(f"Name: {name}")
    lines.append(f"User ID: {user_id}")
    if reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines)

async def notify_admin_ban(context: CallbackContext, user_id, reason, user=None):
    name = getattr(user, "first_name", None) if user else None
    username = getattr(user, "username", None) if user else None
    
    if not user:
        try:
            chat = await context.bot.get_chat(int(user_id))
            name = getattr(chat, "first_name", None)
            username = getattr(chat, "username", None)
        except Exception:
            pass
            
    text = _render_ban_notice(user_id, name, username, reason)
    await context.bot.send_message(admin_id, text)

# ========== Ban/Unban Helpers ==========
async def ban_user(
    context: CallbackContext,
    user_id: str,
    reason: str,
    user_obj=None,
    actor_admin_id: str | None = None,
):
    add_to_blocklist(user_id)

    # Silent ban, do not notify admin of auto-bans
    if (
        reason.startswith("Immediate Ban")
        or reason.startswith("Message too long")
        or reason == "Non-text message"
    ):
        return

    if actor_admin_id == admin_id:
        return
        
    try:
        await notify_admin_ban(context, user_id, reason, user_obj)
    except Exception as e:
        logging.error(f"Failed to notify admin of ban: {e}")

async def unban_user(
    context: CallbackContext,
    user_id: str,
    reason: str,
    user_obj=None,
    actor_admin_id: str | None = None,
):
    if user_id in blocked_users:
        blocked_users.remove(user_id)
        save_blocked_users()
        
    try:
        await context.bot.send_message(user_id, "Unbanned!")
    except Exception:
        pass
        
    if actor_admin_id == admin_id:
        return
        
    try:
        name = getattr(user_obj, "first_name", None) if user_obj else None
        username = getattr(user_obj, "username", None) if user_obj else None
        text = _render_unban_notice(user_id, name, username, reason)
        await context.bot.send_message(admin_id, text)
    except Exception as e:
        logging.error(f"Failed to notify admin of unban: {e}")

# ========== Extract User ID Helper ==========
def extract_user_id_from_text(text: str):
    try:
        for label in ("User ID:", "用户ID:"):
            if label in text:
                part = text.split(label, 1)[1].strip()
                line = part.split("\n", 1)[0].strip()
                digits = "".join(ch for ch in line if ch.isdigit())
                return digits if digits else None
        buf = []
        for ch in text:
            if ch.isdigit():
                buf.append(ch)
            elif buf:
                break
        if buf:
            return "".join(buf)
    except Exception:
        pass
    return None

# ========== Bot Commands ==========

async def start(update: Update, context: CallbackContext):
    if not update.effective_user or update.effective_chat.type != "private":
        return

    user_id = str(update.effective_user.id)

    if user_id == admin_id:
        await update.message.reply_text("I'm online Master!")
        return

    if user_id in blocked_users:
        return

    if user_id in whitelist_users:
        await update.message.reply_text("You are already verified.")
        return

    await update.message.reply_text('Send "Hi" to complete verification (case-sensitive)')

async def ping(update: Update, context: CallbackContext):
    if not update.effective_user or str(update.effective_user.id) != admin_id:
        return
    await update.message.reply_text("Pong!")

async def s_command(update: Update, _context: CallbackContext):
    if not update.effective_user:
        return
        
    user_id = str(update.effective_user.id)
    
    if user_id in blocked_users:
        return
        
    if user_id != admin_id:
        await ban_user(_context, user_id, "Unauthorized /s command", update.effective_user)
        return
        
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(target_url, timeout=10.0)
        if response.status_code == 200:
            await update.message.reply_text("OK")
        else:
            await update.message.reply_text("Er")
    except httpx.RequestError:
        await update.message.reply_text("Er")

async def ban(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != admin_id:
        return
        
    try:
        user_to_ban = None
        if update.message.reply_to_message:
            original_text = update.message.reply_to_message.text or ""
            user_to_ban = extract_user_id_from_text(original_text)
        elif context.args:
            user_to_ban = context.args[0]
            
        if user_to_ban:
            try:
                chat = await context.bot.get_chat(int(user_to_ban))
            except Exception:
                chat = None
                
            await ban_user(
                context,
                user_to_ban,
                "Manual ban",
                chat,
                actor_admin_id=admin_id,
            )
            
            # Provide feedback only to admin
            try:
                name = getattr(chat, "first_name", None) if chat else None
                username = getattr(chat, "username", None) if chat else None
                text = _render_ban_notice(user_to_ban, name, username, "Manual ban")
                await update.message.reply_text(text)
            except Exception:
                pass
        else:
            await update.message.reply_text("Usage: /ban <user_id> or reply to a message")
    except Exception as e:
        await update.message.reply_text(f"Error banning user: {str(e)}")

async def unban(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != admin_id:
        return
        
    try:
        user_to_unban = None
        if update.message.reply_to_message:
            original_text = update.message.reply_to_message.text or ""
            user_to_unban = extract_user_id_from_text(original_text)
        elif context.args:
            user_to_unban = context.args[0]
            
        if user_to_unban:
            if user_to_unban in blocked_users:
                try:
                    chat = await context.bot.get_chat(int(user_to_unban))
                except Exception:
                    chat = None
                    
                await unban_user(
                    context,
                    user_to_unban,
                    "Manual unban",
                    chat,
                    actor_admin_id=admin_id,
                )
                
                try:
                    name = getattr(chat, "first_name", None) if chat else None
                    username = getattr(chat, "username", None) if chat else None
                    text = _render_unban_notice(user_to_unban, name, username, "Manual unban")
                    await update.message.reply_text(text)
                except Exception:
                    pass
            else:
                await update.message.reply_text(f"User {user_to_unban} was not banned")
        else:
            await update.message.reply_text("Usage: /unban <user_id> or reply to a message")
    except Exception as e:
        await update.message.reply_text(f"Error unbanning user: {str(e)}")

async def forward_to_admin(update: Update, context: CallbackContext):
    message = update.message
    if not message:
        return

    user = message.from_user
    if not user:
        return

    chat_id = message.chat.id
    user_id = str(chat_id)

    if user_id in blocked_users:
        return

    # ========== Strict Verification Logic ==========
    if user_id != admin_id:
        # 1. Strictly match "Hi"
        if message.text == "Hi":
            if user_id not in whitelist_users:
                add_to_whitelist(user_id)
                await update.message.reply_text("Success! You are verified.")

                admin_msg = f"New user verified:\nName: {user.first_name} (@{user.username if user.username else 'No username'})\nUser ID: {user_id}"
                await context.bot.send_message(admin_id, admin_msg)
                return
            # If already in whitelist, treat as normal message

        # 2. Not "Hi" and not in whitelist -> Immediate ban
        elif user_id not in whitelist_users:
            await ban_user(
                context,
                user_id,
                "Immediate Ban: Unauthorized message (not 'Hi')",
                user,
            )
            return

    if str(chat_id) != admin_id:
        # Check message type and length limits
        for strategy in BAN_STRATEGIES:
            reason = strategy(message)
            if reason:
                await ban_user(context, user_id, reason, user)
                return
                
        try:
            sender_content = (
                f"From user: {user.first_name} (@{user.username if user.username else 'No username'})\n"
                f"User ID: {chat_id}\n"
                f"------------------------\n"
                f"{message.text}"
            )
            await context.bot.send_message(admin_id, sender_content)

            if "user_chat_ids" not in context.bot_data:
                context.bot_data["user_chat_ids"] = {}
            context.bot_data["user_chat_ids"][str(chat_id)] = chat_id
            await message.reply_text("Forwarded, please wait for a reply.")
        except Exception as e:
            logging.error(f"Error forwarding message: {e}")
            await message.reply_text("Forwarding failed.")
    else:
        # Admin reply logic
        if message.reply_to_message:
            try:
                original_text = message.reply_to_message.text or ""
                user_id_to_reply = extract_user_id_from_text(original_text)
                
                if user_id_to_reply:
                    # Shortcut command /ban
                    if message.text and message.text.lower() == "/ban":
                        try:
                            chat = await context.bot.get_chat(int(user_id_to_reply))
                        except Exception:
                            chat = None
                            
                        await ban_user(
                            context,
                            user_id_to_reply,
                            "Manual ban",
                            chat,
                            actor_admin_id=admin_id,
                        )
                        
                        try:
                            name = getattr(chat, "first_name", None) if chat else None
                            username = getattr(chat, "username", None) if chat else None
                            text = _render_ban_notice(user_id_to_reply, name, username, "Manual ban")
                            await update.message.reply_text(text)
                        except Exception:
                            pass
                        return
                        
                    # Shortcut command /unban
                    elif message.text and message.text.lower() == "/unban":
                        if user_id_to_reply in blocked_users:
                            try:
                                chat = await context.bot.get_chat(int(user_id_to_reply))
                            except Exception:
                                chat = None
                                
                            await unban_user(
                                context,
                                user_id_to_reply,
                                "Manual unban",
                                chat,
                                actor_admin_id=admin_id,
                            )
                            
                            try:
                                name = getattr(chat, "first_name", None) if chat else None
                                username = getattr(chat, "username", None) if chat else None
                                text = _render_unban_notice(user_id_to_reply, name, username, "Manual unban")
                                await update.message.reply_text(text)
                            except Exception:
                                pass
                        else:
                            await update.message.reply_text(f"User {user_id_to_reply} was not banned")
                        return
                        
                    # Normal reply
                    await context.bot.send_message(user_id_to_reply, message.text)
                    await update.message.reply_text("Replied.")
                else:
                    await update.message.reply_text("Please reply to a message with a User ID.")
            except Exception as e:
                logging.error(f"Error replying to message: {e}")
                await update.message.reply_text("Reply failed.")
        else:
            # Admin sends plain text without replying -> Delegate to ha module
            if message.text and not message.text.startswith("/"):
                parts = message.text.strip().split()
                room = parts[0]
                action = parts[1] if len(parts) > 1 else "turn_off"
                
                if room in ha.DEVICE_MAP:
                    ha.control_device(room, action)
                    await update.message.reply_text("OK")
                else:
                    await update.message.reply_text("Er")

# ========== /zh Command - Set Chinese Language ==========
async def set_chinese(update: Update, context: CallbackContext):
    link = "tg://setlanguage?lang=zhcncc"
    await update.message.reply_text(text=f"[Set Chinese]({link})", parse_mode="Markdown")

# ========== Post Initialization Notification ==========
async def post_initialization(application: Application):
    try:
        await application.bot.send_message(chat_id=admin_id, text="Hi Master I'm online")
    except Exception as e:
        logging.error(f"Error sending initialization message: {e}")

# ========== Main Entry ==========
def main():
    application = (
        Application.builder().token(token).post_init(post_initialization).build()
    )

    # Register commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("s", s_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("zh", set_chinese))

    # Only receive text messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_admin)
    )

    # Webhook startup
    webhook_port = int(os.getenv("WEBHOOK_PORT", 5005))
    webhook_listen = os.getenv("WEBHOOK_LISTEN", "0.0.0.0")
    webhook_secret_token = os.getenv("WEBHOOK_SECRET_TOKEN")
    webhook_path = os.getenv("WEBHOOK_PATH", "")

    if webhook_path and not webhook_path.startswith("/"):
        webhook_path = f"/{webhook_path}"

    clean_webhook_host = webhook_host.rstrip("/")
    webhook_url = f"{clean_webhook_host}{webhook_path}"

    print(f"Bot is working")
 
    url_path = webhook_path.lstrip("/") if webhook_path else token

    application.run_webhook(
        listen=webhook_listen,
        port=webhook_port,
        url_path=url_path,
        webhook_url=webhook_url,
        secret_token=webhook_secret_token,
        # Only receive Message updates
        allowed_updates=["message"],
    )

if __name__ == "__main__":
    main()