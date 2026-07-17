import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger("elco.module.ai_regime")

class MarketRegimeEngine:
    def __init__(self, provider):
        """
        AI Market Regime Detection using statistical metrics.
        Classifies the market into:
        1. TRENDING (High ADX, low chop)
        2. RANGE_BOUND (Low ADX, high chop, mean-reverting)
        3. HIGH_VOLATILITY (High ATR, wide Bollinger Bands)
        """
        self.provider = provider

    def detect_regime(self, symbol: str) -> Dict[str, Any]:
        try:
            candles = self.provider.get_candles(symbol, timeframe="1d", count=60)
            if not candles or len(candles) < 20:
                return {"regime": "UNKNOWN", "confidence": 0}

            closes = np.array([c.close for c in candles], dtype=float)
            highs = np.array([c.high for c in candles], dtype=float)
            lows = np.array([c.low for c in candles], dtype=float)
            
            # Simple ADX proxy (Directional Movement)
            # Since full talib might not be available, we approximate
            atr = self._calculate_atr(highs, lows, closes, 14)
            recent_atr = atr[-1]
            avg_atr = np.mean(atr[-14:])
            
            # Trend proxy: Distance from 20 MA vs 50 MA
            ma20 = np.mean(closes[-20:])
            ma50 = np.mean(closes[-50:])
            trend_strength = abs(ma20 - ma50) / ma50
            
            # Chop Index proxy (Consolidation)
            highest_high = np.max(highs[-14:])
            lowest_low = np.min(lows[-14:])
            range_abs = highest_high - lowest_low
            sum_atr = np.sum(atr[-14:])
            
            # Choppiness Index (approximated) = 100 * LOG10( SUM(ATR, n) / (MaxHigh(n) - MinLow(n)) ) / LOG10(n)
            # High chop means range bound. Low chop means trending.
            chop_index = 50 # neutral default
            if range_abs > 0:
                try:
                    chop_index = 100 * np.log10(sum_atr / range_abs) / np.log10(14)
                except:
                    chop_index = 50
                    
            regime = "UNKNOWN"
            confidence = 0.0
            
            # Classification Logic
            if recent_atr > avg_atr * 1.5:
                regime = "HIGH_VOLATILITY"
                confidence = min(1.0, (recent_atr / avg_atr) / 3.0)
            elif chop_index > 61.8:
                regime = "RANGE_BOUND"
                confidence = min(1.0, (chop_index - 61.8) / 38.2)
            elif chop_index < 38.2 and trend_strength > 0.02:
                regime = "TRENDING"
                confidence = min(1.0, (38.2 - chop_index) / 38.2)
            else:
                regime = "TRANSITIONING"
                confidence = 0.5
                
            return {
                "symbol": symbol,
                "regime": regime,
                "confidence": round(confidence, 2),
                "metrics": {
                    "choppiness_index": round(chop_index, 2),
                    "trend_strength_pct": round(trend_strength * 100, 2),
                    "atr_ratio": round(recent_atr / avg_atr if avg_atr > 0 else 1, 2)
                }
            }
        except Exception as e:
            logger.error(f"Error detecting regime for {symbol}: {e}")
            return {"regime": "UNKNOWN", "confidence": 0, "error": str(e)}

    def _calculate_atr(self, highs, lows, closes, period):
        atr = np.zeros_like(closes)
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            if i == 1:
                atr[i] = tr
            else:
                atr[i] = (atr[i-1] * (period - 1) + tr) / period
        return atr
