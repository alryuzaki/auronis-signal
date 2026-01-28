from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import BotDatabase
from modules.utils import super_admin_only

db = BotDatabase()

@super_admin_only
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /settings"""
    
    # Get current state
    maintenance = db.get_setting("maintenance_mode", "0")
    
    status_emoji = "🟢 ON" if maintenance == "0" else "🔴 MAINTENANCE"
    
    keyboard = [
        [InlineKeyboardButton(f"Maintenance Mode: {status_emoji}", callback_data="toggle_maintenance")],
        [InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        "⚙️ **System Settings**\n\n"
        f"**Bot Status**: {status_emoji}\n"
        "Click buttons below to toggle."
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "toggle_maintenance":
        current = db.get_setting("maintenance_mode", "0")
        new_val = "1" if current == "0" else "0"
        db.set_setting("maintenance_mode", new_val)
        
        # Refresh menu
        await settings_menu(update, context)
        
    elif data == "refresh_settings":
        await settings_menu(update, context)

# --- Middleware to check Maintenance ---
async def maintenance_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Middleware to block user commands if maintenance mode is ON.
    Exceptions: Super Admin
    """
    if not update.effective_user:
        return
        
    user_id = update.effective_user.id
    admin_id = int(context.bot_data.get('admin_id', 0)) # Assuming we store this
    
    # Need to load admin ID from Env if not in context
    import os
    real_admin_id = int(os.getenv("ADMIN_USER_ID", 0))
    
    if user_id == real_admin_id:
        return # Admin always allowed
        
    is_maintenance = db.get_setting("maintenance_mode", "0") == "1"
    
    if is_maintenance:
        # If it's a message/command
        if update.message:
            await update.message.reply_text("🚧 **System Maintenance**\n\nThe bot is currently under maintenance. Please try again later.")
            # Stop handling (Raise error or return False to stop propagation? 
            # In PTB, we can't easily stop without a specific mechanism, 
            # usually we wrap handlers or use a high priority TypeHandler that raises ApplicationHandlerStop)
            from telegram.ext import ApplicationHandlerStop
            raise ApplicationHandlerStop
        
        if update.callback_query:
            await update.callback_query.answer("🚧 Maintenance Mode Active", show_alert=True)
            from telegram.ext import ApplicationHandlerStop
            raise ApplicationHandlerStop
