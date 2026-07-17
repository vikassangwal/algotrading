import logging

logger = logging.getLogger("elco.module.options.maxpain")

class MaxPainEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            current_price = self.data.get("spot_price")
            max_pain_strike = self.data.get("max_pain_strike")
            dte = self.data.get("days_to_expiry")
            
            if current_price is not None and max_pain_strike is not None and dte is not None:
                diff_pct = (current_price - max_pain_strike) / current_price
                
                if dte <= 2:
                    if diff_pct > 0.01:
                        score -= 0.3
                        reasons.append(f"Max Pain: Price ({current_price}) is too far above Max Pain ({max_pain_strike}). Expiry magnet effect pulling it DOWN.")
                    elif diff_pct < -0.01:
                        score += 0.3
                        reasons.append(f"Max Pain: Price ({current_price}) is too far below Max Pain ({max_pain_strike}). Expiry magnet effect pulling it UP.")
                    else:
                        reasons.append(f"Max Pain: Price is pinned near Max Pain ({max_pain_strike}). Expect sideways chop.")
                else:
                    reasons.append(f"Max Pain: Current Max Pain is at {max_pain_strike} ({dte} days to expiry, pinning effect weak).")

            highest_ce_oi_strike = self.data.get("highest_ce_oi_strike")
            highest_pe_oi_strike = self.data.get("highest_pe_oi_strike")
            
            if current_price is not None:
                if highest_ce_oi_strike is not None and current_price >= highest_ce_oi_strike * 0.995:
                    score -= 0.2
                    reasons.append(f"Options OI: Price approaching massive Call Writing resistance at {highest_ce_oi_strike}.")
                elif highest_pe_oi_strike is not None and current_price <= highest_pe_oi_strike * 1.005:
                    score += 0.2
                    reasons.append(f"Options OI: Price approaching massive Put Writing support at {highest_pe_oi_strike}.")

        except Exception as e:
            logger.error(f"Error in MaxPainEngine: {e}")
            reasons.append("Max Pain Engine: Error calculating Max Pain dynamics.")

        return {
            "branch": "Max Pain & Expiry Pinning",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
