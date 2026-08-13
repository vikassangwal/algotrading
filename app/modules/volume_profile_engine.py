import pandas as pd
import numpy as np

class VolumeProfileEngine:
    """
    Calculates Volume Profile (POC, VAH, VAL) and Wyckoff proxy phases.
    """
    def __init__(self, df: pd.DataFrame):
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("open", "high", "low", "close", "volume"):
                rename[col] = cl.capitalize()
        self.df = df.rename(columns=rename) if rename else df

    def analyze(self) -> dict:
        if len(self.df) < 20 or 'Volume' not in self.df.columns:
            return {}
            
        vp = self._calc_volume_profile()
        wyckoff = self._calc_wyckoff_phase()
        
        return {
            "poc": vp.get("poc", 0),
            "vah": vp.get("vah", 0),
            "val": vp.get("val", 0),
            "wyckoff_phase": wyckoff
        }
        
    def _calc_volume_profile(self, bins=20) -> dict:
        # Looking at last 50 periods for local volume profile
        window = self.df.iloc[-50:]
        min_p = window['Low'].min()
        max_p = window['High'].max()
        
        if max_p == min_p:
            return {}
            
        step = (max_p - min_p) / bins
        profile = np.zeros(bins)
        
        for _, row in window.iterrows():
            avg_price = (row['High'] + row['Low'] + row['Close']) / 3
            idx = int(min(bins - 1, (avg_price - min_p) / step))
            profile[idx] += row['Volume']
            
        poc_idx = np.argmax(profile)
        poc_price = min_p + (poc_idx * step) + (step / 2)
        
        # Value Area (70% of volume)
        total_vol = np.sum(profile)
        va_vol = profile[poc_idx]
        lower_idx = poc_idx
        upper_idx = poc_idx
        
        while va_vol < total_vol * 0.70:
            lower_val = profile[lower_idx - 1] if lower_idx > 0 else 0
            upper_val = profile[upper_idx + 1] if upper_idx < bins - 1 else 0
            
            if lower_val == 0 and upper_val == 0:
                break
                
            if lower_val > upper_val:
                lower_idx -= 1
                va_vol += lower_val
            else:
                upper_idx += 1
                va_vol += upper_val
                
        val_price = min_p + (lower_idx * step)
        vah_price = min_p + (upper_idx * step) + step
        
        return {"poc": poc_price, "vah": vah_price, "val": val_price}

    def _calc_wyckoff_phase(self) -> str:
        """Proxy for Wyckoff phases using price position vs 50 EMA and Volume."""
        if len(self.df) < 50:
            return "Unknown"
            
        close = self.df['Close']
        vol = self.df['Volume']
        
        ema50 = close.ewm(span=50, adjust=False).mean()
        
        curr_price = close.iloc[-1]
        curr_ema = ema50.iloc[-1]
        
        # Determine trend of EMA
        ema_trend = ema50.iloc[-1] - ema50.iloc[-20]
        
        if curr_price > curr_ema and ema_trend > 0:
            return "Markup Phase (Uptrend)"
        elif curr_price < curr_ema and ema_trend < 0:
            return "Markdown Phase (Downtrend)"
        elif curr_price > curr_ema and ema_trend <= 0:
            # High volume at top?
            if vol.iloc[-10:].mean() > vol.iloc[-50:].mean():
                return "Distribution Phase (Smart Money Selling)"
            return "Consolidation"
        elif curr_price < curr_ema and ema_trend >= 0:
            # High volume at bottom?
            if vol.iloc[-10:].mean() > vol.iloc[-50:].mean():
                return "Accumulation Phase (Smart Money Buying)"
            return "Consolidation"
            
        return "Unknown"
