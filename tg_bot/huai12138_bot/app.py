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

# ========== 加载环境变量 ==========
load_dotenv()

# ========== 配置日志 (WARNING级别) ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ========== Telegram 配置 ==========
token = os.getenv("BOT_TOKEN")
admin_ids_str = os.getenv("ADMIN_IDS")
target_url = os.getenv("URL")
webhook_host = os.getenv("WEBHOOK_HOST")
s_canid = os.getenv("S_CANID")

if not token or not admin_ids_str or not webhook_host or not s_canid:
    raise ValueError(
        "请在.env文件中设置 BOT_TOKEN, ADMIN_IDS (用逗号分隔) 和 WEBHOOK_HOST"
    )

admin_ids = set(admin_ids_str.split(","))
primary_admin_id = admin_ids_str.split(",")[0]
s_canid_list = set(s_canid.split(","))


# ========== 封禁列表 ==========
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
            logging.error(f"加载封禁用户列表时出错: {e}")


def save_blocked_users():
    try:
        with open(block_file_path, "w", encoding="utf-8") as f:
            json.dump(list(blocked_users), f)
    except Exception as e:
        logging.error(f"保存封禁用户列表时出错: {e}")


load_blocked_users()


def load_whitelist_users():
    global whitelist_users
    if os.path.exists(whitelist_file_path):
        try:
            with open(whitelist_file_path, "r", encoding="utf-8") as f:
                whitelist_users = set(json.load(f))
        except Exception as e:
            logging.error(f"加载白名单用户列表时出错: {e}")


def save_whitelist_users():
    try:
        with open(whitelist_file_path, "w", encoding="utf-8") as f:
            json.dump(list(whitelist_users), f)
    except Exception as e:
        logging.error(f"保存白名单用户列表时出错: {e}")


load_whitelist_users()


# ========== 常量与策略配置 ==========
MAX_MSG_LEN = 15
CHAT_CACHE_TTL = 60


# ========== 封禁策略函数列表 ==========
def strategy_non_text(message):
    if not message.text:
        return "Non-text message"
    return None


def strategy_too_long(message):
    if message.text and len(message.text) > MAX_MSG_LEN:
        return f"Message too long: {len(message.text)} chars"
    return None


BAN_STRATEGIES = [strategy_non_text, strategy_too_long]


# ========== 黑白名单互斥辅助函数 ==========
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


# ========== 统一封禁通知工具 ==========
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
    name = None
    username = None
    if user is not None:
        name = getattr(user, "first_name", None)
        username = getattr(user, "username", None)
    else:
        try:
            chat = await context.bot.get_chat(int(user_id))
            name = getattr(chat, "first_name", None)
            username = getattr(chat, "username", None)
        except Exception:
            pass
    text = _render_ban_notice(user_id, name, username, reason)
    await context.bot.send_message(primary_admin_id, text)


# ========== ban / unban 辅助 ==========
async def ban_user(
    context: CallbackContext,
    user_id: str,
    reason: str,
    user_obj=None,
    actor_admin_id: str | None = None,
):
    add_to_blocklist(user_id)

    # 静默封禁，不通知管理员自动封禁事件
    if (
        reason.startswith("Immediate Ban")
        or reason.startswith("Message too long")
        or reason == "Non-text message"
    ):
        return

    if actor_admin_id == primary_admin_id:
        return
    try:
        await notify_admin_ban(context, user_id, reason, user_obj)
    except Exception as e:
        logging.error(f"管理员通知封禁失败: {e}")


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
    if actor_admin_id == primary_admin_id:
        return
    try:
        name = getattr(user_obj, "first_name", None) if user_obj else None
        username = getattr(user_obj, "username", None) if user_obj else None
        text = _render_unban_notice(user_id, name, username, reason)
        await context.bot.send_message(primary_admin_id, text)
    except Exception as e:
        logging.error(f"管理员通知解封失败: {e}")


# ========== 提取用户ID的辅助函数 ==========
def extract_user_id_from_text(text: str):
    try:
        for label in ("用户ID:", "User ID:"):
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


