import logging

logger = logging.getLogger("elco.module.derivatives.futures")

class FuturesRolloverEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            price_change = self.data.get("futures_price_change_pct")
            oi_change = self.data.get("futures_oi_change_pct")
            
            if price_change is not None and oi_change is not None:
                if price_change > 0 and oi_change > 0:
                    score += 0.3
                    reasons.append(f"Futures Analysis: LONG BUILD-UP detected (Price {price_change:.1f}%, OI {oi_change:.1f}%). Strong Bullish Conviction.")
                elif price_change < 0 and oi_change > 0:
                    score -= 0.3
                    reasons.append(f"Futures Analysis: SHORT BUILD-UP detected (Price {price_change:.1f}%, OI {oi_change:.1f}%). Strong Bearish Conviction.")
                elif price_change > 0 and oi_change < 0:
                    score += 0.1
                    reasons.append(f"Futures Analysis: SHORT COVERING detected. Bears are booking losses. (Short-term Bullish)")
                elif price_change < 0 and oi_change < 0:
                    score -= 0.1
                    reasons.append(f"Futures Analysis: LONG UNWINDING detected. Bulls are booking profits. (Short-term Bearish)")

            rollover_pct = self.data.get("futures_rollover_pct")
            historical_rollover = self.data.get("historical_rollover_avg_pct")
            coc_trend = self.data.get("cost_of_carry_trend")
            
            if rollover_pct is not None and historical_rollover is not None and coc_trend is not None:
                if rollover_pct > historical_rollover:
                    if coc_trend == "Increasing":
                        score += 0.15
                        reasons.append(f"Rollover Analysis: Strong Long Rollovers ({rollover_pct*100:.1f}% vs Avg {historical_rollover*100:.1f}%). Cost of Carry is increasing.")
                    else:
                        score -= 0.15
                        reasons.append(f"Rollover Analysis: Strong Short Rollovers ({rollover_pct*100:.1f}% vs Avg {historical_rollover*100:.1f}%). Cost of Carry is decreasing.")

        except Exception as e:
            logger.error(f"Error in FuturesRolloverEngine: {e}")
            reasons.append("Futures Analysis Engine: Error analyzing OI or Rollover data.")

        return {
            "branch": "Futures & Rollover Analysis",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
