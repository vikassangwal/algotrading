import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.pattern")

class PatternModule(AnalysisModule):
    name = "pattern"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            # Fetch last 3 days to identify 2-day patterns
            candles = self.provider.get_candles(symbol, timeframe="1d", count=3)
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch market data."])

        if len(candles) < 3:
            return ModuleSignal(self.name, 0.0, 0.1, ["Insufficient data to detect patterns."])

        # Current and Previous candle
        prev = candles[1]
        curr = candles[2]

        score = 0.0
        reasons = []

        prev_body = abs(prev.close - prev.open)
        curr_body = abs(curr.close - curr.open)
        
        is_prev_bullish = prev.close > prev.open
        is_prev_bearish = prev.close < prev.open
        
        is_curr_bullish = curr.close > curr.open
        is_curr_bearish = curr.close < curr.open

        # Bullish Engulfing Pattern
        if is_prev_bearish and is_curr_bullish:
            if curr.open <= prev.close and curr.close >= prev.open:
                score += 0.8
                reasons.append("Detected BULLISH ENGULFING pattern. Reversal likely.")

        # Bearish Engulfing Pattern
        if is_prev_bullish and is_curr_bearish:
            if curr.open >= prev.close and curr.close <= prev.open:
                score -= 0.8
                reasons.append("Detected BEARISH ENGULFING pattern. Reversal likely.")

        # Doji (Indecision)
        if curr_body < (curr.high - curr.low) * 0.1:
            reasons.append("Detected DOJI pattern. Market indecision.")
            # Reduce existing score due to indecision
            score *= 0.5

        if score == 0.0:
            reasons.append("No significant candlestick patterns detected.")

        confidence = 0.6 if score != 0.0 else 0.2

        return ModuleSignal(
            module=self.name,
            score=score,
            confidence=confidence,
            reasons=reasons
        )
