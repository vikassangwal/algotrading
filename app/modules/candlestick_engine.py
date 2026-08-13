import pandas as pd
import numpy as np

class CandlestickEngine:
    def __init__(self, df: pd.DataFrame):
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("open", "high", "low", "close", "volume"):
                rename[col] = cl.capitalize()
        self.df = df.rename(columns=rename) if rename else df

    def analyze(self) -> list:
        if len(self.df) < 3:
            return []
        
        signals = []
        c = self._detect_candlesticks()
        if c: signals.extend(c)
        
        d = self._detect_divergence()
        if d: signals.append(d)
        
        return signals

    def _detect_candlesticks(self) -> list:
        signals = []
        current = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        body = abs(current['Close'] - current['Open'])
        upper_wick = current['High'] - max(current['Open'], current['Close'])
        lower_wick = min(current['Open'], current['Close']) - current['Low']
        total_range = current['High'] - current['Low']
        
        if total_range == 0:
            return signals

        # Doji
        if body <= total_range * 0.1:
            signals.append("Doji Detected (Indecision)")
            
        # Hammer / Pin Bar
        if lower_wick >= body * 2 and upper_wick <= body * 0.5:
            signals.append("Bullish Hammer Detected (Reversal Signal)")
            
        # Shooting Star
        if upper_wick >= body * 2 and lower_wick <= body * 0.5:
            signals.append("Bearish Shooting Star Detected (Reversal Signal)")
            
        # Bullish Engulfing
        if prev['Close'] < prev['Open'] and current['Close'] > current['Open']:
            if current['Open'] <= prev['Close'] and current['Close'] >= prev['Open']:
                signals.append("Bullish Engulfing Pattern")
                
        # Bearish Engulfing
        if prev['Close'] > prev['Open'] and current['Close'] < current['Open']:
            if current['Open'] >= prev['Close'] and current['Close'] <= prev['Open']:
                signals.append("Bearish Engulfing Pattern")
                
        return signals

    def _detect_divergence(self) -> str:
        """Detects Price vs RSI Divergence."""
        if len(self.df) < 20:
            return None
            
        close = self.df['Close']
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Look at last 15 days vs current
        recent_price_high = close.iloc[-15:-5].max()
        recent_price_low = close.iloc[-15:-5].min()
        recent_rsi_high = rsi.iloc[-15:-5].max()
        recent_rsi_low = rsi.iloc[-15:-5].min()
        
        curr_price = close.iloc[-1]
        curr_rsi = rsi.iloc[-1]
        
        if curr_price > recent_price_high and curr_rsi < recent_rsi_high:
            return "Bearish Divergence (Price making Higher High, RSI making Lower High)"
            
        if curr_price < recent_price_low and curr_rsi > recent_rsi_low:
            return "Bullish Divergence (Price making Lower Low, RSI making Higher Low)"
            
        return None
