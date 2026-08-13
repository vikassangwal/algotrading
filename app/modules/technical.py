import logging
import pandas as pd
import numpy as np
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

# Import the AI Composite Engine
from .ai_composite_engine import AICompositeEngine
from .pattern_engine import PatternEngine

logger = logging.getLogger("elco.module.technical.master")

class TechnicalModule(AnalysisModule):
    name = "technical"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            # Fetch 1D data
            candles_1d = self.provider.get_candles(symbol, timeframe="1d", count=250)
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch market data."])

        if len(candles_1d) < 50:
            return ModuleSignal(self.name, 0.0, 0.1, ["Insufficient data for AI Composite Score."])

        df_1d = pd.DataFrame([{
            'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close,
            'volume': getattr(c, 'volume', 0)
        } for c in candles_1d])

        reasons = []
        total_score = 0.0
        
        reasons.append("--- MASTER AI COMPOSITE ENGINE INITIALIZED ---")

        # Initialize AI Composite Engine
        ai_engine = AICompositeEngine(df_1d)
        composite_data = ai_engine.calculate_scores()
        
        # Detect Patterns
        pattern_engine = PatternEngine(df_1d)
        patterns_found = pattern_engine.analyze()
        
        if patterns_found:
            reasons.append(f"Chart Patterns Detected: {', '.join(patterns_found)}")
            composite_data['patterns_detected'] = patterns_found
        else:
            composite_data['patterns_detected'] = ["No Major Patterns Detected"]

        # Institutional confluence: count how many real sub-scores confirm the
        # composite direction (bullish >55 / bearish <45), plus pattern & regime.
        subs = composite_data.get('sub_scores', {})
        direction_up = composite_data['probability_pct'] >= 50
        checks = 0
        all_indicator_keys = ["trend", "momentum", "volume", "volatility", "smart_money", "options", "risk", "macd", "adx", "bollinger", "stochastic", "vwap"]
        for key in all_indicator_keys:
            val = subs.get(key, 50)
            if direction_up and val >= 55:
                checks += 1
            elif (not direction_up) and val <= 45:
                checks += 1
        if patterns_found:
            checks += 1
        
        # Add descriptive reasons for the new indicators
        if subs.get('macd', 50) >= 60: reasons.append("Bullish MACD Crossover and rising Histogram.")
        elif subs.get('macd', 50) <= 40: reasons.append("Bearish MACD breakdown with falling momentum.")
        
        if subs.get('adx', 50) >= 60: reasons.append("Strong ADX Trend Validation with DMI+ dominance.")
        
        if subs.get('bollinger', 50) >= 70: reasons.append("Price action riding the Upper Bollinger Band (Strong Momentum).")
        elif subs.get('bollinger', 50) <= 30: reasons.append("Mean Reversion setup: Price near Lower Bollinger Band.")
        
        if subs.get('stochastic', 50) >= 70: reasons.append("Stochastic Oscillator turning up from Oversold territory.")
        elif subs.get('stochastic', 50) <= 30: reasons.append("Stochastic Oscillator dropping from Overbought territory.")
        
        if subs.get('vwap', 50) >= 60: reasons.append("Price sustaining above Daily VWAP (Institutional Accumulation).")
        
        # Cap display at max checks.
        confluence_passed = min(len(all_indicator_keys) + 1, checks)
        composite_data['confluence_filters_passed'] = confluence_passed
        reasons.append(f"AI Filter Confluence: {confluence_passed}/{len(all_indicator_keys)} real indicator checks confirm direction.")

        if composite_data['action'] in ["Strong Buy", "Buy"]:
            total_score = composite_data['probability_pct'] / 100.0
            reasons.append(f"AI Composite Rating: {composite_data['action']} with {composite_data['confidence_pct']}% Confidence.")
        elif composite_data['action'] in ["Strong Sell", "Sell"]:
            total_score = - (composite_data['probability_pct'] / 100.0)
            reasons.append(f"AI Composite Rating: {composite_data['action']} with {composite_data['confidence_pct']}% Confidence.")
        else:
            total_score = 0.0
            reasons.append(f"AI Composite Rating: HOLD (Neutral)")

        # Attach the full composite data to the signal's reasons so the frontend can parse it if needed
        # Or better yet, we can attach it as a special attribute if our framework supports it.
        # For now, we will JSON serialize it into the reasons list so the frontend can extract it.
        import json
        reasons.append(f"JSON_DATA:{json.dumps(composite_data)}")

        return ModuleSignal(self.name, total_score, composite_data['confidence_pct'] / 100.0, reasons)