# ========== Bot 命令 ==========


async def start(update: Update, context: CallbackContext):
    if not update.effective_user:
        return

    # 仅允许私聊
    if update.effective_chat.type != "private":
        return

    user_id = str(update.effective_user.id)

    if user_id in admin_ids:
        await update.message.reply_text("I'm online Master!")
        return

    if user_id in blocked_users:
        return

    if user_id in whitelist_users:
        await update.message.reply_text("You are already verified.")
        return

    await update.message.reply_text(
        'Send "Hi" to complete verification (case-sensitive)'
    )


async def ping(update: Update, context: CallbackContext):
    if not update.effective_user:
        return
    user_id = str(update.effective_user.id)
    if user_id not in admin_ids:
        return
    await update.message.reply_text("Pong!")


async def s_command(update: Update, _context: CallbackContext):
    if not update.effective_user:
        return
    user_id = str(update.effective_user.id)
    if user_id in blocked_users:
        return
    if user_id not in admin_ids and user_id not in s_canid_list:
        await ban_user(
            _context,
            user_id,
            "Unauthorized /s command",
            update.effective_user,
            actor_admin_id=None,
        )
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
    if str(update.effective_user.id) not in admin_ids:
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
                actor_admin_id=str(update.effective_user.id),
            )
            # 仅给管理员反馈
            try:
                name = getattr(chat, "first_name", None) if chat else None
                username = getattr(chat, "username", None) if chat else None
                text = _render_ban_notice(user_to_ban, name, username, "Manual ban")
                await update.message.reply_text(text)
            except Exception:
                pass
        else:
            await update.message.reply_text(
                "Usage: /ban <user_id> or reply to a message"
            )
    except Exception as e:
        await update.message.reply_text(f"Error banning user: {str(e)}")


async def unban(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in admin_ids:
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
                    actor_admin_id=str(update.effective_user.id),
                )
                try:
                    name = getattr(chat, "first_name", None) if chat else None
                    username = getattr(chat, "username", None) if chat else None
                    text = _render_unban_notice(
                        user_to_unban, name, username, "Manual unban"
                    )
                    await update.message.reply_text(text)
                except Exception:
                    pass
            else:
                await update.message.reply_text(f"User {user_to_unban} was not banned")
        else:
            await update.message.reply_text(
                "Usage: /unban <user_id> or reply to a message"
            )
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

    # ========== 严格验证逻辑 ==========
    if user_id not in admin_ids:
        # 1. 严格匹配 "Hi"
        if message.text == "Hi":
            if user_id not in whitelist_users:
                add_to_whitelist(user_id)
                await update.message.reply_text("Success! You are verified.")

                admin_msg = f"New user verified:\nName: {user.first_name} (@{user.username if user.username else 'No username'})\nUser ID: {user_id}"
                await context.bot.send_message(primary_admin_id, admin_msg)
                return
            # 如果已在白名单，视为普通消息继续

        # 2. 消息不是 "Hi" 且用户不在白名单 -> 立即封禁
        elif user_id not in whitelist_users:
            await ban_user(
                context,
                user_id,
                "Immediate Ban: Unauthorized message (not 'Hi')",
                user,
                actor_admin_id=None,
            )
            return

    if str(chat_id) not in admin_ids:
        # 检查消息类型和长度限制
        for strategy in BAN_STRATEGIES:
            reason = strategy(message)
            if reason:
                await ban_user(
                    context,
                    user_id,
                    reason,
                    user,
                    actor_admin_id=None,
                )
                return
        try:
            sender_content = (
                f"From user: {user.first_name} (@{user.username if user.username else 'No username'})\n"
                f"User ID: {chat_id}\n"
                f"------------------------\n"
                f"{message.text}"
            )
            await context.bot.send_message(primary_admin_id, sender_content)

            if "user_chat_ids" not in context.bot_data:
                context.bot_data["user_chat_ids"] = {}
            context.bot_data["user_chat_ids"][str(chat_id)] = chat_id
            await message.reply_text("Forwarded, please wait for a reply.")
        except Exception as e:
            logging.error(f"转发消息时出错: {e}")
            await message.reply_text("Forwarding failed.")
    else:
        # 管理员回复逻辑
        if message.reply_to_message:
            try:
                original_text = message.reply_to_message.text or ""
                user_id_to_reply = extract_user_id_from_text(original_text)
                if user_id_to_reply:
                    # 快捷命令 /ban
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
                            actor_admin_id=str(update.effective_user.id),
                        )
                        try:
                            name = getattr(chat, "first_name", None) if chat else None
                            username = getattr(chat, "username", None) if chat else None
                            text = _render_ban_notice(
                                user_id_to_reply, name, username, "Manual ban"
                            )
                            await update.message.reply_text(text)
                        except Exception:
                            pass
                        return
                    # 快捷命令 /unban
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
                                actor_admin_id=str(update.effective_user.id),
                            )
                            try:
                                name = (
                                    getattr(chat, "first_name", None) if chat else None
                                )
                                username = (
                                    getattr(chat, "username", None) if chat else None
                                )
                                text = _render_unban_notice(
                                    user_id_to_reply, name, username, "Manual unban"
                                )
                                await update.message.reply_text(text)
                            except Exception:
                                pass
                        else:
                            await update.message.reply_text(
                                f"User {user_id_to_reply} was not banned"
                            )
                        return
                    # 普通回复
                    await context.bot.send_message(user_id_to_reply, message.text)
                    await update.message.reply_text("Replied.")
                else:
                    await update.message.reply_text(
                        "Please reply to a message with a User ID."
                    )
            except Exception as e:
                logging.error(f"回复消息时出错: {e}")
                await update.message.reply_text("Reply failed.")
        else:
            # 管理员发送非指令的纯文本（且未回复消息），以前是广播，现在直接提示回复
            if message.text and not message.text.startswith("/"):
                await update.message.reply_text(
                    "Please reply to a user message to send a reply."
                )


