import logging
import datetime
from .market_data import MarketData
from .technical_analysis import TechnicalAnalysis

logger = logging.getLogger(__name__)

class SignalGenerator:
    def __init__(self, market_data: MarketData):
        self.market = market_data
        self.last_signals = {} # Cache to prevent duplicates: {symbol: timestamp}
        self.cooldown_minutes = 60 # Don't send same signal for 1 hour
        
        # Free Group Logic
        self.last_free_signal_time = None
        self.free_group_cooldown_hours = 4 # Only 1 signal every 4 hours for free group
        
        # Define Assets and their Category
        self.assets = {
            'crypto': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'],
            'stocks': ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN'],
            'forex': ['EURUSD=X', 'GBPUSD=X', 'JPY=X', 'AUDUSD=X'],
            'gold': ['GC=F', 'SI=F'] # Gold, Silver
        }

    async def check_and_send_signals(self, context):
        """
        Main job function.
        Context job data: {'groups': {'crypto': 123, ...}, 'free_group': 999}
        """
        group_config = context.job.data.get('groups', {})
        free_group_id = context.job.data.get('free_group')
        timeframe = '15m'

        # Iterate through categories (crypto, stocks, etc.)
        for category, symbols in self.assets.items():
            target_group_id = group_config.get(category)
            
            # Note: Even if target_group_id is missing, we might want to send to Free Group?
            # But usually we need the premium group to exist to be "fair".
            # We proceed if either exists.
            
            for symbol in symbols:
                try:
                    # 1. Fetch Data
                    df = self.market.fetch_ohlcv(symbol, timeframe)
                    if df.empty:
                        continue

                    # 2. Analyze
                    df = TechnicalAnalysis.calculate_indicators(df)
                    latest = df.iloc[-1]
                    
                    # 3. Check Conditions (BUY Logic)
                    is_buy_signal = (
                        latest['close'] > latest['SMA_200'] and 
                        latest['RSI'] < 30
                    )
                    
                    if is_buy_signal:
                        # Check Duplicate (Global cooldown for symbol)
                        last_time = self.last_signals.get(symbol)
                        if last_time and (datetime.datetime.now() - last_time).seconds < self.cooldown_minutes * 60:
                            continue
                            
                        # Update Cache
                        self.last_signals[symbol] = datetime.datetime.now()
                        logger.info(f"Signal generated for {symbol}")
                        
                        # --- SEND TO PREMIUM GROUP ---
                        if target_group_id:
                            premium_msg = self.format_signal_message(symbol, latest, timeframe, category, is_free=False)
                            await context.bot.send_message(chat_id=target_group_id, text=premium_msg)
                            
                        # --- SEND TO FREE GROUP (Rate Limited) ---
                        if free_group_id:
                            now = datetime.datetime.now()
                            # Check if enough time passed since last FREE signal
                            if (self.last_free_signal_time is None) or \
                               ((now - self.last_free_signal_time).seconds > self.free_group_cooldown_hours * 3600):
                                
                                free_msg = self.format_signal_message(symbol, latest, timeframe, category, is_free=True)
                                await context.bot.send_message(chat_id=free_group_id, text=free_msg)
                                
                                self.last_free_signal_time = now
                                logger.info(f"Signal sent to FREE GROUP for {symbol}")

                except Exception as e:
                    logger.error(f"Error processing signal for {symbol}: {e}")

    def format_signal_message(self, symbol, row, timeframe, category, is_free=False):
        price = row['close']
        atr = row['ATR'] if 'ATR' in row else price * 0.01
        
        # Calculate dynamic levels
        entry = price
        stop_loss = price - (atr * 2) 
        tp1 = price + (atr * 2)
        tp2 = price + (atr * 3)
        tp3 = price + (atr * 5)
        
        # Trend Analysis
        trend = TechnicalAnalysis.analyze_trend(row)
        rsi_val = int(row['RSI'])
        volatility = TechnicalAnalysis.analyze_volatility(row)
        
        # Clean Symbol
        display_symbol = symbol.replace('=X', '').replace('=F', '').replace('/', '')
        
        # Category Icon
        icons = {'crypto': '₿', 'stocks': '🏢', 'forex': '💱', 'gold': '🥇'}
        icon = icons.get(category, '📊')

        msg = (
            f"{icon} {display_symbol} – {timeframe.upper()}\n"
            f"🟢 BUY SIGNAL\n\n"
            f"Entry : {entry:,.2f}\n"
            f"Stop  : {stop_loss:,.2f}\n\n"
            f"TP1   : {tp1:,.2f}\n"
            f"TP2   : {tp2:,.2f}\n"
            f"TP3   : {tp3:,.2f}\n\n"
            f"Trend      : {trend}\n"
            f"RSI        : {rsi_val} (Pullback)\n"
            f"Volatility : {volatility}"
        )
        
        if is_free:
            msg += (
                "\n\n------------------------\n"
                "🔒 **Free Channel Limit**\n"
                "Get ALL signals in Real-Time!\n"
                "👉 /subscribe to join Premium!"
            )
            
        return msg
