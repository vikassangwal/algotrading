import logging

logger = logging.getLogger("elco.module.derivatives.options_chain")

class OptionsChainEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            pcr = self.data.get("put_call_ratio")
            if pcr is not None:
                if pcr > 1.3:
                    score -= 0.2
                    reasons.append(f"Options Chain: PCR is extremely High ({pcr}). Market is overbought, beware of reversal.")
                elif pcr < 0.6:
                    score += 0.2
                    reasons.append(f"Options Chain: PCR is extremely Low ({pcr}). Market is oversold, potential bounce expected.")
                elif pcr >= 1.0:
                    score += 0.1
                    reasons.append(f"Options Chain: PCR is bullish ({pcr}). More Puts written than Calls.")
                elif pcr < 1.0:
                    score -= 0.1
                    reasons.append(f"Options Chain: PCR is bearish ({pcr}). More Calls written than Puts.")

            call_writing_strength = self.data.get("call_writing_strength")
            put_writing_strength = self.data.get("put_writing_strength")
            
            if call_writing_strength is not None and put_writing_strength is not None:
                if put_writing_strength == "Strong" and call_writing_strength != "Strong":
                    score += 0.2
                    reasons.append("Options Chain: Aggressive Put Writing detected. Strong institutional support.")
                elif call_writing_strength == "Strong" and put_writing_strength != "Strong":
                    score -= 0.2
                    reasons.append("Options Chain: Aggressive Call Writing detected. Strong institutional resistance.")

            current_price = self.data.get("spot_price")
            max_pain = self.data.get("max_pain_strike")
            
            if current_price is not None and max_pain is not None:
                diff = (max_pain - current_price) / current_price
                if diff > 0.02:
                    score += 0.1
                    reasons.append(f"Max Pain: Magnet effect pulls UP (Spot: {current_price}, Max Pain: {max_pain}).")
                elif diff < -0.02:
                    score -= 0.1
                    reasons.append(f"Max Pain: Magnet effect pulls DOWN (Spot: {current_price}, Max Pain: {max_pain}).")

        except Exception as e:
            logger.error(f"Error in OptionsChainEngine: {e}")
            reasons.append("Options Chain Engine: Error analyzing Option Chain data.")

        return {
            "branch": "Options Chain & Max Pain",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
