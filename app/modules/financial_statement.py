"""Financial Statement Analysis — income statement, balance sheet, cash flow health."""
import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.financial_statement")


class FinancialStatementModule(AnalysisModule):
    name = "financial_statement"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            f = self.provider.get_fundamentals(symbol) or {}
            reasons = []
            score = 0.0

            # --- Income statement: profitability ---
            revenue = float(f.get("revenue", 0) or 0)
            net_income = float(f.get("net_income", 0) or 0)
            op_income = float(f.get("operating_income", 0) or 0)
            if revenue > 0:
                net_margin = net_income / revenue
                op_margin = op_income / revenue
                if net_margin > 0.15:
                    score += 0.25; reasons.append(f"Strong net margin {net_margin*100:.1f}%")
                elif net_margin < 0.03:
                    score -= 0.2; reasons.append(f"Thin net margin {net_margin*100:.1f}%")
                reasons.append(f"Operating margin {op_margin*100:.1f}%")

            # --- Cash flow: free cash flow ---
            ocf = float(f.get("operating_cash_flow", 0) or 0)
            capex = float(f.get("capex", 0) or 0)
            fcf = ocf - capex
            if fcf > 0:
                score += 0.2; reasons.append(f"Positive free cash flow ({fcf:.0f})")
            else:
                score -= 0.25; reasons.append(f"Negative free cash flow ({fcf:.0f})")

            # --- Balance sheet: liquidity & quality scores ---
            ca = float(f.get("current_assets", 0) or 0)
            cl = float(f.get("current_liabilities", 0) or 0)
            if cl > 0:
                current_ratio = ca / cl
                if current_ratio >= 1.5:
                    score += 0.15; reasons.append(f"Healthy current ratio {current_ratio:.2f}")
                elif current_ratio < 1.0:
                    score -= 0.2; reasons.append(f"Weak current ratio {current_ratio:.2f}")

            piotroski = f.get("piotroski_f_score")
            if piotroski is not None:
                if piotroski >= 7:
                    score += 0.25; reasons.append(f"High Piotroski F-Score {piotroski}/9")
                elif piotroski <= 3:
                    score -= 0.25; reasons.append(f"Low Piotroski F-Score {piotroski}/9")

            altman = f.get("altman_z_score")
            if altman is not None:
                if altman >= 3.0:
                    score += 0.15; reasons.append(f"Safe Altman-Z {altman}")
                elif altman < 1.8:
                    score -= 0.3; reasons.append(f"Distress zone Altman-Z {altman}")

            beneish = f.get("beneish_m_score")
            if beneish is not None and beneish > -1.78:
                score -= 0.25; reasons.append(f"Beneish M-Score {beneish} flags possible manipulation")

            if not reasons:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient statement data."])

            confidence = 0.85 if len(reasons) >= 4 else 0.6
            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), confidence, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
