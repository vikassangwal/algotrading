import pandas as pd
import numpy as np

class QuantEngine:
    """
    Market Structure (HH/LL), Volatility Regimes, and Correlation.
    """
    def __init__(self, df: pd.DataFrame):
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("open", "high", "low", "close", "volume"):
                rename[col] = cl.capitalize()
        self.df = df.rename(columns=rename) if rename else df

    def analyze(self) -> dict:
        if len(self.df) < 20:
            return {}
            
        ms = self._calc_market_structure()
        vr = self._calc_volatility_regime()
        
        return {
            "market_structure": ms,
            "volatility_regime": vr
        }

    def _calc_market_structure(self) -> str:
        """Detects HH, HL, LH, LL."""
        close = self.df['Close']
        
        # Extremely simplified swing detection
        swings = []
        for i in range(2, len(close)-2):
            if close.iloc[i] > close.iloc[i-1] and close.iloc[i] > close.iloc[i+1]:
                swings.append(('High', close.iloc[i]))
            elif close.iloc[i] < close.iloc[i-1] and close.iloc[i] < close.iloc[i+1]:
                swings.append(('Low', close.iloc[i]))
                
        if len(swings) < 4:
            return "Consolidating"
            
        # Get last two highs and last two lows
        highs = [s[1] for s in swings if s[0] == 'High']
        lows = [s[1] for s in swings if s[0] == 'Low']
        
        if len(highs) >= 2 and len(lows) >= 2:
            last_h, prev_h = highs[-1], highs[-2]
            last_l, prev_l = lows[-1], lows[-2]
            
            if last_h > prev_h and last_l > prev_l:
                return "Higher Highs & Higher Lows (Uptrend)"
            elif last_h < prev_h and last_l < prev_l:
                return "Lower Highs & Lower Lows (Downtrend)"
            elif last_h < prev_h and last_l > prev_l:
                return "Symmetrical Contraction (Compression)"
            elif last_h > prev_h and last_l < prev_l:
                return "Broadening Expansion"
                
        return "Mixed Structure"

    def _calc_volatility_regime(self) -> str:
        """Uses ATR Z-Score to define Volatility Regime."""
        tr1 = self.df['High'] - self.df['Low']
        tr2 = (self.df['High'] - self.df['Close'].shift(1)).abs()
        tr3 = (self.df['Low'] - self.df['Close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(14).mean()
        
        # Calculate Z-Score of ATR over a 50 day period
        atr_mean = atr.rolling(50).mean()
        atr_std = atr.rolling(50).std()
        
        curr_atr = atr.iloc[-1]
        mean_val = atr_mean.iloc[-1]
        std_val = atr_std.iloc[-1]
        
        if std_val == 0 or pd.isna(std_val):
            return "Normal Volatility"
            
        z_score = (curr_atr - mean_val) / std_val
        
        if z_score > 2:
            return "Extreme Volatility (Institutional Rebalancing / Panic)"
        elif z_score > 1:
            return "High Volatility (Expansion Phase)"
        elif z_score < -1:
            return "Low Volatility (Contraction / Accumulation)"
        else:
            return "Normal Volatility"
