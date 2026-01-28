import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, TypeHandler
from telegram import Update # Required for TypeHandler

from modules.user_handlers import start, help_command, my_profile
from modules.admin_handlers import (
    create_role, list_roles, 
    create_package, list_packages, delete_package,
    add_payment_method, list_payment_methods, delete_payment_method,
    add_member, announce, schedule_message,
    bot_status, force_check, check_uninvited
)
from modules.payment_handlers import sub_conv_handler, admin_tx_callback
from modules.notification_handlers import notif_conv_handler, list_notifs, del_notif, notification_scheduler
# NEW: Settings Handlers
from modules.settings_handlers import settings_menu, settings_callback, maintenance_check

from modules.market_data import MarketData
from modules.signals import SignalGenerator
from modules.news import NewsAggregator

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Load separate groups
    groups = {
        'crypto': os.getenv("GROUP_CRYPTO"),
        'stocks': os.getenv("GROUP_STOCKS"),
        'forex': os.getenv("GROUP_FOREX"),
        'gold': os.getenv("GROUP_GOLD")
    }
    groups = {k: int(v) for k, v in groups.items() if v}
    
    # Load Free Group
    free_group_env = os.getenv("GROUP_FREE")
    free_group_id = int(free_group_env) if free_group_env else None
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env")
        return

    # Create the Application
    application = Application.builder().token(token).build()

    # --- MIDDLEWARE (Maintenance Check) ---
    # Register this FIRST so it runs before other handlers
    # TypeHandler(Update, ...) captures all updates
    application.add_handler(TypeHandler(Update, maintenance_check), group=-1)

    # User Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myprofile", my_profile))
    
    # Payment / Subscription Flow
    application.add_handler(sub_conv_handler)
    application.add_handler(CallbackQueryHandler(admin_tx_callback, pattern='^tx_'))

    # Admin Handlers
    application.add_handler(CommandHandler("createrole", create_role))
    application.add_handler(CommandHandler("listroles", list_roles))
    
    # Package Management
    application.add_handler(CommandHandler("createpackage", create_package))
    application.add_handler(CommandHandler("adminlistpackages", list_packages)) 
    application.add_handler(CommandHandler("delpackage", delete_package))
    
    # Payment Method Management
    application.add_handler(CommandHandler("addpayment", add_payment_method))
    application.add_handler(CommandHandler("listpayments", list_payment_methods))
    application.add_handler(CommandHandler("delpayment", delete_payment_method))
    
    application.add_handler(CommandHandler("addmember", add_member))
    application.add_handler(CommandHandler("announce", announce))
    application.add_handler(CommandHandler("schedule", schedule_message))
    
    # Control Handlers
    application.add_handler(CommandHandler("status", bot_status))
    application.add_handler(CommandHandler("forcecheck", force_check))
    application.add_handler(CommandHandler("checkuninvited", check_uninvited))

    # Notification Handlers
    application.add_handler(notif_conv_handler)
    application.add_handler(CommandHandler("listnotifs", list_notifs))
    application.add_handler(CommandHandler("delnotif", del_notif))
    
    # NEW: Settings Handlers
    application.add_handler(CommandHandler("settings", settings_menu))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern='^(toggle_maintenance|refresh_settings)$'))

    # --- Schedulers ---
    job_queue = application.job_queue

    # Config Logging
    if groups:
        logger.info(f"Configured Premium Groups: {groups}")
    if free_group_id:
        logger.info(f"Configured Free Group: {free_group_id}")

    if groups or free_group_id:
        # 1. Signals Job (Every 15 mins)
        market_data = MarketData()
        signal_gen = SignalGenerator(market_data)
        
        job_queue.run_repeating(
            signal_gen.check_and_send_signals, 
            interval=900, 
            first=10, 
            data={
                'groups': groups, 
                'free_group': free_group_id
            },
            name="signal_check"
        )
        
        # 2. News Job (Every 1 hour = 3600s)
        news_agg = NewsAggregator()
        
        job_queue.run_repeating(
            news_agg.check_and_send_news,
            interval=3600,
            first=60, 
            data={'groups': groups},
            name="news_check"
        )
        
        # 3. Custom Notification Job (Every 60s)
        job_queue.run_repeating(
            notification_scheduler,
            interval=60, # Check every minute
            first=5,
            data={
                'groups': groups, 
                'free_group': free_group_id
            },
            name="custom_notif_check"
        )
        
        logger.info("Schedulers active: Signal, News, CustomNotif.")
    else:
        logger.warning("No GROUP IDs defined in .env. Auto signals/news disabled.")

    # Run the bot
    logger.info("Bot started...")
    application.run_polling()

if __name__ == "__main__":
    main()
