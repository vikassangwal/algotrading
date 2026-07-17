import logging

logger = logging.getLogger("elco.module.intermarket.correlation")

class CrossAssetCorrelationEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            eq_yield_corr = self.data.get("equity_bond_yield_correlation")
            if eq_yield_corr is not None:
                if eq_yield_corr < -0.5:
                    score += 0.1
                    reasons.append("Intermarket (Correlation): Equity and Bond Yields show strong inverse correlation (Normal market functioning).")
                elif eq_yield_corr > 0.5:
                    score -= 0.15
                    reasons.append("Intermarket (Correlation): Anomaly detected! Equities and Yields are moving together. Watch for sudden regime shifts.")

            usd_em_corr = self.data.get("usd_em_correlation")
            if usd_em_corr is not None:
                if usd_em_corr < -0.6:
                    reasons.append("Intermarket (Correlation): DXY and Emerging Markets maintaining normal inverse correlation.")
                elif usd_em_corr > 0:
                    score -= 0.2
                    reasons.append("Intermarket (Correlation): DXY and EM moving together. Highly anomalous structural break in the market!")

            recommended_allocation = self.data.get("recommended_allocation_asset")
            if recommended_allocation is not None:
                if recommended_allocation == "Equity":
                    score += 0.25
                    reasons.append("Intermarket (Allocation): Cross-Asset models recommend overweighting EQUITIES.")
                elif recommended_allocation in ["Bonds", "Cash", "Gold"]:
                    score -= 0.3
                    reasons.append(f"Intermarket (Allocation): Cross-Asset models recommend fleeing to {recommended_allocation}. Extreme caution for Equities.")

        except Exception as e:
            logger.error(f"Error in CrossAssetCorrelationEngine: {e}")
            reasons.append("Cross-Asset Engine: Error calculating correlation matrix.")

        return {
            "branch": "Cross-Asset Correlation Matrix",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
