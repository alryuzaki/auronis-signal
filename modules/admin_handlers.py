from telegram import Update
from telegram.ext import ContextTypes
from database import BotDatabase
from modules.utils import super_admin_only
from modules.signals import SignalGenerator
from modules.news import NewsAggregator
from modules.market_data import MarketData
import os
import datetime

db = BotDatabase()

# --- Role Management ---
@super_admin_only
async def create_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /createrole <role_name>"""
    if not context.args:
        await update.message.reply_text("Usage: /createrole <role_name>")
        return
    role_name = " ".join(context.args)
    if db.create_role(role_name):
        await update.message.reply_text(f"✅ Role '{role_name}' created.")
    else:
        await update.message.reply_text(f"❌ Failed to create role. Name might exist.")

@super_admin_only
async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roles = db.get_roles()
    text = "📋 **Roles:**\n"
    for r in roles:
        text += f"- ID: {r['id']} | {r['name']}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

# --- Package Management ---
@super_admin_only
async def create_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /createpackage <name> <price> <days> [assets]"""
    try:
        args = context.args
        if len(args) < 3:
            raise ValueError
        
        assets = "all"
        try:
            int(args[-1])
            days = int(args[-1])
            price = float(args[-2])
            name = " ".join(args[:-2])
        except ValueError:
            assets = args[-1]
            days = int(args[-2])
            price = float(args[-3])
            name = " ".join(args[:-3])
            
        db.create_package(name, price, days, assets)
        await update.message.reply_text(f"✅ Package '{name}' created.\nPrice: {price}\nDays: {days}\nAssets: {assets}")
    except ValueError:
        await update.message.reply_text("Usage: /createpackage <name> <price> <days> [assets]\nExample: /createpackage VIP Crypto 150000 30 crypto")

@super_admin_only
async def list_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pkgs = db.get_packages()
    if not pkgs:
        await update.message.reply_text("No packages found.")
        return
    text = "📦 **Packages:**\n"
    for p in pkgs:
        text += f"- ID: {p['id']} | {p['name']} | ${p['price']} | {p['duration_days']}d | ({p['assets']})\n"
    await update.message.reply_text(text, parse_mode='Markdown')

@super_admin_only
async def delete_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /delpackage <id>"""
    try:
        pkg_id = int(context.args[0])
        if db.delete_package(pkg_id):
            await update.message.reply_text(f"✅ Package {pkg_id} deleted.")
        else:
            await update.message.reply_text(f"❌ Package not found.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /delpackage <id>")

# --- Payment Method Management ---
@super_admin_only
async def add_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /addpayment <type> <name> <details>"""
    try:
        args = context.args
        if len(args) < 3:
             raise ValueError
        ptype = args[0].lower()
        name = args[1]
        details = " ".join(args[2:])
        db.add_payment_method(ptype, name, details)
        await update.message.reply_text(f"✅ Payment Method '{name}' ({ptype}) added.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addpayment <type> <name> <details>\nExample: /addpayment bank BCA 123456789 A/N Admin")

@super_admin_only
async def list_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    methods = db.get_payment_methods()
    if not methods:
        await update.message.reply_text("No payment methods configured.")
        return
    text = "💳 **Payment Methods:**\n"
    for m in methods:
        text += f"- ID: {m['id']} | [{m['type'].upper()}] {m['name']}: {m['details']}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

@super_admin_only
async def delete_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /delpayment <id>"""
    try:
        mid = int(context.args[0])
        if db.delete_payment_method(mid):
             await update.message.reply_text(f"✅ Payment method {mid} deleted.")
        else:
             await update.message.reply_text(f"❌ Payment method not found.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /delpayment <id>")

# --- Member Management ---
@super_admin_only
async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /addmember <user_id> <username> [role]"""
    try:
        user_id = int(context.args[0])
        username = context.args[1]
        role = context.args[2] if len(context.args) > 2 else "Viewer"
        if db.add_user(user_id, username, role):
             await update.message.reply_text(f"✅ User {username} added as {role}.")
        else:
             await update.message.reply_text(f"❌ User already exists.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addmember <user_id> <username> [role]")

