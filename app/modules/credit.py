"""Credit Analysis — debt-servicing ability and default risk."""
import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.credit")


class CreditModule(AnalysisModule):
    name = "credit"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            f = self.provider.get_fundamentals(symbol) or {}
            reasons = []
            score = 0.0

            # --- Leverage: debt / equity ---
            debt = float(f.get("total_debt", 0) or 0)
            equity = float(f.get("shareholder_equity", 0) or 0)
            if equity > 0:
                de = debt / equity
                if de < 0.5:
                    score += 0.3; reasons.append(f"Low leverage D/E {de:.2f}")
                elif de > 1.5:
                    score -= 0.35; reasons.append(f"High leverage D/E {de:.2f}")
                else:
                    reasons.append(f"Moderate D/E {de:.2f}")

            # --- Interest coverage proxy: EBIT vs debt burden ---
            ebit = float(f.get("ebit", 0) or 0)
            if debt > 0 and ebit:
                cover = ebit / (debt * 0.09)  # assume ~9% avg interest
                if cover > 4:
                    score += 0.25; reasons.append(f"Strong interest coverage ~{cover:.1f}x")
                elif cover < 1.5:
                    score -= 0.3; reasons.append(f"Weak interest coverage ~{cover:.1f}x")

            # --- Cash flow vs debt ---
            ocf = float(f.get("operating_cash_flow", 0) or 0)
            if debt > 0 and ocf:
                ocf_debt = ocf / debt
                if ocf_debt > 0.4:
                    score += 0.2; reasons.append(f"Healthy OCF/Debt {ocf_debt:.2f}")
                elif ocf_debt < 0.1:
                    score -= 0.2; reasons.append(f"Thin OCF/Debt {ocf_debt:.2f}")

            # --- Distress score ---
            altman = f.get("altman_z_score")
            if altman is not None:
                if altman >= 3.0:
                    score += 0.2; reasons.append(f"Safe Altman-Z {altman}")
                elif altman < 1.8:
                    score -= 0.35; reasons.append(f"Distress zone Altman-Z {altman}")

            # --- Macro rate environment ---
            macro = self.provider.get_macro_data() or {}
            rate = macro.get("india_10y_yield") or macro.get("macro_interest_rate")
            if rate and float(rate) > 7.5:
                score -= 0.05; reasons.append(f"Elevated rates ({rate}%) raise refinancing cost")

            if not reasons:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient credit data."])

            confidence = 0.8 if len(reasons) >= 3 else 0.55
            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), confidence, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
