"""Order Flow Analysis — institutional/dark-pool flow and dealer positioning."""
import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.order_flow")


class OrderFlowModule(AnalysisModule):
    name = "order_flow"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            sent = self.provider.get_sentiment_data(symbol) or {}
            deriv = self.provider.get_derivatives_data(symbol) or {}
            reasons = []
            score = 0.0

            # --- Dark pool buy vs sell ---
            dp_buy = float(sent.get("dark_pool_buy_volume", 0) or 0)
            dp_sell = float(sent.get("dark_pool_sell_volume", 0) or 0)
            if dp_buy + dp_sell > 0:
                imb = (dp_buy - dp_sell) / (dp_buy + dp_sell)
                if imb > 0.2:
                    score += 0.3; reasons.append(f"Dark-pool net buying (imbalance {imb:+.2f})")
                elif imb < -0.2:
                    score -= 0.3; reasons.append(f"Dark-pool net selling (imbalance {imb:+.2f})")
                else:
                    reasons.append(f"Balanced dark-pool flow ({imb:+.2f})")

            # --- Institutional block ratio ---
            block = sent.get("institutional_block_ratio")
            if block is not None:
                if float(block) > 2.0:
                    score += 0.2; reasons.append(f"Heavy institutional block activity ({block})")
                elif float(block) < 0.5:
                    score -= 0.15; reasons.append(f"Weak institutional participation ({block})")

            # --- FII index futures bias ---
            fii_bias = str(deriv.get("fii_index_futures_bias", "")).lower()
            if "bull" in fii_bias:
                score += 0.2; reasons.append("FII index-futures bias bullish")
            elif "bear" in fii_bias:
                score -= 0.2; reasons.append("FII index-futures bias bearish")

            # --- Option writing pressure ---
            cw = float(deriv.get("call_writing_strength", 0) or 0)
            pw = float(deriv.get("put_writing_strength", 0) or 0)
            if pw > cw * 1.2:
                score += 0.15; reasons.append("Put writing dominant (support building)")
            elif cw > pw * 1.2:
                score -= 0.15; reasons.append("Call writing dominant (resistance building)")

            # --- Dealer gamma exposure ---
            gex = deriv.get("dealer_gex")
            if gex is not None and float(gex) < 0:
                reasons.append(f"Negative dealer GEX ({gex}) — volatility amplifying")

            if not reasons:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient order-flow data."])
            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), 0.7, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
