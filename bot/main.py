import logging
import httpx
import json
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
)
from dotenv import load_dotenv

# ========== Load Environment Variables ==========
load_dotenv()

# ========== Logging Configuration ==========
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ========== Configuration & Constants ==========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
TARGET_URL = os.getenv("URL")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")

if not all([TOKEN, ADMIN_ID, WEBHOOK_HOST]):
    raise ValueError("Please check .env file")

MAX_MSG_LEN = 15
BLOCK_FILE = "blocked_users.json"
WHITE_FILE = "whitelist.json"

# ========== File/Set Management ==========
def load_set(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            logging.error(f"Error loading {path}: {e}")
    return set()

def save_set(path, data_set):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(data_set), f)
    except Exception as e:
        logging.error(f"Error saving {path}: {e}")

blocked_users = load_set(BLOCK_FILE)
whitelist_users = load_set(WHITE_FILE)

def update_user_status(user_id: str, to_block: bool):
    # Add to target list and remove from the other, then save
    if to_block:
        blocked_users.add(user_id)
        whitelist_users.discard(user_id)
    else:
        whitelist_users.add(user_id)
        blocked_users.discard(user_id)
    save_set(BLOCK_FILE, blocked_users)
    save_set(WHITE_FILE, whitelist_users)

# ========== Helpers ==========
async def delete_message_job(context: CallbackContext):
    try:
        await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)
    except Exception: pass

async def send_temp_message(update: Update, context: CallbackContext, text: str, delay: int = 30, **kwargs):
    msg = await update.message.reply_text(text, **kwargs)
    context.job_queue.run_once(delete_message_job, when=delay, chat_id=update.effective_chat.id, data=msg.message_id)
    return msg

def extract_user_id(text: str):
    # Regex to simplify user ID extraction
    match = re.search(r'(?:User ID:|用户ID:)\s*(\d+)', text)
    if match: return match.group(1)
    match = re.search(r'\d+', text)
    return match.group(0) if match else None

def render_notice(action: str, user_id: str, user_obj=None, reason: str = ""):
    lines = [f"{action} user"]
    if user_obj:
        name = getattr(user_obj, "first_name", "")
        uname = getattr(user_obj, "username", "")
        if name or uname:
            lines.append(f"Name: {name} (@{uname})" if uname else f"Name: {name}")
    lines.append(f"User ID: {user_id}")
    if reason: lines.append(f"Reason: {reason}")
    return "\n".join(lines)

# ========== Ban Strategies ==========
def check_strategies(message):
    if not message.text: return "Non-text message"
    if len(message.text) > MAX_MSG_LEN: return f"Message too long: {len(message.text)} chars"
    return None

# ========== Core Bot Actions ==========
async def handle_ban_action(context: CallbackContext, user_id: str, reason: str, is_ban: bool, user_obj=None, admin_actor: bool = False):
    update_user_status(user_id, to_block=is_ban)
    
    if not is_ban:
        try: await context.bot.send_message(user_id, "Unbanned!")
        except Exception: pass

    if admin_actor or (is_ban and reason in ("Non-text message", "Immediate Ban") or reason.startswith("Message too long")):
        return # Skip admin notification for specific cases

    if not user_obj and is_ban:
        try: user_obj = await context.bot.get_chat(int(user_id))
        except Exception: pass

    action_str = "Banned" if is_ban else "Unbanned"
    await context.bot.send_message(ADMIN_ID, render_notice(action_str, user_id, user_obj, reason))

# ========== Command Handlers ==========
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if not user or update.effective_chat.type != "private": return
    uid = str(user.id)

    if uid == ADMIN_ID:
        return await send_temp_message(update, context, "I'm online Master!")
    if uid in blocked_users: return
    if uid in whitelist_users:
        return await send_temp_message(update, context, "Verified.")
    await update.message.reply_text('Send "Hi" to complete verification (case-sensitive)')

