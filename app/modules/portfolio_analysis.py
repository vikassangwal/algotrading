"""Portfolio-fit Analysis — does adding this symbol improve the book?"""
import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.portfolio_analysis")


class PortfolioAnalysisModule(AnalysisModule):
    name = "portfolio_analysis"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            p = self.provider.get_portfolio_data() or {}
            reasons = []
            score = 0.0

            # --- Sector concentration headroom ---
            cur = p.get("current_sector_exposure")
            limit = p.get("max_sector_weight_limit")
            if cur is not None and limit is not None:
                cur, limit = float(cur), float(limit)
                room = limit - cur
                if room > 0.05:
                    score += 0.25; reasons.append(f"Room under sector limit ({cur*100:.0f}% vs {limit*100:.0f}%)")
                elif room <= 0:
                    score -= 0.3; reasons.append(f"Sector already at/over limit ({cur*100:.0f}%)")
                else:
                    reasons.append(f"Limited sector room ({cur*100:.0f}% of {limit*100:.0f}%)")

            # --- Correlation / diversification ---
            corr = p.get("avg_correlation")
            if corr is not None:
                c = float(corr)
                if c < 0.4:
                    score += 0.25; reasons.append(f"Low avg correlation ({c:.2f}) — good diversifier")
                elif c > 0.7:
                    score -= 0.25; reasons.append(f"High avg correlation ({c:.2f}) — adds little diversification")
                else:
                    reasons.append(f"Moderate correlation ({c:.2f})")

            # --- Portfolio beta ---
            beta = p.get("current_portfolio_beta")
            if beta is not None:
                b = float(beta)
                if b > 1.3:
                    score -= 0.1; reasons.append(f"Book beta high ({b:.2f}) — prefer defensive adds")
                elif b < 0.8:
                    score += 0.1; reasons.append(f"Book beta low ({b:.2f}) — room for growth adds")

            # --- Cash available ---
            cash = p.get("cash_reserves")
            if cash is not None and float(cash) > 0:
                reasons.append(f"Deployable cash reserves ({float(cash):,.0f})")
            elif cash is not None:
                score -= 0.15; reasons.append("No cash reserves to deploy")

            if not reasons:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient portfolio data."])
            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), 0.65, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
