import logging

logger = logging.getLogger("elco.module.derivatives.volatility")

class VolatilityGreeksEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            ivr = self.data.get("iv_rank")
            if ivr is not None:
                if ivr > 80:
                    reasons.append(f"Volatility: IV Rank is very high ({ivr}). Option premiums are expensive. Favorable for Option Writers (Credit Spreads).")
                elif ivr < 20:
                    reasons.append(f"Volatility: IV Rank is very low ({ivr}). Option premiums are cheap. Favorable for Option Buyers (Long Straddles).")

            put_iv = self.data.get("atm_put_iv")
            call_iv = self.data.get("atm_call_iv")
            
            if put_iv is not None and call_iv is not None:
                skew = put_iv - call_iv
                if skew > 5.0:
                    score -= 0.15
                    reasons.append("Volatility Skew: Put IV is significantly higher than Call IV. Market is paying a high premium for downside protection (Fear).")
                elif skew < -1.0:
                    score += 0.15
                    reasons.append("Volatility Skew: Call IV is higher than Put IV. Market is aggressively pricing in upside calls (Greed).")

            gex = self.data.get("gamma_exposure")
            if gex is not None:
                if gex == "Negative":
                    reasons.append("Greeks (GEX): Dealers are in NEGATIVE Gamma. Expect high volatility and extended directional moves (Breakouts will sustain).")
                elif gex == "Positive":
                    reasons.append("Greeks (GEX): Dealers are in POSITIVE Gamma. Expect mean-reverting, low volatility, choppy market.")

        except Exception as e:
            logger.error(f"Error in VolatilityGreeksEngine: {e}")
            reasons.append("Volatility & Greeks Engine: Error analyzing complex math data.")

        return {
            "branch": "Implied Volatility & Greeks (GEX)",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
