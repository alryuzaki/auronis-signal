import ccxt
import pandas as pd
import logging
import yfinance as yf

logger = logging.getLogger(__name__)

class MarketData:
    def __init__(self, exchange_id='binance'):
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
        })
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '15m', limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV data from exchange (Crypto) or Yahoo Finance (Stocks/Forex/Gold).
        """
        try:
            # Check if symbol is Crypto (contains '/')
            if '/' in symbol:
                return self._fetch_crypto(symbol, timeframe, limit)
            else:
                return self._fetch_yahoo(symbol, timeframe, limit)
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def _fetch_crypto(self, symbol, timeframe, limit):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def _fetch_yahoo(self, symbol, timeframe, limit):
        # Map timeframe: 15m -> 15m, 1h -> 1h, 1d -> 1d
        # yfinance supports: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        period = "5d" # Default period
        if timeframe == '1d': period = "1y"
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=timeframe)
        
        if df.empty:
            return pd.DataFrame()
            
        # Reset index to get timestamp column
        df = df.reset_index()
        
        # Normalize columns
        df = df.rename(columns={
            'Date': 'timestamp', 
            'Datetime': 'timestamp',
            'Open': 'open', 
            'High': 'high', 
            'Low': 'low', 
            'Close': 'close', 
            'Volume': 'volume'
        })
        
        # Ensure lowercase columns
        df.columns = [c.lower() for c in df.columns]
        
        # Remove timezone if present to match CCXT
        if 'timestamp' in df.columns and df['timestamp'].dt.tz is not None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(None)
            
        return df.tail(limit)

    def get_current_price(self, symbol: str) -> float:
        try:
            if '/' in symbol:
                ticker = self.exchange.fetch_ticker(symbol)
                return ticker['last']
            else:
                ticker = yf.Ticker(symbol)
                # fast info or history
                return ticker.fast_info.last_price
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return 0.0
