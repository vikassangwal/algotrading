import logging
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.ml_model")

class MLModelModule(AnalysisModule):
    name = "ml_model"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            # We fetch 1D candles to simulate daily feature extraction
            candles = self.provider.get_candles(symbol, timeframe="1d", count=5)
        except Exception as e:
            logger.error(f"Failed to fetch data for ML Model: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["ML Inference failed (No data)."])

        if len(candles) < 5:
            return ModuleSignal(self.name, 0.0, 0.1, ["Insufficient data for ML inference."])

        # Calculate a simple trend feature based on recent 5 days
        start_price = candles[0].open
        end_price = candles[-1].close
        trend_pct = ((end_price - start_price) / start_price) * 100

        # Simulate a Quant ML Model (e.g. Random Forest / LSTM)
        # In reality, this would load a .pkl / .onnx model and run inference on technical features.
        # We will deterministically mock this using the trend_pct to give realistic-looking scores.
        
        reasons = []
        
        # Base probability is 0.5
        # If trend is strongly up, model predicts mean reversion or continuation
        # Let's say our model is a momentum model:
        prediction_score = 0.0
        
        if trend_pct > 2.0:
            prediction_score = 0.7 # 70% probability of continuation
            reasons.append("Momentum model: strong bullish trend over last 5 days (continuation bias).")
        elif trend_pct < -2.0:
            prediction_score = -0.7 # 70% probability of bearish continuation
            reasons.append("Momentum model: strong bearish trend over last 5 days (continuation bias).")
        else:
            prediction_score = 0.1 # Slight bullish bias on flat market
            reasons.append("Momentum model: no significant edge (Neutral/Sideways).")

        # Deterministic per module contract (no random noise): clamp the trend-derived score.
        final_score = max(-1.0, min(1.0, prediction_score))
        
        confidence = abs(final_score) * 0.8 + 0.1

        return ModuleSignal(
            module=self.name,
            score=final_score,
            confidence=confidence,
            reasons=reasons
        )