# ========== /zh 命令 - 设置中文语言 ==========
async def set_chinese(update: Update, context: CallbackContext):
    link = "tg://setlanguage?lang=zhcncc"
    await update.message.reply_text(
        text=f"[设置聪聪中文]({link})", parse_mode="Markdown"
    )


# ========== 启动后通知 ==========
async def post_initialization(application: Application):
    try:
        await application.bot.send_message(chat_id=primary_admin_id, text="I'm online")
    except Exception as e:
        logging.error(f"发送上线通知时出错: {e}")


# ========== 主入口 ==========
def main():
    application = (
        Application.builder().token(token).post_init(post_initialization).build()
    )

    # 注册命令
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("s", s_command))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("zh", set_chinese))

    # 仅接收文本消息
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_admin)
    )

    # Webhook 启动
    webhook_port = int(os.getenv("WEBHOOK_PORT", 5005))
    webhook_listen = os.getenv("WEBHOOK_LISTEN", "0.0.0.0")
    webhook_secret_token = os.getenv("WEBHOOK_SECRET_TOKEN")
    webhook_path = os.getenv("WEBHOOK_PATH", "")

    if webhook_path and not webhook_path.startswith("/"):
        webhook_path = f"/{webhook_path}"

    clean_webhook_host = webhook_host.rstrip("/")
    webhook_url = f"{clean_webhook_host}{webhook_path}"

    print(f"以 Webhook 模式启动机器人 (无MC功能)")
    print(f"监听地址: {webhook_listen}:{webhook_port}")
    print(f"Webhook URL: {webhook_url}")

    url_path = webhook_path.lstrip("/") if webhook_path else token

    application.run_webhook(
        listen=webhook_listen,
        port=webhook_port,
        url_path=url_path,
        webhook_url=webhook_url,
        secret_token=webhook_secret_token,
        # 只接收 Message 更新
        allowed_updates=["message"],
    )


if __name__ == "__main__":
    main()
