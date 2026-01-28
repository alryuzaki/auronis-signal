import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volatility import AverageTrueRange

class TechnicalAnalysis:
    @staticmethod
    def calculate_indicators(df: pd.DataFrame):
        """
        Calculate RSI and MA indicators using 'ta' library.
        Adds 'RSI', 'SMA_200', 'ATR' columns to the DataFrame.
        """
        if df.empty:
            return df
        
        # Ensure Close is float
        close_prices = df['close'].astype(float)
        high_prices = df['high'].astype(float)
        low_prices = df['low'].astype(float)

        # Calculate RSI (14)
        rsi_indicator = RSIIndicator(close=close_prices, window=14)
        df['RSI'] = rsi_indicator.rsi()
        
        # Calculate SMA (200) for trend
        sma_indicator = SMAIndicator(close=close_prices, window=200)
        df['SMA_200'] = sma_indicator.sma_indicator()
        
        # Calculate ATR (14) for volatility/stops
        atr_indicator = AverageTrueRange(high=high_prices, low=low_prices, close=close_prices, window=14)
        df['ATR'] = atr_indicator.average_true_range()
        
        return df

    @staticmethod
    def analyze_trend(row):
        if pd.isna(row['SMA_200']):
            return "Neutral"
        return "Bullish" if row['close'] > row['SMA_200'] else "Bearish"

    @staticmethod
    def analyze_volatility(row):
        # Simple heuristic
        return "Normal"
