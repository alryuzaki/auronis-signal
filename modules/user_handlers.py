from telegram import Update
from telegram.ext import ContextTypes
from database import BotDatabase

db = BotDatabase()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Auto-register
    db.add_user(user.id, user.username or user.first_name, "Viewer")
    
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        "Welcome to the Financial Signals Bot.\n"
        "Use /help to see available commands.\n"
        "Use /subscribe to view packages."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 **Available Commands:**\n\n"
        "👤 **User:**\n"
        "/start - Register and welcome\n"
        "/myprofile - Check subscription status\n"
        "/subscribe <id> - Subscribe to a package\n"
        "/listpackages - View available packages\n\n"
        "🛠 **Admin (Super Admin only):**\n"
        "/createrole, /listroles\n"
        "/createpackage, /listpackages\n"
        "/addmember, /announce\n"
        "/schedule"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    sub = db.get_user_subscription(user_id)
    
    if not user:
        await update.message.reply_text("You are not registered. /start first.")
        return

    text = f"👤 **Profile:**\nName: {user['username']}\nRole: {user['role_name']}\n\n"
    
    if sub:
        text += f"💎 **Subscription:** {sub['package_name']}\n"
        text += f"📅 Expires: {sub['end_date']}\n"
        text += f"Status: {sub['status']}"
    else:
        text += "❌ No active subscription."
        
    await update.message.reply_text(text, parse_mode='Markdown')

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /subscribe <package_id>"""
    try:
        pkg_id = int(context.args[0])
        user_id = update.effective_user.id
        
        # In a real bot, you'd handle payment here.
        # For this task, we assume immediate success.
        if db.add_subscription(user_id, pkg_id):
            sub = db.get_user_subscription(user_id)
            await update.message.reply_text(f"✅ Successfully subscribed to **{sub['package_name']}**!\nExpires: {sub['end_date']}", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Invalid Package ID or Package not found.")
            
    except (IndexError, ValueError):
        # List packages if no ID provided
        pkgs = db.get_packages()
        text = "📦 **Available Packages:**\n(Use `/subscribe <id>`)\n\n"
        for p in pkgs:
            text += f"ID: `{p['id']}` | {p['name']} | ${p['price']} | {p['duration_days']} days\n"
        await update.message.reply_text(text, parse_mode='Markdown')
