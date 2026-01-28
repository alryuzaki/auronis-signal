import asyncio
import os
import datetime
from dotenv import load_dotenv
from telegram import Bot
from database import BotDatabase

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Get specific groups (Crypto, Stocks, etc.) to kick users from ALL of them
GROUP_CRYPTO = os.getenv("GROUP_CRYPTO")
GROUP_STOCKS = os.getenv("GROUP_STOCKS")
GROUP_FOREX = os.getenv("GROUP_FOREX")
GROUP_GOLD = os.getenv("GROUP_GOLD")

db = BotDatabase()

async def send_reminders(bot: Bot):
    print("Checking for reminders...")
    # Get users expiring in 3 days
    users = db.check_expiring_soon(days=3)
    for u in users:
        try:
            msg = (
                f"⚠️ **Subscription Reminder**\n"
                f"Hi {u['username']}, your subscription will expire in 3 days.\n"
                f"Please renew to avoid losing access."
            )
            await bot.send_message(chat_id=u['user_id'], text=msg, parse_mode='Markdown')
            print(f"Sent reminder to {u['username']}")
        except Exception as e:
            print(f"Failed to send reminder to {u['user_id']}: {e}")

async def process_expirations(bot: Bot):
    print("Checking for expirations...")
    expired_subs = db.check_expired()
    
    # Collect all managed groups
    all_groups = []
    if GROUP_CRYPTO: all_groups.append(GROUP_CRYPTO)
    if GROUP_STOCKS: all_groups.append(GROUP_STOCKS)
    if GROUP_FOREX: all_groups.append(GROUP_FOREX)
    if GROUP_GOLD: all_groups.append(GROUP_GOLD)
    
    # Filter valid IDs
    all_groups = [g for g in all_groups if g]

    for sub in expired_subs:
        user_id = sub['user_id']
        username = sub['username']
        
        # 1. Kick from ALL groups (Brute force safety: remove from all potential groups)
        # Ideally, we check sub['package_id'] -> get assets -> get specific groups.
        # But for expiration, it's safer to just remove from all managed groups to be sure.
        
        if all_groups:
            for group_id in all_groups:
                try:
                    await bot.ban_chat_member(chat_id=group_id, user_id=user_id)
                    await bot.unban_chat_member(chat_id=group_id, user_id=user_id) # Unban to allow re-join later
                    print(f"Kicked {username} from {group_id}")
                except Exception as e:
                    # Often fails if user is not in that group, which is fine
                    # print(f"Failed to kick {username} from {group_id}: {e}")
                    pass
        
        # 2. Update DB status
        db.expire_subscription(sub['id'])
        
        # 3. Notify user
        try:
            await bot.send_message(
                chat_id=user_id, 
                text="❌ Your subscription has expired. You have been removed from the premium groups."
            )
        except Exception as e:
            print(f"Failed to notify {user_id} of expiration: {e}")

async def main():
    if not TOKEN:
        print("Bot token not found.")
        return
        
    bot = Bot(token=TOKEN)
    
    await send_reminders(bot)
    await process_expirations(bot)

if __name__ == "__main__":
    asyncio.run(main())
