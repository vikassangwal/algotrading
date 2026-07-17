import pandas as pd
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger("elco.module.institutional")

class InstitutionalEngine:
    """
    Handles Smart Money Concepts (SMC), ICT, Wyckoff, Market Structure, Volume Analysis, Order Flow.
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
        # 1. Market Structure (BOS / CHOCH)
        # ==================================
        swing_high = self.df['high'].rolling(5, center=True).max().iloc[-3]
        swing_low = self.df['low'].rolling(5, center=True).min().iloc[-3]
        
        if self.current['close'] > swing_high:
            score += 0.2
            reasons.append("Market Structure: Bullish Break of Structure (BOS) / CHOCH detected.")
        elif self.current['close'] < swing_low:
            score -= 0.2
            reasons.append("Market Structure: Bearish Break of Structure (BOS) / CHOCH detected.")

        # ==================================
        # 2. Smart Money Concepts (FVG & Order Blocks)
        # ==================================
        # FVG
        if self.current['low'] > self.df.iloc[-3]['high']:
            score += 0.15
            reasons.append("SMC: Bullish Fair Value Gap (FVG) / Imbalance created.")
        elif self.current['high'] < self.df.iloc[-3]['low']:
            score -= 0.15
            reasons.append("SMC: Bearish Fair Value Gap (FVG) / Imbalance created.")
            
        # Order Block Proxy (Last down candle before a strong up move)
        if self.prev2['close'] < self.prev2['open'] and self.prev['close'] > self.prev['open'] and self.current['close'] > self.prev['close']:
            if self.current['volume'] > self.df['volume'].mean() * 1.5:
                score += 0.15
                reasons.append("SMC: Bullish Order Block (OB) validated with strong volume expansion.")

        # ==================================
        # 3. ICT Concepts (Liquidity Sweeps & Kill Zones)
        # ==================================
        if self.current['low'] < swing_low and self.current['close'] > swing_low:
            score += 0.2
            reasons.append("ICT: Sell-Side Liquidity Sweep (Turtle Soup) - Bullish Rejection.")
        elif self.current['high'] > swing_high and self.current['close'] < swing_high:
            score -= 0.2
            reasons.append("ICT: Buy-Side Liquidity Sweep (Turtle Soup) - Bearish Rejection.")
            
        # Kill Zones (Proxy based on typical time volatility, simulated if datetime index not present perfectly)
        # Assuming we just check if it's high volume (Silver Bullet proxy)
        if self.current['volume'] > self.df['volume'].mean() * 3:
            reasons.append("ICT: Extreme Volume Spikes detected (Potential Kill Zone / Silver Bullet entry window).")

        # ==================================
        # 4. Volume Analysis (VSA, OBV, VWAP)
        # ==================================
        avg_vol = self.df['volume'].mean()
        
        # Volume Spread Analysis (VSA) - Effort vs Result
        spread = self.current['high'] - self.current['low']
        if self.current['volume'] > avg_vol * 2 and spread < (self.df['high'] - self.df['low']).mean() * 0.5:
            if self.current['close'] < self.current['open']:
                score += 0.2
                reasons.append("VSA (Volume Analysis): Heavy Effort but no Result. Bullish Absorption at lows.")
            else:
                score -= 0.2
                reasons.append("VSA (Volume Analysis): Heavy Effort but no Result. Bearish Distribution at highs.")

        # On-Balance Volume (OBV)
        obv = (np.sign(self.df['close'].diff()) * self.df['volume']).fillna(0).cumsum()
        if obv.iloc[-1] > obv.rolling(20).mean().iloc[-1] and self.current['close'] < self.df['close'].rolling(20).mean().iloc[-1]:
            score += 0.15
            reasons.append("Volume Analysis: OBV Bullish Divergence (Smart Money is accumulating).")
            
        # VWAP (Volume Weighted Average Price) Proxy (Using HLC3 for Daily VWAP anchor approximation)
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        vwap = (typical_price * self.df['volume']).sum() / (self.df['volume'].sum() + 1e-8)
        if self.current['close'] > vwap:
            score += 0.1
            reasons.append(f"Volume Analysis: Price is above Anchored VWAP ({vwap:.2f}) - Institutional Buy Bias.")
        elif self.current['close'] < vwap:
            score -= 0.1
            reasons.append(f"Volume Analysis: Price is below Anchored VWAP ({vwap:.2f}) - Institutional Sell Bias.")

        # Volume Profile Proxy (Finding the Point of Control - POC)
        # We bin the typical prices into 10 buckets and sum the volume for each bucket
        min_price = typical_price.min()
        max_price = typical_price.max()
        bins = np.linspace(min_price, max_price, 10)
        bin_indices = np.digitize(typical_price, bins)
        
        vol_profile = {}
        for i in range(1, 11):
            vol_profile[i] = 0
            
        for i in range(len(self.df)):
            b_idx = bin_indices[i]
            if b_idx > 10: b_idx = 10
            vol_profile[b_idx] += self.df['volume'].iloc[i]
            
        # Find Point of Control (Bucket with max volume)
        poc_bin = max(vol_profile, key=vol_profile.get)
        poc_price = bins[poc_bin - 1] if poc_bin <= len(bins) else bins[-1]
        
        if self.current['close'] > poc_price:
            score += 0.15
            reasons.append(f"Order Flow / Volume Profile: Price is above Point of Control (POC ~{poc_price:.2f}) indicating Buyer Dominance.")
        else:
            score -= 0.15
            reasons.append(f"Order Flow / Volume Profile: Price is below Point of Control (POC ~{poc_price:.2f}) indicating Seller Dominance.")

        # ==================================
        # 5. Wyckoff Method (Climaxes)
        # ==================================
        if self.current['volume'] > avg_vol * 2.5:
            if self.current['close'] > self.current['open'] and self.current['low'] < swing_low:
                score += 0.2
                reasons.append("Wyckoff: Potential Phase C 'Spring' (Climactic volume marking a bottom).")
            elif self.current['close'] < self.current['open'] and self.current['high'] > swing_high:
                score -= 0.2
                reasons.append("Wyckoff: Potential Phase C 'Upthrust' (Climactic volume marking a top).")

        # ==================================
        # 6. Power of Three (PO3) - ICT Concept
        # ==================================
        # PO3 consists of: Accumulation (consolidation), Manipulation (fakeout), Distribution (real trend).
        # We look for a tight range over N bars, followed by a sweep of that range, followed by strong momentum the other way.
        recent_20 = self.df.tail(20)
        first_10 = recent_20.head(10)
        last_5 = recent_20.tail(5)
        
        acc_high = first_10['high'].max()
        acc_low = first_10['low'].min()
        acc_range = acc_high - acc_low
        
        if acc_range / (acc_low + 1e-8) < 0.02: # Tight accumulation phase (2% range)
            manipulation_low = last_5['low'].min()
            manipulation_high = last_5['high'].max()
            
            # Bullish PO3: Fakeout below accumulation low, then close above it
            if manipulation_low < acc_low and self.current['close'] > acc_low + (acc_range * 0.5):
                score += 0.25
                reasons.append("ICT (PO3): Bullish Power of Three detected (Accumulation -> Manipulation below Lows -> Distribution UP).")
                
            # Bearish PO3: Fakeout above accumulation high, then close below it
            elif manipulation_high > acc_high and self.current['close'] < acc_high - (acc_range * 0.5):
                score -= 0.25
                reasons.append("ICT (PO3): Bearish Power of Three detected (Accumulation -> Manipulation above Highs -> Distribution DOWN).")

        return {
            "branch": "Institutional / SMC",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
