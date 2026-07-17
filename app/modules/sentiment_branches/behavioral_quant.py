import logging

logger = logging.getLogger("elco.module.sentiment.behavioral")

class BehavioralQuantEngine:
    """
    Handles Behavioral Finance (Fear/Greed) and Quantitative Volatility Sentiment.
    """
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. Fear & Greed Index
            fg_index = self.data.get("fear_greed_index")
            if fg_index is not None:
                if fg_index > 80:
                    score -= 0.25
                    reasons.append(f"Behavioral (Fear/Greed): Index at {fg_index} (Extreme Greed / FOMO). Contrarian Bearish.")
                elif fg_index < 20:
                    score += 0.25
                    reasons.append(f"Behavioral (Fear/Greed): Index at {fg_index} (Extreme Fear / Panic). Contrarian Bullish.")
            else:
                reasons.append("Behavioral (Fear/Greed): Index data unavailable.")

            # 2. VIX Term Structure
            vix_front = self.data.get("vix_front_month")
            vix_next = self.data.get("vix_next_month")
            
            if vix_front is not None and vix_next is not None:
                if vix_front > vix_next * 1.05: # Backwardation
                    score -= 0.3
                    reasons.append(f"Volatility Sentiment: VIX Term Structure in BACKWARDATION ({vix_front} > {vix_next}). Severe market panic.")
                elif vix_front < vix_next * 0.95: # Healthy Contango
                    score += 0.1
                    reasons.append(f"Volatility Sentiment: VIX Term Structure in healthy Contango ({vix_front} < {vix_next}). Normal risk environment.")
            else:
                reasons.append("Volatility Sentiment: VIX Term Structure data unavailable.")

            # 3. Volatility Skew
            put_skew = self.data.get("put_call_skew_ratio")
            if put_skew is not None:
                if put_skew > 1.3:
                    score -= 0.15
                    reasons.append(f"Volatility Sentiment: Put Skew is extremely high ({put_skew:.2f}). Heavy downside protection buying.")
                elif put_skew < 0.8:
                    score += 0.15
                    reasons.append(f"Volatility Sentiment: Call Skew is elevated ({put_skew:.2f}). Aggressive upside convexity buying.")
            else:
                reasons.append("Volatility Sentiment: Put/Call skew data unavailable.")

            # 4. Regional Volatility (India VIX / CBOE VIX)
            india_vix = self.data.get("india_vix")
            cboe_vix = self.data.get("cboe_vix")
            
            if india_vix is not None:
                if india_vix > 25:
                    score -= 0.2
                    reasons.append(f"Regional Volatility: India VIX is critically high ({india_vix:.1f}). Extreme fear in Indian Markets.")
                elif india_vix < 13:
                    score += 0.1
                    reasons.append(f"Regional Volatility: India VIX is very low ({india_vix:.1f}). High complacency, steady uptrend likely.")
            elif cboe_vix is not None:
                if cboe_vix > 30:
                    score -= 0.2
                    reasons.append(f"Global Volatility: CBOE VIX is critically high ({cboe_vix:.1f}). Global panic.")
                elif cboe_vix < 15:
                    score += 0.1
                    reasons.append(f"Global Volatility: CBOE VIX is low ({cboe_vix:.1f}). Global risk-on environment.")
            else:
                reasons.append("Volatility Sentiment: Regional/Global VIX data unavailable.")

        except Exception as e:
            logger.error(f"Error in BehavioralQuantEngine: {e}")
            reasons.append("Behavioral Engine: Error analyzing fear and volatility models.")

        return {
            "branch": "Behavioral Finance & Volatility",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
