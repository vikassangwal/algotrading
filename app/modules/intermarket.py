import logging
import os
from .base import AnalysisModule, ModuleSignal

# Import the Intermarket sub-engines
from .intermarket_branches.bond_equity_yield import BondEquityYieldEngine
from .intermarket_branches.currency_commodity import CurrencyCommodityEngine
from .intermarket_branches.risk_on_off import RiskOnOffEngine
from .intermarket_branches.cross_asset_correlation import CrossAssetCorrelationEngine

logger = logging.getLogger("elco.module.intermarket.master")

# Live cross-asset fetches over yfinance are OFF by default (network + native
# lib crash risk). Set ELCO_LIVE_MACRO=true to opt in.
_LIVE_MACRO = os.getenv("ELCO_LIVE_MACRO", "false").strip().lower() == "true"


class IntermarketModule(AnalysisModule):
    name = "intermarket"

    def _fetch_real_intermarket_data(self) -> dict:
        if not _LIVE_MACRO:
            return {}
        real_data = {}
        try:
            import yfinance as yf
            for key, tkr in [("us_10y_yield_series", "^TNX"), ("dxy", "DX-Y.NYB"),
                             ("gold", "GC=F"), ("crude", "BZ=F")]:
                hist = yf.Ticker(tkr).history(period="1mo")
                if not hist.empty and len(hist) > 10:
                    short_ma = hist['Close'].tail(5).mean()
                    long_ma = hist['Close'].tail(20).mean()
                    real_data[f"{key}_trend"] = "Rising" if short_ma > long_ma else "Falling"
        except Exception as e:
            logger.warning(f"Error fetching yfinance intermarket data: {e}")
        return real_data

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []

        try:
            raw_data = {}
            try:
                raw_data = self.provider.get_intermarket_data() or {}
            except Exception:
                raw_data = {}
            raw_data.update(self._fetch_real_intermarket_data())
        except Exception as e:
            logger.error(f"Failed to fetch intermarket data: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch intermarket data."])
        
        reasons.append("--- MASTER 10-LEVEL INTERMARKET (CROSS-ASSET) ENGINE INITIALIZED ---")

        total_score = 0.0
        
        # ==========================================
        # ENGINE 1: Bond vs Equity Dynamics
        # ==========================================
        bond_engine = BondEquityYieldEngine(raw_data)
        bond_res = bond_engine.analyze()
        total_score += bond_res['score']
        reasons.extend(bond_res['reasons'])

        # ==========================================
        # ENGINE 2: Currency & Commodity Nexus
        # ==========================================
        cc_engine = CurrencyCommodityEngine(raw_data)
        cc_res = cc_engine.analyze()
        total_score += cc_res['score']
        reasons.extend(cc_res['reasons'])

        # ==========================================
        # ENGINE 3: Risk-On / Risk-Off Regimes
        # ==========================================
        risk_engine = RiskOnOffEngine(raw_data)
        risk_res = risk_engine.analyze()
        total_score += risk_res['score']
        reasons.extend(risk_res['reasons'])

        # ==========================================
        # ENGINE 4: Cross-Asset Correlation
        # ==========================================
        corr_engine = CrossAssetCorrelationEngine(raw_data)
        corr_res = corr_engine.analyze()
        total_score += corr_res['score']
        reasons.extend(corr_res['reasons'])

        # ==========================================
        # MASTER INTERMARKET AGGREGATION
        # ==========================================
        final_score = total_score / 4.0
        
        # Confidence logic based on Global Capital flows
        if raw_data.get("risk_regime") == "Risk-On" and raw_data.get("dxy_trend") == "Falling":
            confidence = 0.95
            reasons.insert(1, "GLOBAL CAPITAL CONFLUENCE: Risk-On environment with Weak Dollar. Extreme tailwind for Indian Equities.")
        elif raw_data.get("risk_regime") == "Risk-Off" and raw_data.get("dxy_trend") == "Rising":
            confidence = 0.95
            reasons.insert(1, "GLOBAL CAPITAL DIVERGENCE: Risk-Off environment with Strong Dollar. Extreme headwind for Indian Equities (Capital Flight).")
        else:
            confidence = 0.60
            reasons.insert(1, "INTERMARKET MIXED: Capital flows are rotating without a clear directional bias.")

        if final_score > 0.4:
            reasons.insert(0, f"INTERMARKET OUTLOOK: MASSIVE LIQUIDITY INFLOW (Score: +{final_score:.2f})")
        elif final_score < -0.4:
            reasons.insert(0, f"INTERMARKET OUTLOOK: SEVERE CAPITAL FLIGHT (Score: {final_score:.2f})")
        else:
            reasons.insert(0, f"INTERMARKET OUTLOOK: NEUTRAL FLOWS (Score: {final_score:.2f})")

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
