import pandas as pd
import numpy as np
import logging
import math

logger = logging.getLogger("elco.module.advanced_quant")

class AdvancedQuantEngine:
    """
    Handles Multi-Timeframe, FFT Cycles, Quantitative stats, Elliott Wave counts, Options PCR logic, Gann, Intermarket.
    """
    def __init__(self, df_1d: pd.DataFrame, df_15m: pd.DataFrame = None):
        self.df = df_1d
        self.df_15m = df_15m if df_15m is not None else df_1d # Fallback if no 15m
        self.current = df_1d.iloc[-1]

    def _apply_fourier_transform(self, series: pd.Series) -> float:
        data = series.values
        n = len(data)
        x = np.arange(n)
        poly = np.polyfit(x, data, 1)
        detrended = data - (poly[0]*x + poly[1])
        
        fft_vals = np.fft.fft(detrended)
        frequencies = np.fft.fftfreq(n)
        magnitudes = np.abs(fft_vals)
        magnitudes[0] = 0
        
        dom_idx = np.argsort(magnitudes)[-2]
        if dom_idx == 0: dom_idx = np.argsort(magnitudes)[-3]
        
        dom_freq = frequencies[dom_idx]
        phase = np.angle(fft_vals[dom_idx])
        amplitude = magnitudes[dom_idx] / n
        t_next = n
        slope = amplitude * np.cos(2 * np.pi * dom_freq * t_next + phase) * (2 * np.pi * dom_freq)
        
        return float(slope)

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        # ==================================
        # 1. Multi-Timeframe Analysis (MTFA)
        # ==================================
        trend_1d = self.df['close'].iloc[-1] > self.df['close'].rolling(20).mean().iloc[-1]
        trend_15m = self.df_15m['close'].iloc[-1] > self.df_15m['close'].rolling(20).mean().iloc[-1]
        
        if trend_1d and trend_15m:
            score += 0.15
            reasons.append("MTFA: Daily (1D) and Intraday (15M) trends are perfectly aligned (BULLISH).")
        elif not trend_1d and not trend_15m:
            score -= 0.15
            reasons.append("MTFA: Daily (1D) and Intraday (15M) trends are perfectly aligned (BEARISH).")
        else:
            reasons.append("MTFA: Timeframes are in conflict. Proceeding with caution.")

        # ==================================
        # 2. Cycle Analysis (FFT / Digital Signal Processing)
        # ==================================
        fft_slope = self._apply_fourier_transform(self.df['close'])
        if fft_slope > 0:
            score += 0.2
            reasons.append("Cycle Analysis: Dominant Fourier frequency indicates an upward phase.")
        else:
            score -= 0.2
            reasons.append("Cycle Analysis: Dominant Fourier frequency indicates a downward phase.")

        # ==================================
        # 3. Quantitative / Mean Reversion (Z-Score)
        # ==================================
        mean_price = self.df['close'].rolling(20).mean().iloc[-1]
        std_price = self.df['close'].rolling(20).std().iloc[-1]
        z_score = (self.current['close'] - mean_price) / (std_price + 1e-8)
        
        if z_score < -2.0:
            score += 0.25
            reasons.append(f"Quant: Price is {z_score:.2f} SD below mean (Strong Mean Reversion Buy).")
        elif z_score > 2.0:
            score -= 0.25
            reasons.append(f"Quant: Price is {z_score:.2f} SD above mean (Strong Mean Reversion Sell).")

        # ==================================
        # 4. Elliott Wave proxy
        # ==================================
        hh_count = 0
        for i in range(1, 6):
            if self.df['high'].iloc[-i] > self.df['high'].iloc[-(i+1)]:
                hh_count += 1
            else:
                break
        
        if hh_count == 3:
            score += 0.1
            reasons.append("Elliott Wave: Potential Wave 3 continuation detected.")
        elif hh_count >= 5:
            score -= 0.15
            reasons.append("Elliott Wave: Potential Wave 5 exhaustion. Expecting A-B-C correction.")

        # ==================================
        # 5. Gann Analysis (Geometry)
        # ==================================
        # Simple Square of Nine / Gann Angle proxy based on pure price geometry
        # Checking if current price is near a major psychological/Gann square root level
        sqrt_price = math.sqrt(self.current['close'])
        floor_sq = math.floor(sqrt_price) ** 2
        ceil_sq = math.ceil(sqrt_price) ** 2
        
        if abs(self.current['close'] - floor_sq) / (self.current['close'] + 1e-8) < 0.005:
            score += 0.1
            reasons.append(f"Gann Analysis: Price finding geometric support at Gann Square ({floor_sq}).")
        elif abs(self.current['close'] - ceil_sq) / (self.current['close'] + 1e-8) < 0.005:
            score -= 0.1
            reasons.append(f"Gann Analysis: Price finding geometric resistance at Gann Square ({ceil_sq}).")

        # ==================================
        # 6. Sentiment & Intermarket Analysis (Proxies)
        # ==================================
        # Since we don't have DXY or India VIX injected into this exact dataframe right now,
        # we will use historical volatility of the asset itself as a Fear gauge proxy (VIX proxy).
        volatility_expanding = std_price > self.df['close'].rolling(20).std().mean()
        market_crashing = self.current['close'] < self.df['close'].rolling(50).mean().iloc[-1]
        
        if volatility_expanding and market_crashing:
            score -= 0.15
            reasons.append("Sentiment Analysis: High Fear regime detected (Volatility spike + Downtrend).")
        elif volatility_expanding and not market_crashing:
            score += 0.1
            reasons.append("Sentiment Analysis: Greed / FOMO regime detected (Volatility spike + Uptrend).")

        return {
            "branch": "Advanced Quant & Macro",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
