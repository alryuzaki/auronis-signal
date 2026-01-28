import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import BotDatabase
import datetime

db = BotDatabase()

# Stages
SELECT_ASSET, SELECT_DURATION, SHOW_PAYMENT, UPLOAD_PROOF = range(4)

# Admin ID for notifications
ADMIN_ID = int(os.getenv("ADMIN_USER_ID", 0))

async def subscribe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /subscribe"""
    # 1. Ask for Asset Type
    keyboard = [
        [InlineKeyboardButton("₿ Crypto", callback_data='asset_crypto'),
         InlineKeyboardButton("📈 Stocks", callback_data='asset_stocks')],
        [InlineKeyboardButton("💱 Forex", callback_data='asset_forex'),
         InlineKeyboardButton("🥇 Gold", callback_data='asset_gold')],
        [InlineKeyboardButton("🌐 All In One", callback_data='asset_all')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💎 **New Subscription**\n\nPlease select the asset class you want to subscribe to:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return SELECT_ASSET

async def select_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    asset_type = query.data.split('_')[1] # crypto, stocks, etc.
    context.user_data['sub_asset'] = asset_type
    
    # 2. Ask for Duration
    keyboard = [
        [InlineKeyboardButton("📅 1 Week", callback_data='duration_7'),
         InlineKeyboardButton("🗓 1 Month", callback_data='duration_30')],
        [InlineKeyboardButton("📆 6 Months", callback_data='duration_180'),
         InlineKeyboardButton("📅 1 Year", callback_data='duration_365')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Selected: **{asset_type.upper()}**\n\nNow select the duration:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return SELECT_DURATION

async def select_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    duration = int(query.data.split('_')[1])
    context.user_data['sub_duration'] = duration
    asset = context.user_data['sub_asset']
    
    # Calculate Price
    base_prices = {
        'crypto': 100000, 'stocks': 100000, 'forex': 80000, 'gold': 80000, 'all': 250000
    }
    multipliers = {
        7: 0.3, 30: 1.0, 180: 5.5, 365: 10.0 # Discount for longer terms
    }
    
    base = base_prices.get(asset, 100000)
    mult = multipliers.get(duration, 1.0)
    final_price = base * mult
    context.user_data['sub_price'] = final_price
    
    # 3. Fetch Payment Methods from DB
    methods = db.get_payment_methods()
    
    payment_text = ""
    if methods:
        payment_text = "💳 **Payment Methods:**\n"
        for i, m in enumerate(methods, 1):
            payment_text += f"{i}. [{m['type'].upper()}] **{m['name']}**: {m['details']}\n"
    else:
        payment_text = "⚠️ No payment methods available. Contact Admin."

    msg = (
        f"📝 **Subscription Summary**\n"
        f"• Plan: {asset.upper()}\n"
        f"• Duration: {duration} Days\n"
        f"• Price: **Rp {final_price:,.0f}**\n\n"
        f"{payment_text}\n"
        "**Instructions:**\n"
        "Please transfer the exact amount and reply with your **Transfer Receipt** (Image/Photo)."
    )
    
    await query.edit_message_text(msg, parse_mode='Markdown')
    
    return UPLOAD_PROOF

async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Please upload an image as proof.")
        return UPLOAD_PROOF
        
    photo = update.message.photo[-1] # Best quality
    file_id = photo.file_id
    
    user = update.effective_user
    data = context.user_data
    
    # Find or Create Package for Tracking
    pkg_name = f"Custom {data['sub_asset'].title()} {data['sub_duration']}d"
    
    # Optimization: Check if package exists first
    packages = db.get_packages()
    target_pkg = None
    for p in packages:
        if p['name'] == pkg_name and p['price'] == data['sub_price']:
            target_pkg = p
            break
            
    if target_pkg:
        pkg_id = target_pkg['id']
    else:
        db.create_package(pkg_name, data['sub_price'], data['sub_duration'], assets=data['sub_asset'])
        pkgs = db.get_packages()
        pkg_id = pkgs[-1]['id']
    
    tx_id = db.create_transaction(user.id, pkg_id, data['sub_price'], file_id)
    
    await update.message.reply_text("✅ **Receipt Received!**\nWaiting for Admin confirmation...")
    
    # Notify Admin
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"tx_confirm_{tx_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"tx_reject_{tx_id}")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    
    admin_msg = (
        f"🔔 **New Subscription Request**\n\n"
        f"User: {user.full_name} (@{user.username})\n"
        f"Plan: {pkg_name}\n"
        f"Amount: Rp {data['sub_price']:,.0f}\n"
        f"Tx ID: {tx_id}"
    )
    
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=admin_msg, reply_markup=markup)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Subscription process cancelled.")
    return ConversationHandler.END

# Helper to generate Invite Link
async def generate_invite_link(bot, group_id, user_id, duration_days):
    try:
        # Create a unique invite link for this user
        expire = datetime.datetime.now() + datetime.timedelta(days=1) # Link valid for 1 day
        link = await bot.create_chat_invite_link(
            chat_id=group_id, 
            name=f"Sub {user_id}",
            member_limit=1,
            expire_date=expire
        )
        return link.invite_link
    except Exception as e:
        print(f"Error generating invite link: {e}")
        return None

# Admin Callback for Transactions
async def admin_tx_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, tx_id = query.data.split('_')[1], int(query.data.split('_')[2])
    
    tx = db.get_transaction(tx_id)
    if not tx:
        await query.edit_message_caption("❌ Transaction not found.")
        return
        
    user_id = tx['user_id']
    pkg_id = tx['package_id']
    assets = tx['assets'] # 'crypto', 'stocks', or 'all'
    
    if action == 'confirm':
        db.update_transaction_status(tx_id, 'confirmed')
        db.add_subscription(user_id, pkg_id)
        
        # --- AUTO INVITE LOGIC ---
        groups = {
            'crypto': os.getenv("GROUP_CRYPTO"),
            'stocks': os.getenv("GROUP_STOCKS"),
            'forex': os.getenv("GROUP_FOREX"),
            'gold': os.getenv("GROUP_GOLD")
        }
        
        links = []
        failed_groups = []
        
        target_assets = []
        if assets == 'all':
            target_assets = ['crypto', 'stocks', 'forex', 'gold']
        else:
            target_assets = [assets]
            
        for asset in target_assets:
            gid = groups.get(asset)
            if gid:
                link = await generate_invite_link(context.bot, gid, user_id, tx['duration_days'])
                if link:
                    links.append(f"- {asset.upper()}: {link}")
                else:
                    failed_groups.append(asset)
        
        invite_msg = ""
        if links:
            invite_msg = "\n\n🔗 **Join Links:**\n" + "\n".join(links)
            # Update invite status in DB (Implementation detail: we should get the sub_id to update)
            # For now, simplistic update:
            # db.update_invite_status_by_user(user_id, 'sent') 
        
        if failed_groups:
             invite_msg += f"\n\n⚠️ Failed to generate links for: {', '.join(failed_groups)}. Admin will contact you."
        
        # Notify User
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"🎉 **Payment Accepted!**\nYour subscription is now active.{invite_msg}"
        )
        
        # Update Admin
        admin_note = "\n\n✅ **CONFIRMED**"
        if failed_groups:
            admin_note += f"\n⚠️ **Warning**: Invite link failed for {failed_groups}. Check /checkuninvited."
            
        await query.edit_message_caption(f"{query.message.caption}{admin_note}")
        
    elif action == 'reject':
        db.update_transaction_status(tx_id, 'rejected')
        await query.edit_message_caption(f"{query.message.caption}\n\n❌ **REJECTED**")
        await context.bot.send_message(chat_id=user_id, text="⚠️ **Payment Rejected.**\nPlease contact admin for more info.")

# Handler Object
sub_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('subscribe', subscribe_start)],
    states={
        SELECT_ASSET: [CallbackQueryHandler(select_asset, pattern='^asset_')],
        SELECT_DURATION: [CallbackQueryHandler(select_duration, pattern='^duration_')],
        UPLOAD_PROOF: [MessageHandler(filters.PHOTO, handle_proof)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
