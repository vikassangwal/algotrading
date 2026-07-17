import logging

logger = logging.getLogger("elco.module.derivatives.institutional")

class InstitutionalPositioningEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            fii_long_ratio = self.data.get("fii_index_futures_long_ratio")
            if fii_long_ratio is not None:
                if fii_long_ratio > 0.7:
                    score += 0.25
                    reasons.append(f"Institutional F&O: FIIs are Extremely Long in Index Futures ({fii_long_ratio*100:.0f}%). Major Market Tailwind.")
                elif fii_long_ratio < 0.3:
                    score -= 0.25
                    reasons.append(f"Institutional F&O: FIIs are Extremely Short in Index Futures ({fii_long_ratio*100:.0f}% Long). Major Market Headwind.")
                elif fii_long_ratio > 0.5:
                    score += 0.1
                    reasons.append("Institutional F&O: FII Index Futures bias is mildly Bullish.")
                else:
                    score -= 0.1
                    reasons.append("Institutional F&O: FII Index Futures bias is mildly Bearish.")

            client_options_bias = self.data.get("client_options_bias")
            fii_options_bias = self.data.get("fii_options_bias")
            
            if client_options_bias is not None and fii_options_bias is not None:
                if client_options_bias == "Bullish" and fii_options_bias == "Bearish":
                    score -= 0.3
                    reasons.append("Trap Analysis: SMART MONEY DIVERGENCE! Retail is Bullish, FIIs are Bearish. Expect a sharp drop.")
                elif client_options_bias == "Bearish" and fii_options_bias == "Bullish":
                    score += 0.3
                    reasons.append("Trap Analysis: SMART MONEY DIVERGENCE! Retail is Bearish, FIIs are Bullish. Expect a short squeeze upwards.")

        except Exception as e:
            logger.error(f"Error in InstitutionalPositioningEngine: {e}")
            reasons.append("Institutional F&O Engine: Error analyzing participant data.")

        return {
            "branch": "Institutional F&O Positioning",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