# --- Announcement & Scheduling ---
@super_admin_only
async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /announce <message>"""
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Usage: /announce <message>")
        return
    users = db.get_all_users()
    count = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u['user_id'], text=f"📢 **Announcement:**\n\n{message}", parse_mode='Markdown')
            count += 1
        except Exception as e:
            print(f"Failed to send to {u['user_id']}: {e}")
    await update.message.reply_text(f"✅ Announcement sent to {count} users.")

@super_admin_only
async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /schedule <type> <time> <message>"""
    try:
        sch_type = context.args[0].lower()
        sch_time = context.args[1]
        message = " ".join(context.args[2:])
        if sch_type not in ['daily', 'once', 'weekly']:
            await update.message.reply_text("Type must be: daily, once, weekly")
            return
        db.add_scheduled_message(sch_type, sch_time, message)
        await update.message.reply_text(f"✅ Scheduled '{sch_type}' message at {sch_time}.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /schedule <type> <time> <message>\nExample: /schedule daily 09:00 Good Morning!")

# --- Bot Status & Control ---
@super_admin_only
async def bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /status - Check system health"""
    groups = {
        'Crypto': os.getenv("GROUP_CRYPTO"),
        'Stocks': os.getenv("GROUP_STOCKS"),
        'Forex': os.getenv("GROUP_FOREX"),
        'Gold': os.getenv("GROUP_GOLD")
    }
    jobs = context.job_queue.jobs()
    job_names = [j.name for j in jobs]
    text = (
        "🤖 **Bot Status**\n\n"
        f"✅ **System**: Online\n"
        f"🕒 **Time**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "📢 **Configured Groups**:\n"
    )
    for name, gid in groups.items():
        status = "✅ Connected" if gid else "❌ Not Configured"
        text += f"- {name}: `{gid}` ({status})\n"
    text += "\n⚙️ **Active Jobs**:\n"
    for j in job_names:
        text += f"- {j}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

@super_admin_only
async def force_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /forcecheck <signal|news>"""
    try:
        check_type = context.args[0].lower()
        groups = {
            'crypto': int(os.getenv("GROUP_CRYPTO", 0)),
            'stocks': int(os.getenv("GROUP_STOCKS", 0)),
            'forex': int(os.getenv("GROUP_FOREX", 0)),
            'gold': int(os.getenv("GROUP_GOLD", 0))
        }
        groups = {k: v for k, v in groups.items() if v != 0}
        
        class MockJob:
            data = {'groups': groups}
        context.job = MockJob()
        
        if check_type == 'signal':
            await update.message.reply_text("⏳ Forcing Signal Check... (Check Logs)")
            md = MarketData()
            sig = SignalGenerator(md)
            sig.last_signals = {} 
            await sig.check_and_send_signals(context)
            await update.message.reply_text("✅ Signal Check Complete.")
        elif check_type == 'news':
            await update.message.reply_text("⏳ Forcing News Check... (Check Logs)")
            news = NewsAggregator()
            await news.check_and_send_news(context)
            await update.message.reply_text("✅ News Check Complete.")
        else:
            await update.message.reply_text("Usage: /forcecheck <signal|news>")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /forcecheck <signal|news>")

# --- NEW: Check Uninvited ---
@super_admin_only
async def check_uninvited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /checkuninvited - Check for users who paid but didn't get links"""
    subs = db.get_uninvited_subscriptions()
    
    if not subs:
        await update.message.reply_text("✅ All active subscribers have been invited.")
        return
        
    text = "⚠️ **Uninvited Subscribers:**\n\n"
    for s in subs:
        text += (
            f"👤 **{s['username']}** (ID: `{s['user_id']}`)\n"
            f"📦 Plan: {s['package_name']} ({s['assets']})\n"
            f"📅 Status: Active, Invite: {s['invite_status']}\n"
            "-------------------\n"
        )
    
    text += "\n💡 **Action**: Please manually DM these users with invite links."
    await update.message.reply_text(text, parse_mode='Markdown')
