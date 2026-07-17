import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.ratio")

class RatioModule(AnalysisModule):
    name = "ratio"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            fund = self.provider.get_fundamentals(symbol) or {}
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch fundamental data."])

        # Support both dict-shaped providers and dataclass Fundamentals.
        def g(key, attr, default=0.0):
            if isinstance(fund, dict):
                return fund.get(key, default)
            return getattr(fund, attr, default)

        pe = float(g("pe_ratio", "pe", 0.0))
        pb = float(g("pb_ratio", "pb", 0.0))
        debt = float(g("total_debt", "total_debt", 0.0))
        equity = float(g("shareholder_equity", "shareholder_equity", 0.0))
        de = float(g("debt_to_equity", "debt_to_equity", (debt / equity) if equity else 0.0))

        score = 0.0
        reasons = []

        # Analyze Price to Earnings (P/E)
        if 0 < pe < 10:
            score += 0.4
            reasons.append(f"Undervalued P/E ({pe}). Stock is cheap relative to earnings.")
        elif pe > 40:
            score -= 0.4
            reasons.append(f"Overvalued P/E ({pe}). Priced for perfection.")
        elif pe > 0:
            reasons.append(f"Fair P/E ({pe}).")

        # Analyze Price to Book (P/B)
        if 0 < pb < 1.0:
            score += 0.4
            reasons.append(f"Undervalued P/B ({pb}). Trading below book value.")
        elif pb > 5.0:
            score -= 0.3
            reasons.append(f"High P/B ({pb}). Expensive relative to book value.")

        # Analyze Debt to Equity
        if de > 2.0:
            score -= 0.3
            reasons.append(f"High Debt/Equity ({de:.2f}). Highly leveraged risk.")
        elif 0 <= de < 0.5:
            score += 0.2
            reasons.append(f"Low Debt/Equity ({de:.2f}). Healthy balance sheet.")

        if not reasons:
            reasons.append("Ratios within normal range.")

        score = max(-1.0, min(1.0, score))
        confidence = 0.8

        return ModuleSignal(
            module=self.name,
            score=score,
            confidence=confidence,
            reasons=reasons
        )
