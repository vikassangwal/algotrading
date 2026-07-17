import logging

logger = logging.getLogger("elco.module.macro.policy")

class PolicyLiquidityEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. RBI Monetary Policy Bias
            policy_bias = self.data.get("rbi_policy_bias")
            if policy_bias is not None:
                if policy_bias == "Dovish":
                    score += 0.2
                    reasons.append("Policy & Liquidity: Central Bank is Dovish (Rate cuts / Easing). Highly positive for equities.")
                elif policy_bias == "Hawkish":
                    score -= 0.2
                    reasons.append("Policy & Liquidity: Central Bank is Hawkish (Rate hikes / Tightening). Negative for equities.")
                else:
                    reasons.append("Policy & Liquidity: Central Bank stance is Neutral.")
            else:
                reasons.append("Policy & Liquidity: Central Bank stance data is unavailable.")

            # 2. Yield Curve Inversion (India 10Y vs 2Y)
            yield_10y = self.data.get("india_10y_yield")
            yield_2y = self.data.get("india_2y_yield")
            
            if yield_10y is not None and yield_2y is not None:
                if yield_2y > yield_10y:
                    score -= 0.3
                    reasons.append(f"Policy & Liquidity: Yield Curve INVERSION detected (2Y: {yield_2y:.2f}% > 10Y: {yield_10y:.2f}%). Major Recession warning!")
                else:
                    score += 0.1
                    reasons.append(f"Policy & Liquidity: Normal Yield Curve (10Y: {yield_10y:.2f}% > 2Y: {yield_2y:.2f}%). Healthy credit market.")
            elif yield_10y is not None:
                reasons.append(f"Policy & Liquidity: 10Y Yield is {yield_10y:.2f}%. 2Y Yield data missing to check inversion.")
            else:
                reasons.append("Policy & Liquidity: Yield data is unavailable.")

            # 3. Fiscal Deficit / Government Spending
            fiscal_deficit_pct = self.data.get("fiscal_deficit_to_gdp")
            if fiscal_deficit_pct is not None:
                if fiscal_deficit_pct > 6.5:
                    score -= 0.15
                    reasons.append(f"Policy & Liquidity: Fiscal Deficit is high ({fiscal_deficit_pct}%). Sovereign risk rising.")
                elif fiscal_deficit_pct <= 5.9:
                    score += 0.15
                    reasons.append(f"Policy & Liquidity: Fiscal Deficit is controlled ({fiscal_deficit_pct}%). Strong macro management.")
                else:
                    reasons.append(f"Policy & Liquidity: Fiscal Deficit is moderate ({fiscal_deficit_pct}%).")
            else:
                reasons.append("Policy & Liquidity: Fiscal Deficit data is unavailable.")

        except Exception as e:
            logger.error(f"Error in PolicyLiquidityEngine: {e}")
            reasons.append("Policy/Liquidity Engine: Error analyzing central bank data.")

        return {
            "branch": "Policy & System Liquidity",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
