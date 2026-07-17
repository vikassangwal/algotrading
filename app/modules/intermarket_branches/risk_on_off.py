import logging

logger = logging.getLogger("elco.module.intermarket.risk")

class RiskOnOffEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            market_regime = self.data.get("risk_regime")
            if market_regime is not None:
                if market_regime == "Risk-On":
                    score += 0.3
                    reasons.append("Intermarket (Liquidity): Global Capital is in RISK-ON mode. Money is flowing into Equities and High-Beta assets.")
                elif market_regime == "Risk-Off":
                    score -= 0.4
                    reasons.append("Intermarket (Liquidity): Global Capital is in RISK-OFF mode! Panic flows into Safe Havens (Gold, Bonds). Avoid Equities.")

            small_cap_outperformance = self.data.get("small_cap_vs_large_cap")
            if small_cap_outperformance is not None:
                if small_cap_outperformance > 0.0:
                    score += 0.15
                    reasons.append("Intermarket (Risk Appetite): Small Caps are outperforming Large Caps. Indicates high risk appetite in the market.")
                elif small_cap_outperformance < -0.05:
                    score -= 0.15
                    reasons.append("Intermarket (Risk Appetite): Small Caps are crashing relative to Large Caps. Liquidity is drying up.")

            hy_spread_trend = self.data.get("high_yield_spread_trend")
            if hy_spread_trend is not None:
                if hy_spread_trend == "Widening":
                    score -= 0.2
                    reasons.append("Intermarket (Credit): High Yield (Junk) spreads are widening. Smart money is fleeing risky assets.")

        except Exception as e:
            logger.error(f"Error in RiskOnOffEngine: {e}")
            reasons.append("Risk-On/Off Engine: Error analyzing liquidity cycles.")

        return {
            "branch": "Risk-On / Risk-Off Regimes",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
