"""Smart Money Analysis — follow FII/DII, promoters, and commercial positioning."""
import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.smart_money")


class SmartMoneyModule(AnalysisModule):
    name = "smart_money"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            f = self.provider.get_fundamentals(symbol) or {}
            sent = self.provider.get_sentiment_data(symbol) or {}
            deriv = self.provider.get_derivatives_data(symbol) or {}
            reasons = []
            score = 0.0

            # --- FII / DII holding changes ---
            fii = f.get("fii_holding_change_qoy")
            dii = f.get("dii_holding_change_qoy")
            if fii is not None:
                if float(fii) > 0:
                    score += 0.25; reasons.append(f"FII accumulating (+{float(fii)*100:.1f}% QoQ)")
                else:
                    score -= 0.2; reasons.append(f"FII reducing ({float(fii)*100:.1f}% QoQ)")
            if dii is not None:
                if float(dii) > 0:
                    score += 0.15; reasons.append(f"DII accumulating (+{float(dii)*100:.1f}% QoQ)")
                else:
                    score -= 0.1; reasons.append(f"DII reducing ({float(dii)*100:.1f}% QoQ)")

            # --- Promoter pledge (red flag) ---
            pledge = f.get("promoter_pledge_pct")
            if pledge is not None:
                if float(pledge) > 0.25:
                    score -= 0.25; reasons.append(f"High promoter pledge ({float(pledge)*100:.0f}%)")
                elif float(pledge) < 0.05:
                    score += 0.1; reasons.append("Negligible promoter pledge")

            # --- Commercial (smart) positioning via COT ---
            if sent.get("cot_commercial_net_short") is True:
                score -= 0.15; reasons.append("Commercials net short (smart money cautious)")

            # --- Institutional block ratio ---
            block = sent.get("institutional_block_ratio")
            if block is not None and float(block) > 1.5:
                score += 0.15; reasons.append(f"Elevated institutional blocks ({block})")

            # --- FII derivatives bias ---
            fii_bias = str(deriv.get("fii_index_futures_bias", "")).lower()
            if "bull" in fii_bias:
                score += 0.1; reasons.append("FII derivatives bias bullish")
            elif "bear" in fii_bias:
                score -= 0.1; reasons.append("FII derivatives bias bearish")

            if not reasons:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient smart-money data."])
            confidence = 0.8 if (fii is not None or dii is not None) else 0.55
            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), confidence, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
