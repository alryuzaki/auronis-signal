import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import BotDatabase

db = BotDatabase()

# Stages
NOTIF_MSG, NOTIF_TARGET, NOTIF_FREQ, NOTIF_TIME = range(4)

async def add_notif_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /addnotif"""
    await update.message.reply_text(
        "🔔 **Create Custom Notification**\n\n"
        "Please enter the **message content** (Text/HTML supported).\n"
        "Example: `<b>Daily Market Update</b>\nEverything is bullish!`",
        parse_mode='Markdown'
    )
    return NOTIF_MSG

async def notif_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['notif_msg'] = update.message.text
    
    # Select Targets
    keyboard = [
        [InlineKeyboardButton("₿ Crypto", callback_data='target_crypto'),
         InlineKeyboardButton("📈 Stocks", callback_data='target_stocks')],
        [InlineKeyboardButton("💱 Forex", callback_data='target_forex'),
         InlineKeyboardButton("🥇 Gold", callback_data='target_gold')],
        [InlineKeyboardButton("🔓 Free Group", callback_data='target_free'),
         InlineKeyboardButton("🌐 ALL GROUPS", callback_data='target_all')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Message saved.\n\nSelect **Target Group**:",
        reply_markup=reply_markup
    )
    return NOTIF_TARGET

async def notif_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    target = query.data.split('_')[1]
    context.user_data['notif_target'] = target
    
    # Select Frequency
    keyboard = [
        [InlineKeyboardButton("Hourly", callback_data='freq_hourly'),
         InlineKeyboardButton("Daily", callback_data='freq_daily')],
        [InlineKeyboardButton("Weekly", callback_data='freq_weekly'),
         InlineKeyboardButton("Monthly", callback_data='freq_monthly')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Target: **{target.upper()}**\n\nSelect **Frequency**:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return NOTIF_FREQ

async def notif_freq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    freq = query.data.split('_')[1]
    context.user_data['notif_freq'] = freq
    
    instruction = ""
    if freq == 'hourly':
        instruction = "Enter the **Minute** mark (0-59).\nExample: `30` (sends at 10:30, 11:30...)"
    elif freq == 'daily':
        instruction = "Enter **Time** (HH:MM) in 24h format.\nExample: `09:00`"
    elif freq == 'weekly':
        instruction = "Enter **DayName HH:MM**.\nExample: `Monday 09:00`"
    elif freq == 'monthly':
        instruction = "Enter **DayNumber HH:MM**.\nExample: `1 09:00` (1st of month)"
        
    await query.edit_message_text(
        f"✅ Frequency: **{freq.upper()}**\n\n{instruction}",
        parse_mode='Markdown'
    )
    return NOTIF_TIME

async def notif_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_str = update.message.text
    # Basic validation could be added here
    context.user_data['notif_time'] = time_str
    
    data = context.user_data
    
    # Save to DB
    db.add_custom_notification(
        data['notif_msg'],
        data['notif_target'],
        data['notif_freq'],
        data['notif_time']
    )
    
    await update.message.reply_text(
        f"✅ **Notification Created!**\n\n"
        f"Msg: {data['notif_msg'][:20]}...\n"
        f"Target: {data['notif_target']}\n"
        f"Freq: {data['notif_freq']} @ {data['notif_time']}",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Notification creation cancelled.")
    return ConversationHandler.END

# Handler Object
notif_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('addnotif', add_notif_start)],
    states={
        NOTIF_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, notif_msg)],
        NOTIF_TARGET: [CallbackQueryHandler(notif_target, pattern='^target_')],
        NOTIF_FREQ: [CallbackQueryHandler(notif_freq, pattern='^freq_')],
        NOTIF_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, notif_time)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

async def list_notifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notifs = db.get_custom_notifications()
    if not notifs:
        await update.message.reply_text("No custom notifications active.")
        return
        
    text = "🔔 **Active Notifications:**\n\n"
    for n in notifs:
        text += (
            f"🆔 **{n['id']}** | {n['frequency'].title()} @ {n['schedule_time']}\n"
            f"🎯 {n['target_groups']}\n"
            f"📝 {n['message'][:30]}...\n"
            "-------------------\n"
        )
    await update.message.reply_text(text, parse_mode='Markdown')

async def del_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nid = int(context.args[0])
        if db.delete_custom_notification(nid):
            await update.message.reply_text(f"✅ Notification {nid} deleted.")
        else:
            await update.message.reply_text("❌ Notification not found.")
    except:
        await update.message.reply_text("Usage: /delnotif <id>")

# --- SCHEDULER LOGIC ---

async def notification_scheduler(context):
    """Checks and sends custom notifications"""
    notifs = db.get_custom_notifications()
    now = datetime.datetime.now()
    
    # Load Groups
    groups = context.job.data.get('groups', {})
    free_group = context.job.data.get('free_group')
    
    all_groups = {}
    if groups: all_groups.update(groups)
    if free_group: all_groups['free'] = free_group
    
    for n in notifs:
        should_send = False
        freq = n['frequency']
        sched = n['schedule_time']
        
        try:
            if freq == 'hourly':
                # sched is "30" (minute)
                if now.minute == int(sched):
                    should_send = True
                    
            elif freq == 'daily':
                # sched is "09:00"
                if now.strftime("%H:%M") == sched:
                    should_send = True
                    
            elif freq == 'weekly':
                # sched is "Monday 09:00"
                day, time = sched.split(' ')
                if now.strftime("%A").lower() == day.lower() and now.strftime("%H:%M") == time:
                    should_send = True
                    
            elif freq == 'monthly':
                # sched is "1 09:00"
                day, time = sched.split(' ')
                if now.day == int(day) and now.strftime("%H:%M") == time:
                    should_send = True
            
            # Prevent double sending in same minute if job runs multiple times?
            # Job runs every 60s. Last sent check.
            last_sent = n['last_sent']
            if should_send:
                # Basic debounce: if sent within last 65 seconds, skip
                if last_sent:
                    # Parse from DB string if needed, usually sqlite returns string for timestamp
                    # Assuming db returns string "YYYY-MM-DD HH:MM:SS" or datetime obj
                    if isinstance(last_sent, str):
                        last_sent = datetime.datetime.fromisoformat(last_sent)
                    
                    if (now - last_sent).seconds < 70:
                        continue # Already sent this minute
                
                # SEND
                targets = []
                t_str = n['target_groups']
                if t_str == 'all':
                    targets = list(all_groups.values())
                else:
                    keys = t_str.split(',')
                    for k in keys:
                        gid = all_groups.get(k)
                        if gid: targets.append(gid)
                
                # Dedup targets
                targets = list(set(targets))
                
                for gid in targets:
                    await context.bot.send_message(chat_id=gid, text=n['message'], parse_mode='HTML')
                
                db.update_last_sent(n['id'])
                
        except Exception as e:
            print(f"Error processing notif {n['id']}: {e}")
