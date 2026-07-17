import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("elco.module.core_ta")

class CoreTAEngine:
    """
    Handles Classical TA, Candlesticks, Moving Averages, Momentum, Volume, Volatility, and Trend.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.current = df.iloc[-1]
        self.prev = df.iloc[-2]
        self.prev2 = df.iloc[-3]

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        # ==================================
        # 1. Classical / Trend Analysis (Dow Theory)
        # ==================================
        hh = self.current['high'] > self.prev['high'] and self.prev['high'] > self.df.iloc[-3]['high']
        ll = self.current['low'] < self.prev['low'] and self.prev['low'] < self.df.iloc[-3]['low']
        if hh:
            score += 0.1
            reasons.append("Dow Theory: Higher Highs detected (Trend Continuation UP).")
        elif ll:
            score -= 0.1
            reasons.append("Dow Theory: Lower Lows detected (Trend Continuation DOWN).")

        # ==================================
        # 2. Candlestick Analysis (Deep)
        # ==================================
        body = abs(self.current['close'] - self.current['open'])
        wick_up = self.current['high'] - max(self.current['close'], self.current['open'])
        wick_down = min(self.current['close'], self.current['open']) - self.current['low']
        
        # Single Candle
        if wick_down > body * 2 and wick_up < body:
            score += 0.15
            reasons.append("Candlestick (Single): Bullish Hammer / Pinbar Rejection.")
        elif wick_up > body * 2 and wick_down < body:
            score -= 0.15
            reasons.append("Candlestick (Single): Bearish Shooting Star Rejection.")
        elif body > (self.current['high'] - self.current['low']) * 0.9: # Marubozu
            if self.current['close'] > self.current['open']:
                score += 0.2
                reasons.append("Candlestick (Single): Bullish Marubozu (Strong momentum).")
            else:
                score -= 0.2
                reasons.append("Candlestick (Single): Bearish Marubozu (Strong momentum).")
        elif body < (self.current['high'] - self.current['low']) * 0.1: # Doji
            reasons.append("Candlestick (Single): Doji detected (Indecision).")

        # Double Candle
        prev_body = abs(self.prev['close'] - self.prev['open'])
        if self.prev['close'] < self.prev['open'] and self.current['close'] > self.current['open'] and self.current['close'] > self.prev['open'] and self.current['open'] < self.prev['close']:
            score += 0.2
            reasons.append("Candlestick (Double): Bullish Engulfing pattern.")
        elif self.prev['close'] > self.prev['open'] and self.current['close'] < self.current['open'] and self.current['close'] < self.prev['open'] and self.current['open'] > self.prev['close']:
            score -= 0.2
            reasons.append("Candlestick (Double): Bearish Engulfing pattern.")
        elif self.prev['close'] < self.prev['open'] and self.current['close'] > self.current['open'] and self.current['close'] < self.prev['open'] and self.current['open'] > self.prev['close']:
            score += 0.1
            reasons.append("Candlestick (Double): Bullish Harami (Inside Bar).")
            
        # Triple Candle (Morning/Evening Star)
        if self.prev2['close'] < self.prev2['open'] and prev_body < (self.prev['high'] - self.prev['low']) * 0.3 and self.current['close'] > self.current['open'] and self.current['close'] > self.prev2['close']:
            score += 0.25
            reasons.append("Candlestick (Triple): Morning Star Reversal.")

        # ==================================
        # 3. Moving Average Analysis
        # ==================================
        if len(self.df) >= 200:
            sma50 = self.df['close'].rolling(50).mean().iloc[-1]
            sma200 = self.df['close'].rolling(200).mean().iloc[-1]
            if sma50 > sma200:
                score += 0.1
                reasons.append(f"Moving Average: Golden Cross territory (50 SMA > 200 SMA).")
            else:
                score -= 0.1
                reasons.append(f"Moving Average: Death Cross territory (50 SMA < 200 SMA).")
                
            # EMA Ribbon proxy (short term alignment)
            ema9 = self.df['close'].ewm(span=9).mean().iloc[-1]
            ema21 = self.df['close'].ewm(span=21).mean().iloc[-1]
            if ema9 > ema21 > sma50:
                score += 0.1
                reasons.append("Moving Average: EMA Ribbon perfectly aligned for Bull Run.")

        # ==================================
        # 4. Momentum Analysis (RSI & MACD)
        # ==================================
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-8) # Added 1e-8 to prevent ZeroDivisionError
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        if current_rsi < 30:
            score += 0.15
            reasons.append(f"Momentum: RSI ({current_rsi:.1f}) is Oversold.")
        elif current_rsi > 70:
            score -= 0.15
            reasons.append(f"Momentum: RSI ({current_rsi:.1f}) is Overbought.")
            
        # MACD
        ema12 = self.df['close'].ewm(span=12).mean()
        ema26 = self.df['close'].ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
            score += 0.15
            reasons.append("Momentum: MACD Bullish Crossover.")
        elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
            score -= 0.15
            reasons.append("Momentum: MACD Bearish Crossover.")

        # ==================================
        # 5. Volatility Analysis (Squeeze & ATR)
        # ==================================
        std = self.df['close'].rolling(20).std().iloc[-1]
        sma20 = self.df['close'].rolling(20).mean().iloc[-1]
        bb_upper = sma20 + (std * 2)
        bb_lower = sma20 - (std * 2)
        bb_width = (bb_upper - bb_lower) / (sma20 + 1e-8) # Added 1e-8
        
        if bb_width < 0.02: # Extremely tight bands
            reasons.append("Volatility: Bollinger Squeeze detected (Big move imminent).")
        
        if self.current['close'] > bb_upper:
            score += 0.1
            reasons.append("Volatility: Price expansion above Upper Bollinger Band.")
        elif self.current['close'] < bb_lower:
            score -= 0.1
            reasons.append("Volatility: Price expansion below Lower Bollinger Band.")

        # ==================================
        # 6. Fibonacci Analysis
        # ==================================
        # Find 30-day high/low for retracement levels
        recent_high = self.df['high'].tail(30).max()
        recent_low = self.df['low'].tail(30).min()
        diff = recent_high - recent_low
        fib_618 = recent_high - (diff * 0.618)
        fib_500 = recent_high - (diff * 0.500)
        
        if abs(self.current['close'] - fib_618) / (self.current['close'] + 1e-8) < 0.005: # Added 1e-8
            score += 0.2
            reasons.append("Fibonacci: Price interacting directly with the Golden Zone (61.8% Retracement).")

        # ==================================
        # 7. Stochastic Oscillator
        # ==================================
        low14 = self.df['low'].rolling(14).min()
        high14 = self.df['high'].rolling(14).max()
        stoch_k = 100 * (self.df['close'] - low14) / (high14 - low14 + 1e-8)
        stoch_d = stoch_k.rolling(3).mean()
        curr_k = stoch_k.iloc[-1]
        curr_d = stoch_d.iloc[-1]
        
        if curr_k < 20 and curr_d < 20 and curr_k > curr_d:
            score += 0.1
            reasons.append(f"Momentum: Stochastic is Oversold and crossing UP (K:{curr_k:.1f}, D:{curr_d:.1f}).")
        elif curr_k > 80 and curr_d > 80 and curr_k < curr_d:
            score -= 0.1
            reasons.append(f"Momentum: Stochastic is Overbought and crossing DOWN (K:{curr_k:.1f}, D:{curr_d:.1f}).")

        # ==================================
        # 8. ADX (Average Directional Index Proxy)
        # ==================================
        tr1 = self.df['high'] - self.df['low']
        tr2 = abs(self.df['high'] - self.df['close'].shift(1))
        tr3 = abs(self.df['low'] - self.df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # Supertrend Proxy (using ATR)
        hl2 = (self.df['high'] + self.df['low']) / 2
        supertrend_upper = hl2 + (3 * atr)
        supertrend_lower = hl2 - (3 * atr)
        if self.current['close'] > supertrend_upper.iloc[-2]:
            score += 0.15
            reasons.append("Trend: Supertrend is BULLISH.")
        elif self.current['close'] < supertrend_lower.iloc[-2]:
            score -= 0.15
            reasons.append("Trend: Supertrend is BEARISH.")

        # ==================================
        # 9. Ichimoku Cloud Proxy
        # ==================================
        tenkan = (self.df['high'].rolling(9).max() + self.df['low'].rolling(9).min()) / 2
        kijun = (self.df['high'].rolling(26).max() + self.df['low'].rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((self.df['high'].rolling(52).max() + self.df['low'].rolling(52).min()) / 2).shift(26)
        
        curr_close = self.current['close']
        curr_sa = senkou_a.iloc[-1]
        curr_sb = senkou_b.iloc[-1]
        
        if pd.notna(curr_sa) and pd.notna(curr_sb):
            if curr_close > curr_sa and curr_close > curr_sb:
                score += 0.1
                reasons.append("Ichimoku: Price is ABOVE the Kumo Cloud (Bullish Trend).")
            elif curr_close < curr_sa and curr_close < curr_sb:
                score -= 0.1
                reasons.append("Ichimoku: Price is BELOW the Kumo Cloud (Bearish Trend).")

        # ==================================
        # 10. Pivot Points (Classic & Camarilla)
        # ==================================
        p_high, p_low, p_close = self.prev['high'], self.prev['low'], self.prev['close']
        pivot = (p_high + p_low + p_close) / 3
        r1 = (2 * pivot) - p_low
        s1 = (2 * pivot) - p_high
        
        # Camarilla H3/L3 proxy
        range_val = p_high - p_low
        h3 = p_close + (range_val * 1.1 / 4)
        l3 = p_close - (range_val * 1.1 / 4)
        
        if abs(curr_close - s1) / curr_close < 0.005:
            score += 0.1
            reasons.append("Pivots: Price is bouncing off Classic Support 1 (S1).")
        elif abs(curr_close - l3) / curr_close < 0.005:
            score += 0.1
            reasons.append("Pivots: Price is bouncing off Camarilla L3 Support.")

        return {
            "branch": "Core TA",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }

