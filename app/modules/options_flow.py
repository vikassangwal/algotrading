import logging
from .base import AnalysisModule, ModuleSignal

# Import the Options sub-engines
from .options_branches.greeks import OptionsGreeksEngine
from .options_branches.flow import OptionsFlowEngine
from .options_branches.max_pain import MaxPainEngine

logger = logging.getLogger("elco.module.options")

class OptionsFlowModule(AnalysisModule):
    name = "options_flow"

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []
        
        try:
            raw_data = {}
            if hasattr(self.provider, 'get_options_data'):
                raw_data = self.provider.get_options_data(symbol) or {}
            current_price = None
            if hasattr(self.provider, 'get_quote'):
                try:
                    current_price = self.provider.get_quote(symbol).ltp
                except:
                    pass
            if current_price is not None:
                raw_data["spot_price"] = current_price
        except Exception as e:
            logger.error(f"Failed to fetch options data for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch options data."])
        
        reasons.append("--- MASTER 18-LEVEL OPTIONS & F&O ENGINE INITIALIZED ---")

        total_score = 0.0
        
        # ==========================================
        # ENGINE 1: Options Greeks & Volatility
        # ==========================================
        greeks_engine = OptionsGreeksEngine(raw_data)
        greeks_res = greeks_engine.analyze()
        total_score += greeks_res['score']
        reasons.extend(greeks_res['reasons'])

        # ==========================================
        # ENGINE 2: Smart Money Flow (Traps)
        # ==========================================
        flow_engine = OptionsFlowEngine(raw_data)
        flow_res = flow_engine.analyze()
        total_score += flow_res['score']
        reasons.extend(flow_res['reasons'])

        # ==========================================
        # ENGINE 3: Max Pain & Expiry Magnet
        # ==========================================
        pain_engine = MaxPainEngine(raw_data)
        pain_res = pain_engine.analyze()
        total_score += pain_res['score']
        reasons.extend(pain_res['reasons'])

        # ==========================================
        # MASTER OPTIONS AGGREGATION
        # ==========================================
        final_score = total_score / 3.0
        
        # Confidence logic based on agreement across engines
        engine_scores = [greeks_res['score'], flow_res['score'], pain_res['score']]
        bulls = sum(1 for s in engine_scores if s > 0.05)
        bears = sum(1 for s in engine_scores if s < -0.05)
        
        if bulls == 3 or bears == 3:
            confidence = 0.95
            reasons.insert(1, "PERFECT OPTIONS CONFLUENCE: Greeks, Flow, and Max Pain all point in the same direction.")
        elif bulls >= 2 or bears >= 2:
            confidence = 0.80
            reasons.insert(1, "STRONG OPTIONS CONFLUENCE: Smart Money flow is decisively aligned.")
        else:
            confidence = 0.40
            reasons.insert(1, "MIXED OPTIONS DATA: Choppy / Sideways expiry expected.")

        if final_score > 0.4:
            reasons.insert(0, f"OPTIONS SENTIMENT: STRONG BULLISH (Score: +{final_score:.2f})")
        elif final_score < -0.4:
            reasons.insert(0, f"OPTIONS SENTIMENT: STRONG BEARISH (Score: {final_score:.2f})")
        else:
            reasons.insert(0, f"OPTIONS SENTIMENT: NEUTRAL / SIDEWAYS (Score: {final_score:.2f})")

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
