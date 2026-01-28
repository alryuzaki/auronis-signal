import os
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database import BotDatabase
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_USER_ID", 0))
db = BotDatabase()

def get_user_role(user_id: int):
    if user_id == ADMIN_ID:
        return "Super Admin"
    user = db.get_user(user_id)
    if user:
        return user['role_name']
    return None

def restricted(allowed_roles):
    def decorator(func):
        @wraps(func)
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            role = get_user_role(user_id)
            
            if role in allowed_roles or user_id == ADMIN_ID:
                return await func(update, context, *args, **kwargs)
            else:
                await update.message.reply_text("⛔ You do not have permission to use this command.")
        return wrapped
    return decorator

def super_admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id == ADMIN_ID:
            return await func(update, context, *args, **kwargs)
        else:
            await update.message.reply_text("⛔ This command is for Super Admin only.")
    return wrapped
