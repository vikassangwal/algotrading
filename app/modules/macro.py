import logging
import os
from .base import AnalysisModule, ModuleSignal

# Import the Macro sub-engines
from .macro_branches.economic_indicators import EconomicIndicatorsEngine
from .macro_branches.policy_liquidity import PolicyLiquidityEngine
from .macro_branches.global_cross_asset import GlobalCrossAssetEngine
from .macro_branches.business_cycle import BusinessCycleEngine

logger = logging.getLogger("elco.module.macro.master")

# Live macro fetches over yfinance are OFF by default: they add 5+ blocking
# network calls per analysis (slow) and can crash native libs on some Python
# builds. Set ELCO_LIVE_MACRO=true to opt in.
_LIVE_MACRO = os.getenv("ELCO_LIVE_MACRO", "false").strip().lower() == "true"


class MacroModule(AnalysisModule):
    name = "macro"

    def _fetch_real_macro_data(self) -> dict:
        """Live market macro via yfinance — only when ELCO_LIVE_MACRO=true."""
        if not _LIVE_MACRO:
            return {}
        real_data = {}
        try:
            import yfinance as yf
            for key, tkr, period in [
                ("brent_crude_usd", "BZ=F", "5d"),
                ("dxy_index", "DX-Y.NYB", "5d"),
                ("us_10y_yield", "^TNX", "5d"),
            ]:
                hist = yf.Ticker(tkr).history(period=period)
                if not hist.empty:
                    real_data[key] = float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.warning(f"Error fetching yfinance macro data: {e}")
        return real_data

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []

        try:
            # Base macro from the data provider (always available, no network),
            # optionally enriched with live market data.
            raw_data = {}
            try:
                raw_data = self.provider.get_macro_data() or {}
            except Exception:
                raw_data = {}
            raw_data.update(self._fetch_real_macro_data())
        except Exception as e:
            logger.error(f"Failed to fetch macro data: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch macro data."])
        
        reasons.append("--- MASTER 18-LEVEL MACRO-ECONOMIC ENGINE INITIALIZED ---")

        total_score = 0.0
        
        # ==========================================
        # ENGINE 1: Economic Indicators
        # ==========================================
        econ_engine = EconomicIndicatorsEngine(raw_data)
        econ_res = econ_engine.analyze()
        total_score += econ_res['score']
        reasons.extend(econ_res['reasons'])

        # ==========================================
        # ENGINE 2: Policy & Liquidity
        # ==========================================
        policy_engine = PolicyLiquidityEngine(raw_data)
        policy_res = policy_engine.analyze()
        total_score += policy_res['score']
        reasons.extend(policy_res['reasons'])

        # ==========================================
        # ENGINE 3: Global Macro & Cross Asset
        # ==========================================
        global_engine = GlobalCrossAssetEngine(raw_data)
        global_res = global_engine.analyze()
        total_score += global_res['score']
        reasons.extend(global_res['reasons'])

        # ==========================================
        # ENGINE 4: Business Cycle
        # ==========================================
        cycle_engine = BusinessCycleEngine(raw_data)
        cycle_res = cycle_engine.analyze()
        total_score += cycle_res['score']
        reasons.extend(cycle_res['reasons'])

        # ==========================================
        # MASTER MACRO AGGREGATION
        # ==========================================
        final_score = total_score / 4.0
        
        engine_scores = [econ_res['score'], policy_res['score'], global_res['score'], cycle_res['score']]
        bulls = sum(1 for s in engine_scores if s > 0.1)
        bears = sum(1 for s in engine_scores if s < -0.1)
        
        if bulls >= 3:
            confidence = 0.95
            reasons.insert(1, "MACRO CONFLUENCE: Deep structural tailwinds for the Indian Economy.")
        elif bears >= 3:
            confidence = 0.95
            reasons.insert(1, "MACRO DIVERGENCE: Severe structural headwinds. Capital preservation prioritized.")
        else:
            confidence = 0.50
            reasons.insert(1, "MACRO MIXED: Economy is in a transitional phase. Stock-specific (Alpha) action expected.")

        if final_score > 0.4:
            reasons.insert(0, f"MACRO REGIME: STRONG EXPANSION / RISK-ON (Score: +{final_score:.2f})")
        elif final_score < -0.4:
            reasons.insert(0, f"MACRO REGIME: RECESSIONARY / RISK-OFF (Score: {final_score:.2f})")
        else:
            reasons.insert(0, f"MACRO REGIME: NEUTRAL / SLOWDOWN (Score: {final_score:.2f})")

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
