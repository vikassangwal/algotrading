import pandas as pd
import numpy as np

class ICTEngine:
    """
    Inner Circle Trader (ICT) / Smart Money Concepts (SMC) Engine.
    Detects Liquidity Sweeps, Fair Value Gaps (FVG), Order Blocks (OB), and BOS/CHoCH.
    """
    def __init__(self, df: pd.DataFrame):
        # Ensure we have capitalized columns for standard processing
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("open", "high", "low", "close", "volume"):
                rename[col] = cl.capitalize()
        self.df = df.rename(columns=rename) if rename else df
        
    def analyze(self) -> list:
        """Runs all ICT detections and returns a list of found concepts."""
        if len(self.df) < 5:
            return []
            
        signals = []
        
        # Check FVG on the latest candles
        fvg = self._detect_fvg()
        if fvg:
            signals.append(fvg)
            
        # Check Order Blocks near current price
        ob = self._detect_order_block()
        if ob:
            signals.append(ob)
            
        # Check for Liquidity Sweeps
        sweep = self._detect_liquidity_sweep()
        if sweep:
            signals.append(sweep)
            
        # Check for Break of Structure
        bos = self._detect_bos()
        if bos:
            signals.append(bos)
            
        return signals
        
    def _detect_fvg(self) -> str:
        """
        Detects Fair Value Gap (FVG) in the last 3 closed candles.
        Bullish FVG: Low of candle 3 is higher than High of candle 1.
        Bearish FVG: High of candle 3 is lower than Low of candle 1.
        """
        if len(self.df) < 4:
            return None
            
        # We look at the last 3 completed candles: iloc[-4], iloc[-3], iloc[-2]
        # (iloc[-1] is the current forming candle or latest close)
        c1 = self.df.iloc[-4]
        c2 = self.df.iloc[-3]
        c3 = self.df.iloc[-2]
        c4 = self.df.iloc[-1]
        
        # Bullish FVG check
        if c3['Low'] > c1['High']:
            # Gap size
            gap = c3['Low'] - c1['High']
            # If current price is dropping back into the FVG (mitigation)
            if c4['Low'] <= c3['Low'] and c4['Close'] >= c1['High']:
                return "Bullish FVG Mitigated (Buy Zone)"
            return "Bullish FVG Formed (Imbalance)"
            
        # Bearish FVG check
        if c3['High'] < c1['Low']:
            gap = c1['Low'] - c3['High']
            if c4['High'] >= c3['High'] and c4['Close'] <= c1['Low']:
                return "Bearish FVG Mitigated (Sell Zone)"
            return "Bearish FVG Formed (Imbalance)"
            
        return None

    def _detect_order_block(self) -> str:
        """
        Simplified Order Block (OB) detection.
        Bullish OB: The last down candle before a strong up move.
        Bearish OB: The last up candle before a strong down move.
        Checks if current price is interacting with a recent OB.
        """
        if len(self.df) < 10:
            return None
            
        # Lookback window for strong moves
        window = self.df.iloc[-10:-1]
        
        # Find the largest up-move and down-move in the window
        # For a bullish OB, we want a strong green candle
        returns = window['Close'] - window['Open']
        max_bullish_idx = returns.idxmax()
        max_bearish_idx = returns.idxmin()
        
        if returns[max_bullish_idx] > window['Close'].mean() * 0.01: # 1% move roughly
            # Find the last down candle before this up move
            idx_pos = window.index.get_loc(max_bullish_idx)
            if idx_pos > 0:
                prev_candle = window.iloc[idx_pos - 1]
                if prev_candle['Close'] < prev_candle['Open']: # It was a down candle
                    ob_high = prev_candle['High']
                    ob_low = prev_candle['Low']
                    # Check if current price is testing this OB
                    current = self.df.iloc[-1]
                    if current['Low'] <= ob_high and current['Close'] >= ob_low:
                        return "Bullish Order Block Tested (Smart Money Buy)"
                        
        if returns[max_bearish_idx] < -window['Close'].mean() * 0.01:
            idx_pos = window.index.get_loc(max_bearish_idx)
            if idx_pos > 0:
                prev_candle = window.iloc[idx_pos - 1]
                if prev_candle['Close'] > prev_candle['Open']: # It was an up candle
                    ob_high = prev_candle['High']
                    ob_low = prev_candle['Low']
                    current = self.df.iloc[-1]
                    if current['High'] >= ob_low and current['Close'] <= ob_high:
                        return "Bearish Order Block Tested (Smart Money Sell)"
                        
        return None

    def _detect_liquidity_sweep(self) -> str:
        """
        Detects if the current or previous candle wicked past a recent major high/low 
        but closed inside the range (Stop Hunt / Liquidity Sweep).
        """
        if len(self.df) < 20:
            return None
            
        # Find recent highs/lows over a 15 candle window (excluding last 2)
        past_window = self.df.iloc[-20:-2]
        recent_high = past_window['High'].max()
        recent_low = past_window['Low'].min()
        
        current = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        # Bullish Sweep (Sweeps lows and closes higher)
        if current['Low'] < recent_low and current['Close'] > recent_low:
            return "Bullish Liquidity Sweep (Stop Hunt at Lows)"
        if prev['Low'] < recent_low and prev['Close'] > recent_low and current['Close'] > prev['Close']:
            return "Confirmed Bullish Liquidity Sweep"
            
        # Bearish Sweep (Sweeps highs and closes lower)
        if current['High'] > recent_high and current['Close'] < recent_high:
            return "Bearish Liquidity Sweep (Stop Hunt at Highs)"
        if prev['High'] > recent_high and prev['Close'] < recent_high and current['Close'] < prev['Close']:
            return "Confirmed Bearish Liquidity Sweep"
            
        return None

    def _detect_bos(self) -> str:
        """
        Detects Break of Structure (BOS) or Change of Character (CHoCH).
        Checks if the last closed candle decisively broke a recent swing high/low.
        """
        if len(self.df) < 20:
            return None
            
        past_window = self.df.iloc[-20:-5]
        swing_high = past_window['High'].max()
        swing_low = past_window['Low'].min()
        
        current = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        # Bullish BOS
        if prev['Close'] > swing_high and current['Close'] > swing_high:
            return "Bullish Break of Structure (BOS)"
            
        # Bearish BOS
        if prev['Close'] < swing_low and current['Close'] < swing_low:
            return "Bearish Break of Structure (BOS)"
            
        return None
