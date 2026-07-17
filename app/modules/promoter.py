import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.promoter")

class PromoterModule(AnalysisModule):
    name = "promoter"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            fund = self.provider.get_fundamentals(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch fundamental data."])

        score = 0.0
        reasons = []

        # Analyze Promoter Holding
        if fund.promoter_holding_pct > 50:
            score += 0.5
            reasons.append(f"High Promoter Holding ({fund.promoter_holding_pct}%). Shows strong 'skin in the game'.")
        elif fund.promoter_holding_pct < 20:
            score -= 0.5
            reasons.append(f"Low Promoter Holding ({fund.promoter_holding_pct}%). Warning sign.")

        # Analyze Promoter Pledge
        if fund.promoter_pledge_pct > 25:
            score -= 0.8
            reasons.append(f"CRITICAL: High Promoter Pledge ({fund.promoter_pledge_pct}%). Severe risk of margin call dump.")
        elif fund.promoter_pledge_pct > 5:
            score -= 0.4
            reasons.append(f"Warning: Promoter Pledge at {fund.promoter_pledge_pct}%.")
        elif fund.promoter_pledge_pct == 0:
            score += 0.2
            reasons.append("Zero pledged shares. Clean holding structure.")

        score = max(-1.0, min(1.0, score))
        confidence = 0.9

        return ModuleSignal(
            module=self.name,
            score=score,
            confidence=confidence,
            reasons=reasons
        )
