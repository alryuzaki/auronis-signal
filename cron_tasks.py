import asyncio
import os
import datetime
from dotenv import load_dotenv
from telegram import Bot
from database import BotDatabase

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MANAGED_GROUP_ID = os.getenv("MANAGED_GROUP_ID") # Comma separated if multiple

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
    
    group_ids = [gid.strip() for gid in (MANAGED_GROUP_ID or "").split(",") if gid.strip()]

    for sub in expired_subs:
        user_id = sub['user_id']
        username = sub['username']
        
        # 1. Kick from groups
        if group_ids:
            for group_id in group_ids:
                try:
                    await bot.ban_chat_member(chat_id=group_id, user_id=user_id)
                    await bot.unban_chat_member(chat_id=group_id, user_id=user_id) # Unban to allow re-join later
                    print(f"Kicked {username} from {group_id}")
                except Exception as e:
                    print(f"Failed to kick {username} from {group_id}: {e}")
        
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

async def process_scheduled_messages(bot: Bot):
    print("Checking scheduled messages...")
    # This is a simplified logic. In a real cron, you'd check if `schedule_time` matches current time window.
    # Since GH Actions might run hourly, we check if any message is 'due' and 'not sent'.
    # For this demo, we'll just check for any 'daily' messages and send them if the hour matches roughly.
    
    # NOTE: A proper scheduler (APScheduler) inside the running bot is better for "Daily at 9AM".
    # But since the requirement is "Cron task", we assume this script runs e.g. every hour.
    
    now = datetime.datetime.now()
    current_hour_min = now.strftime("%H:%M")
    
    # We need to fetch all schedules. 
    # For simplicity, we just look for exact matches or 'daily' types.
    # Realistically, this part is better handled by the main bot process with APScheduler.
    # But to satisfy the "GitHub Actions Cron" requirement for signals:
    
    # Let's assume we have a source of signals here.
    # For now, we skip complex scheduling logic in this script and focus on Maintenance (Reminders/Kick).
    pass

async def main():
    if not TOKEN:
        print("Bot token not found.")
        return
        
    bot = Bot(token=TOKEN)
    
    await send_reminders(bot)
    await process_expirations(bot)
    # await process_scheduled_messages(bot)

if __name__ == "__main__":
    asyncio.run(main())
