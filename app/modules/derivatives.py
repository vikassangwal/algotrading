import logging
from .base import AnalysisModule, ModuleSignal

# Import the Advanced Derivatives sub-engines
from .derivatives_branches.futures_rollover import FuturesRolloverEngine
from .derivatives_branches.options_chain import OptionsChainEngine
from .derivatives_branches.institutional_positioning import InstitutionalPositioningEngine
from .derivatives_branches.volatility_greeks import VolatilityGreeksEngine

logger = logging.getLogger("elco.module.derivatives.master")

class DerivativesModule(AnalysisModule):
    name = "derivatives"

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []
        
        try:
            # Note: yfinance doesn't natively support options/futures for Indian markets easily
            # Assuming provider has this data or we fall back gracefully.
            raw_data = {}
            if hasattr(self.provider, 'get_derivatives_data'):
                raw_data = self.provider.get_derivatives_data(symbol) or {}
        except Exception as e:
            logger.error(f"Failed to fetch derivatives data for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch derivatives data."])
        
        reasons.append("--- MASTER 18-LEVEL DERIVATIVES (F&O) ENGINE INITIALIZED ---")

        total_score = 0.0
        
        # ==========================================
        # ENGINE 1: Futures & Rollover Analysis
        # ==========================================
        fut_engine = FuturesRolloverEngine(raw_data)
        fut_res = fut_engine.analyze()
        total_score += fut_res['score']
        reasons.extend(fut_res['reasons'])

        # ==========================================
        # ENGINE 2: Options Chain Analysis
        # ==========================================
        current_price = None
        if hasattr(self.provider, 'get_quote'):
            try:
                current_price = self.provider.get_quote(symbol).ltp
            except:
                pass
        if current_price is not None:
            raw_data["spot_price"] = current_price
            
        opt_engine = OptionsChainEngine(raw_data)
        opt_res = opt_engine.analyze()
        total_score += opt_res['score']
        reasons.extend(opt_res['reasons'])

        # ==========================================
        # ENGINE 3: Institutional F&O Positioning
        # ==========================================
        inst_engine = InstitutionalPositioningEngine(raw_data)
        inst_res = inst_engine.analyze()
        total_score += inst_res['score']
        reasons.extend(inst_res['reasons'])

        # ==========================================
        # ENGINE 4: Volatility & Greeks
        # ==========================================
        vol_engine = VolatilityGreeksEngine(raw_data)
        vol_res = vol_engine.analyze()
        total_score += vol_res['score']
        reasons.extend(vol_res['reasons'])

        # ==========================================
        # MASTER DERIVATIVES AGGREGATION
        # ==========================================
        final_score = total_score / 4.0
        
        # Confidence logic based on Institutional Trap detection
        client_bias = raw_data.get("client_options_bias")
        fii_bias = raw_data.get("fii_options_bias")
        
        confidence = 0.50
        if client_bias is not None and fii_bias is not None:
            if client_bias != fii_bias:
                confidence = 0.95
                reasons.insert(1, "SMART MONEY TRAP CONFIRMED: FIIs and Retail are positioned in opposite directions. Edge is extreme.")
            else:
                confidence = 0.60
                reasons.insert(1, "DERIVATIVES ALIGNED: FIIs and Retail are moving together. Standard market flow.")

        if final_score > 0.4:
            reasons.insert(0, f"DERIVATIVES OUTLOOK: STRONG BULLISH TRAP / SQUEEZE (Score: +{final_score:.2f})")
        elif final_score < -0.4:
            reasons.insert(0, f"DERIVATIVES OUTLOOK: STRONG BEARISH TRAP / LIQUIDATION (Score: {final_score:.2f})")
        else:
            reasons.insert(0, f"DERIVATIVES OUTLOOK: NEUTRAL / CHOPPY (Score: {final_score:.2f})")

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
