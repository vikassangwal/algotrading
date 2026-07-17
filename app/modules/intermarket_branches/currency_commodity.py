import logging

logger = logging.getLogger("elco.module.intermarket.currency")

class CurrencyCommodityEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            dxy_trend = self.data.get("dxy_trend")
            gold_trend = self.data.get("gold_trend")
            
            if dxy_trend is not None:
                if dxy_trend == "Rising":
                    score -= 0.2
                    reasons.append("Intermarket (Currency): Dollar Index (DXY) is Rising. Severe headwind for Gold and Emerging Market Equities.")
                elif dxy_trend == "Falling":
                    score += 0.25
                    reasons.append("Intermarket (Currency): Dollar Index (DXY) is Weakening. Highly favorable for Emerging Market Capital Flows.")

            if gold_trend is not None and dxy_trend is not None:
                if gold_trend == "Rising" and dxy_trend == "Rising":
                    score -= 0.2
                    reasons.append("Intermarket (Anomaly): Both Gold and DXY are rising simultaneously! Extreme market fear / panic indicator.")

            crude_trend = self.data.get("crude_oil_trend")
            if crude_trend is not None:
                if crude_trend == "Rising":
                    score -= 0.2
                    reasons.append("Intermarket (Commodity): Crude Oil is in a strong uptrend. Raises inflation fears and probability of Rate Hikes (Bearish for Stocks).")
                elif crude_trend == "Falling":
                    score += 0.15
                    reasons.append("Intermarket (Commodity): Crude Oil is falling. Disinflationary environment is supportive for Equities (especially India).")

            usd_inr_trend = self.data.get("usd_inr_trend")
            if usd_inr_trend is not None:
                if usd_inr_trend == "Depreciating":
                    score -= 0.1
                    reasons.append("Intermarket (Currency): INR is depreciating rapidly. FIIs may pull out capital to prevent FX losses.")
                elif usd_inr_trend == "Appreciating":
                    score += 0.15
                    reasons.append("Intermarket (Currency): INR is appreciating. FII capital flows will accelerate due to FX gains.")

        except Exception as e:
            logger.error(f"Error in CurrencyCommodityEngine: {e}")
            reasons.append("Currency & Commodity Engine: Error analyzing intermarket data.")

        return {
            "branch": "Currency & Commodity Nexus",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
