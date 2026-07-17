import logging
from .base import AnalysisModule, ModuleSignal

# Import the Quant sub-engines
from .quant_branches.time_series import TimeSeriesEngine
from .quant_branches.risk_portfolio import RiskPortfolioEngine
from .quant_branches.machine_learning import MachineLearningEngine
from .quant_branches.stat_arb import StatArbEngine

logger = logging.getLogger("elco.module.quant.master")

class QuantModule(AnalysisModule):
    name = "quant"

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []
        
        try:
            raw_data = {}
            if hasattr(self.provider, 'get_quant_data'):
                raw_data = self.provider.get_quant_data(symbol) or {}
                
            # Fetch OHLC data for ML training
            candles = self.provider.get_candles(symbol, "1d", 250)
            import pandas as pd
            if candles:
                df = pd.DataFrame([{
                    'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close, 'volume': getattr(c, 'volume', 0)
                } for c in candles])
                raw_data['df'] = df
            else:
                # Optional yfinance fallback — only when explicitly enabled
                # (avoids hidden network I/O in the analysis hot path).
                import os
                if os.getenv("ELCO_LIVE_MACRO", "false").strip().lower() == "true":
                    import yfinance as yf
                    ticker = yf.Ticker(symbol + ".NS" if not symbol.endswith(".NS") else symbol)
                    df = ticker.history(period="1y")
                    if not df.empty:
                        df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
                        raw_data['df'] = df
                
        except Exception as e:
            logger.error(f"Failed to fetch quant data for {symbol}: {e}")
        
        reasons.append("--- MASTER 18-LEVEL QUANTITATIVE ENGINE INITIALIZED ---")

        total_score = 0.0
        
        # ==========================================
        # ENGINE 1: Time Series & Forecasting
        # ==========================================
        ts_engine = TimeSeriesEngine(raw_data)
        ts_res = ts_engine.analyze()
        total_score += ts_res['score']
        reasons.extend(ts_res['reasons'])

        # ==========================================
        # ENGINE 2: Risk & Portfolio
        # ==========================================
        risk_engine = RiskPortfolioEngine(raw_data)
        risk_res = risk_engine.analyze()
        total_score += risk_res['score']
        reasons.extend(risk_res['reasons'])

        # ==========================================
        # ENGINE 3: Machine Learning
        # ==========================================
        ml_engine = MachineLearningEngine(raw_data)
        ml_res = ml_engine.analyze()
        total_score += ml_res['score']
        reasons.extend(ml_res['reasons'])

        # ==========================================
        # ENGINE 4: Stat Arb & Microstructure
        # ==========================================
        arb_engine = StatArbEngine(raw_data)
        arb_res = arb_engine.analyze()
        total_score += arb_res['score']
        reasons.extend(arb_res['reasons'])

        # ==========================================
        # MASTER QUANT AGGREGATION
        # ==========================================
        final_score = total_score / 4.0
        
        # Probability of Success calculation
        base_prob = raw_data.get("xgboost_win_probability")
        if base_prob is None:
            base_prob = 0.5
        adjusted_prob = base_prob + (final_score * 0.15)
        win_probability = min(max(adjusted_prob, 0.0), 1.0)
        
        if final_score > 0.4:
            reasons.insert(0, f"QUANTITATIVE SCORE: HIGHLY FAVORABLE (Probability of Success: {win_probability*100:.1f}%)")
            confidence = 0.90
        elif final_score < -0.4:
            reasons.insert(0, f"QUANTITATIVE SCORE: HIGHLY UNFAVORABLE (Probability of Success: {win_probability*100:.1f}%)")
            confidence = 0.90
        else:
            reasons.insert(0, f"QUANTITATIVE SCORE: NEUTRAL / LOW EDGE (Probability of Success: {win_probability*100:.1f}%)")
            confidence = 0.50

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
