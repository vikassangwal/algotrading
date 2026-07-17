import pandas as pd
import numpy as np

class VolumeScanner:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def scan(self, volume_threshold: float = 1.5, window: int = 20) -> pd.DataFrame:
        """
        Scans for volume breakouts.
        Returns a DataFrame of symbols/rows where the current volume is greater than 
        `volume_threshold` times the moving average volume over `window` periods.
        """
        if 'volume' not in self.data.columns:
            raise ValueError("DataFrame must contain a 'volume' column.")
            
        self.data['vol_ma'] = self.data['volume'].rolling(window=window).mean()
        self.data['vol_breakout'] = self.data['volume'] > (self.data['vol_ma'] * volume_threshold)
        
        return self.data[self.data['vol_breakout'] == True]

class DeliveryScanner:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def scan(self, delivery_pct_threshold: float = 50.0, delivery_vol_threshold: float = 1.5, window: int = 5) -> pd.DataFrame:
        """
        Scans for delivery volume anomalies.
        Returns a DataFrame of symbols/rows where the delivery percentage is high and
        the delivery volume is greater than `delivery_vol_threshold` times the recent average.
        """
        required_cols = ['delivery_volume', 'delivery_percentage']
        if not all(col in self.data.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain {required_cols} columns.")
            
        self.data['deliv_vol_ma'] = self.data['delivery_volume'].rolling(window=window).mean()
        
        condition1 = self.data['delivery_percentage'] > delivery_pct_threshold
        condition2 = self.data['delivery_volume'] > (self.data['deliv_vol_ma'] * delivery_vol_threshold)
        
        self.data['deliv_breakout'] = condition1 & condition2
        
        return self.data[self.data['deliv_breakout'] == True]

class MomentumScanner:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def scan_rsi(self, window: int = 14, overbought: float = 70, oversold: float = 30) -> dict:
        """
        Scans for RSI overbought/oversold conditions.
        """
        if 'close' not in self.data.columns:
            raise ValueError("DataFrame must contain a 'close' column.")
            
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        self.data['rsi'] = 100 - (100 / (1 + rs))
        
        return {
            'overbought': self.data[self.data['rsi'] >= overbought],
            'oversold': self.data[self.data['rsi'] <= oversold]
        }
        
    def scan_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        Scans for MACD crossovers.
        """
        if 'close' not in self.data.columns:
            raise ValueError("DataFrame must contain a 'close' column.")
            
        exp1 = self.data['close'].ewm(span=fast, adjust=False).mean()
        exp2 = self.data['close'].ewm(span=slow, adjust=False).mean()
        
        self.data['macd'] = exp1 - exp2
        self.data['signal_line'] = self.data['macd'].ewm(span=signal, adjust=False).mean()
        
        # Bullish crossover: MACD crosses above signal line
        self.data['crossover'] = (self.data['macd'] > self.data['signal_line']) & (self.data['macd'].shift(1) <= self.data['signal_line'].shift(1))
        
        return self.data[self.data['crossover'] == True]
