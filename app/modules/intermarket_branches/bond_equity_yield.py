import logging

logger = logging.getLogger("elco.module.intermarket.bond_equity")

class BondEquityYieldEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            us_10y_yield_trend = self.data.get("us_10y_yield_trend")
            us_10y_yield = self.data.get("us_10y_yield")
            
            if us_10y_yield_trend is not None and us_10y_yield is not None:
                if us_10y_yield_trend == "Rising" and us_10y_yield > 4.2:
                    score -= 0.3
                    reasons.append(f"Intermarket (Bonds): US 10Y Yield is Rising aggressively ({us_10y_yield:.2f}%). Negative for Emerging Market Equities.")
                elif us_10y_yield_trend == "Falling":
                    score += 0.2
                    reasons.append(f"Intermarket (Bonds): US 10Y Yield is Falling ({us_10y_yield:.2f}%). Capital flow supportive for Equities.")
            
            yield_curve_status = self.data.get("yield_curve_status")
            if yield_curve_status is not None:
                if yield_curve_status == "Inverted":
                    score -= 0.3
                    reasons.append("Intermarket (Bonds): Yield Curve is INVERTED (Short-term > Long-term rates). High Probability of Recession.")
                elif yield_curve_status == "Steepening":
                    score += 0.15
                    reasons.append("Intermarket (Bonds): Yield Curve is Steepening. Indicates economic recovery phase.")

            credit_spread_trend = self.data.get("credit_spread_trend")
            if credit_spread_trend is not None:
                if credit_spread_trend == "Widening":
                    score -= 0.2
                    reasons.append("Intermarket (Bonds): Corporate Credit Spreads are Widening. Bond market is pricing in default risk (Bearish).")
                elif credit_spread_trend == "Narrowing":
                    score += 0.15
                    reasons.append("Intermarket (Bonds): Corporate Credit Spreads are Narrowing. High confidence in corporate health (Bullish).")

        except Exception as e:
            logger.error(f"Error in BondEquityYieldEngine: {e}")
            reasons.append("Bond vs Equity Engine: Error analyzing yield data.")

        return {
            "branch": "Bond Market & Yield Curve Dynamics",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