async def s_command(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    if uid in blocked_users: return
    if uid != ADMIN_ID:
        return await handle_ban_action(context, uid, "Unauthorized /s command", True, update.effective_user)

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.get(TARGET_URL, timeout=10.0)
        await send_temp_message(update, context, "OK" if res.status_code == 200 else "Er")
    except httpx.RequestError:
        await send_temp_message(update, context, "Er")

async def toggle_ban(update: Update, context: CallbackContext, is_ban: bool):
    if str(update.effective_user.id) != ADMIN_ID: return

    uid_target = extract_user_id(update.message.reply_to_message.text) if update.message.reply_to_message else (context.args[0] if context.args else None)
    
    if not uid_target:
        return await send_temp_message(update, context, f"Usage: /{'ban' if is_ban else 'unban'} <user_id> or reply")

    if not is_ban and uid_target not in blocked_users:
        return await send_temp_message(update, context, f"User {uid_target} was not banned")

    try: chat = await context.bot.get_chat(int(uid_target))
    except Exception: chat = None

    reason = f"Manual {'ban' if is_ban else 'unban'}"
    await handle_ban_action(context, uid_target, reason, is_ban, chat, admin_actor=True)
    await send_temp_message(update, context, render_notice("Banned" if is_ban else "Unbanned", uid_target, chat, reason))

async def ban(update: Update, context: CallbackContext): await toggle_ban(update, context, True)
async def unban(update: Update, context: CallbackContext): await toggle_ban(update, context, False)

async def forward_to_admin(update: Update, context: CallbackContext):
    msg, user = update.message, update.effective_user
    if not msg or not user: return
    
    chat_id = str(msg.chat.id)
    if chat_id in blocked_users: return

    # User Logic
    if chat_id != ADMIN_ID:
        if msg.text == "Hi" and chat_id not in whitelist_users:
            update_user_status(chat_id, to_block=False)
            await send_temp_message(update, context, "Success!")
            return await context.bot.send_message(ADMIN_ID, f"New user verified:\nName: {user.first_name} (@{user.username or 'No username'})\nUser ID: {chat_id}")
        
        if chat_id not in whitelist_users:
            return await handle_ban_action(context, chat_id, "Immediate Ban: Unauthorized message", True, user)

        if reason := check_strategies(msg):
            return await handle_ban_action(context, chat_id, reason, True, user)

        # Forwarding
        content = f"From user: {user.first_name} (@{user.username or 'No username'})\nUser ID: {chat_id}\n---\n{msg.text}"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Ban", callback_data=f"ban_{chat_id}")]])
        try:
            await context.bot.send_message(ADMIN_ID, content, reply_markup=markup)
            await send_temp_message(update, context, "Forwarded, please wait for a reply.")
        except Exception as e:
            logging.error(f"Forward error: {e}")
            await msg.reply_text("Forwarding failed.")
        return

    # Admin Logic
    if msg.reply_to_message:
        target_id = extract_user_id(msg.reply_to_message.text)
        if not target_id:
            return await send_temp_message(update, context, "Please reply to a message with a User ID.")
            
        text_lower = msg.text.lower() if msg.text else ""
        if text_lower == "/ban": return await ban(update, context)
        if text_lower == "/unban": return await unban(update, context)

        try:
            await context.bot.send_message(target_id, msg.text)
            await send_temp_message(update, context, "Replied.")
        except Exception as e:
            logging.error(f"Reply error: {e}")
            await send_temp_message(update, context, "Reply failed.")

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if str(update.effective_user.id) != ADMIN_ID or not query.data.startswith("ban_"): return

    target_id = query.data.split("_")[1]
    try: chat = await context.bot.get_chat(int(target_id))
    except Exception: chat = None

    await handle_ban_action(context, target_id, "Quick ban via button", True, chat, admin_actor=True)
    await context.bot.send_message(ADMIN_ID, render_notice("Banned", target_id, chat, "Quick ban via button"))
    await query.edit_message_reply_markup(reply_markup=None)

async def post_init(app: Application):
    try: await app.bot.send_message(chat_id=ADMIN_ID, text="Hi Master I'm online")
    except Exception as e: logging.error(f"Init msg error: {e}")

# ========== Main ==========
def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handlers([
        CommandHandler("start", start),
        CommandHandler("ban", ban),
        CommandHandler("unban", unban),
        CommandHandler("s", s_command),
        CallbackQueryHandler(button_callback),
        MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_admin)
    ])

    port = int(os.getenv("WEBHOOK_PORT", 5005))
    path = f"/{os.getenv('WEBHOOK_PATH', '').lstrip('/')}"
    url = f"{WEBHOOK_HOST.rstrip('/')}{path}"
    
    print("Bot is working")
    app.run_webhook(
        listen=os.getenv("WEBHOOK_LISTEN", "0.0.0.0"),
        port=port,
        url_path=path.lstrip("/") or TOKEN,
        webhook_url=url,
        secret_token=os.getenv("WEBHOOK_SECRET_TOKEN"),
        allowed_updates=["message", "callback_query"],
    )

if __name__ == "__main__":
    main()