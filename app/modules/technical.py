import logging
import pandas as pd
import numpy as np
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

# Import the AI Composite Engine
from .ai_composite_engine import AICompositeEngine
from .pattern_engine import PatternEngine
from .ict_engine import ICTEngine
from .candlestick_engine import CandlestickEngine
from .volume_profile_engine import VolumeProfileEngine
from .quant_engine import QuantEngine
from .ultra_quant_engine import UltraQuantEngine
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
        
        # Detect ICT / SMC Concepts
        ict_engine = ICTEngine(df_1d)
        ict_signals = ict_engine.analyze()
        
        # Detect Candlesticks & Divergence
        candle_engine = CandlestickEngine(df_1d)
        candle_signals = candle_engine.analyze()
        
        # Detect Volume Profile & Wyckoff
        vp_engine = VolumeProfileEngine(df_1d)
        vp_data = vp_engine.analyze()
        if vp_data and vp_data.get('wyckoff_phase') != "Unknown":
            reasons.append(f"Wyckoff Phase: {vp_data['wyckoff_phase']}")
            
        # Detect Quant Market Structure & Volatility
        quant_engine = QuantEngine(df_1d)
        quant_data = quant_engine.analyze()
        if quant_data:
            reasons.append(f"Market Structure: {quant_data.get('market_structure', 'Unknown')}")
            reasons.append(f"Volatility Regime: {quant_data.get('volatility_regime', 'Normal')}")
            
        # Detect Ultra-Advanced Quant (FFT, Monte Carlo, Kelly, ML)
        ultra_engine = UltraQuantEngine(df_1d)
        ultra_data = ultra_engine.analyze()
        if ultra_data:
            reasons.append(f"Machine Learning Forecast: {ultra_data.get('ml_prediction')}")
            reasons.append(f"Monte Carlo Probability (Next 5 Days): {ultra_data.get('monte_carlo_win_prob')}% Win Rate")
            reasons.append(f"FFT Cycle Prediction: {ultra_data.get('fft_cycle')}")
            reasons.append(f"Microstructure Volume Delta: {ultra_data.get('volume_delta_proxy')}")
            reasons.append(f"Optimal Kelly Position Size: Risk {ultra_data.get('recommended_kelly_pct')}% of Capital")
            # Overwrite final probability score with Monte Carlo average if it exists
            mc_prob = ultra_data.get('monte_carlo_win_prob', 50)
            composite_data['probability_pct'] = int(round((composite_data['probability_pct'] + mc_prob) / 2))
        
        # Combine patterns and ICT
        all_price_action = patterns_found + ict_signals + candle_signals
        
        if all_price_action:
            reasons.append(f"Price Action, Candlesticks & SMC Detected: {', '.join(all_price_action)}")
            composite_data['patterns_detected'] = all_price_action
        else:
            composite_data['patterns_detected'] = ["No Major Patterns Detected"]

        # Boost AI Confidence if ICT signals align with the trend
        if ict_signals:
            bullish_ict = any("Bullish" in s for s in ict_signals)
            bearish_ict = any("Bearish" in s for s in ict_signals)
            
            if composite_data['probability_pct'] >= 50 and bullish_ict:
                composite_data['probability_pct'] = min(98, composite_data['probability_pct'] + 10)
                composite_data['confidence_pct'] = min(98, composite_data['confidence_pct'] + 15)
                reasons.append("SMART MONEY BUY SIGNAL: ICT setup aligns with AI trend.")
            elif composite_data['probability_pct'] < 50 and bearish_ict:
                composite_data['probability_pct'] = max(2, composite_data['probability_pct'] - 10)
                composite_data['confidence_pct'] = min(98, composite_data['confidence_pct'] + 15)
                reasons.append("SMART MONEY SELL SIGNAL: ICT setup aligns with AI trend.")

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
