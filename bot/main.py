import logging
import json
import os
import re
import tempfile
from contextlib import suppress
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
)

# ========== Load Environment Variables ==========
load_dotenv()

# ========== Logging Configuration ==========
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.WARNING)

# ========== Configuration & Constants ==========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
TARGET_URL = os.getenv("URL")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")

if not all([TOKEN, ADMIN_ID, WEBHOOK_HOST]):
    raise ValueError("Missing essential environment variables.")

MAX_MSG_LEN = 15
BLOCK_FILE = "blocked_users.json"
WHITE_FILE = "whitelist.json"

# ========== File/Set Management ==========
def load_set(path):
    with suppress(Exception):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return set(json.load(f))
    return set()

def save_set(path, data_set):
    # Atomic write to prevent data corruption during concurrent operations
    with suppress(Exception):
        dir_name = os.path.dirname(path) or "."
        fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(list(data_set), f)
        os.replace(temp_path, path)

blocked_users = load_set(BLOCK_FILE)
whitelist_users = load_set(WHITE_FILE)

def update_user_status(user_id: str, to_block: bool):
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
    with suppress(Exception):
        await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)

async def send_temp_message(update: Update, context: CallbackContext, text: str, delay: int = 30, **kwargs):
    msg = await update.message.reply_text(text, **kwargs)
    context.job_queue.run_once(delete_message_job, when=delay, chat_id=update.effective_chat.id, data=msg.message_id)
    return msg

def extract_user_id(text: str):
    # Strict extraction
    match = re.search(r'(?:User ID:|用户ID:)\s*(\d+)', text or "")
    return match.group(1) if match else None

def render_notice(action: str, user_id: str, user_obj=None, reason: str = ""):
    lines = [f"{action} user"]
    if user_obj:
        name, uname = getattr(user_obj, "first_name", ""), getattr(user_obj, "username", "")
        if name or uname:
            lines.append(f"Name: {name} (@{uname})" if uname else f"Name: {name}")
    lines.append(f"User ID: {user_id}")
    if reason: lines.append(f"Reason: {reason}")
    return "\n".join(lines)

# ========== Core Bot Actions ==========
async def handle_ban_action(context: CallbackContext, user_id: str, reason: str, is_ban: bool, notify_admin: bool = False):
    update_user_status(user_id, to_block=is_ban)
    
    if not is_ban:
        with suppress(Exception):
            await context.bot.send_message(user_id, "Unbanned!")

    if notify_admin:
        user_obj = None
        with suppress(Exception):
            user_obj = await context.bot.get_chat(int(user_id))
        action_str = "Banned" if is_ban else "Unbanned"
        await context.bot.send_message(ADMIN_ID, render_notice(action_str, user_id, user_obj, reason))

# ========== Command Handlers ==========
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if not user or update.effective_chat.type != "private": return
    uid = str(user.id)

    if uid == ADMIN_ID: return await send_temp_message(update, context, "I'm online Master!")
    if uid in blocked_users: return
    if uid in whitelist_users: return await send_temp_message(update, context, "Verified.")
    await update.message.reply_text('Send "Hi" to complete verification (case-sensitive)')

async def s_command(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    if uid in blocked_users: return
    if uid != ADMIN_ID:
        return await handle_ban_action(context, uid, "Unauthorized /s command", is_ban=True, notify_admin=True)

    import httpx
    with suppress(httpx.RequestError):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.get(TARGET_URL, timeout=10.0)
            return await send_temp_message(update, context, "OK" if res.status_code == 200 else "Er")
    await send_temp_message(update, context, "Er")

async def toggle_ban(update: Update, context: CallbackContext, is_ban: bool):
    if str(update.effective_user.id) != ADMIN_ID: return

    uid_target = extract_user_id(update.message.reply_to_message.text) if update.message.reply_to_message else (context.args[0] if context.args else None)
    
    if not uid_target:
        return await send_temp_message(update, context, f"Usage: /{'ban' if is_ban else 'unban'} <user_id> or reply")

    if not is_ban and uid_target not in blocked_users:
        return await send_temp_message(update, context, f"User {uid_target} was not banned")

    reason = f"Manual {'ban' if is_ban else 'unban'}"
    await handle_ban_action(context, uid_target, reason, is_ban, notify_admin=False)
    
    chat = None
    with suppress(Exception): chat = await context.bot.get_chat(int(uid_target))
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
            return
        
        if chat_id not in whitelist_users:
            return await handle_ban_action(context, chat_id, "Immediate Ban: Unauthorized message", is_ban=True, notify_admin=False)

        if not msg.text: return await handle_ban_action(context, chat_id, "Non-text message", is_ban=True, notify_admin=False)
        if len(msg.text) > MAX_MSG_LEN: return await handle_ban_action(context, chat_id, "Message too long", is_ban=True, notify_admin=False)
        
        # Ban immediately if verified user sends "Hi" again
        if msg.text == "Hi":
            return await handle_ban_action(context, chat_id, "Immediate Ban: Sent 'Hi' after verification", is_ban=True, notify_admin=False)

        # Forwarding
        content = f"From user: {user.first_name} (@{user.username or 'No username'})\nUser ID: {chat_id}\n---\n{msg.text}"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Ban", callback_data=f"ban_{chat_id}")]])
        with suppress(Exception):
            await context.bot.send_message(ADMIN_ID, content, reply_markup=markup)
            await send_temp_message(update, context, "Forwarded, please wait for a reply.")
        return

    # Admin Logic
    if msg.reply_to_message:
        target_id = extract_user_id(msg.reply_to_message.text)
        if not target_id: return await send_temp_message(update, context, "Please reply to a message with a User ID.")
            
        text_lower = msg.text.lower() if msg.text else ""
        if text_lower == "/ban": return await ban(update, context)
        if text_lower == "/unban": return await unban(update, context)

        with suppress(Exception):
            await context.bot.send_message(target_id, msg.text)
            await send_temp_message(update, context, "Replied.")

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if str(update.effective_user.id) != ADMIN_ID or not query.data.startswith("ban_"): return

    target_id = query.data.split("_")[1]
    await handle_ban_action(context, target_id, "Quick ban via button", is_ban=True, notify_admin=True)
    with suppress(Exception):
        await query.edit_message_reply_markup(reply_markup=None)

async def post_init(app: Application):
    with suppress(Exception):
        await app.bot.send_message(chat_id=ADMIN_ID, text="Hi Master I'm online")

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