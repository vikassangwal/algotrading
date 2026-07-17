import logging

logger = logging.getLogger("elco.module.macro.global")

class GlobalCrossAssetEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. Crude Oil (Brent)
            crude_price = self.data.get("brent_crude_usd")
            if crude_price is not None:
                if crude_price > 90.0:
                    score -= 0.25
                    reasons.append(f"Global Macro: Crude Oil is highly elevated (${crude_price:.2f}/bbl). Major inflation risk for India.")
                elif crude_price < 70.0:
                    score += 0.2
                    reasons.append(f"Global Macro: Crude Oil is cheap (${crude_price:.2f}/bbl). Extremely positive for Indian margins and CAD.")
                else:
                    reasons.append(f"Global Macro: Crude Oil is moderate (${crude_price:.2f}/bbl).")
            else:
                reasons.append("Global Macro: Crude Oil data is unavailable.")

            # 2. Dollar Index (DXY)
            dxy_level = self.data.get("dxy_index")
            if dxy_level is not None:
                if dxy_level > 105.0:
                    score -= 0.2
                    reasons.append(f"Global Macro: Dollar Index (DXY) is very strong ({dxy_level:.2f}). Risk of capital flight from Emerging Markets.")
                elif dxy_level < 100.0:
                    score += 0.2
                    reasons.append(f"Global Macro: Dollar Index (DXY) is weak ({dxy_level:.2f}). Highly favorable for FII inflows to India.")
                else:
                    reasons.append(f"Global Macro: Dollar Index (DXY) is moderate ({dxy_level:.2f}).")
            else:
                reasons.append("Global Macro: Dollar Index data is unavailable.")

            # 3. Gold / Safe Haven flows
            gold_trend = self.data.get("gold_trend_up")
            if gold_trend is not None and dxy_level is not None:
                if gold_trend and dxy_level < 105:
                    reasons.append("Global Macro: Gold is trending UP. Investors might be seeking safe havens.")
            elif gold_trend is not None:
                if gold_trend:
                    reasons.append("Global Macro: Gold is trending UP.")
            else:
                reasons.append("Global Macro: Gold trend data is unavailable.")

        except Exception as e:
            logger.error(f"Error in GlobalCrossAssetEngine: {e}")
            reasons.append("Global/Cross-Asset Engine: Error analyzing global data.")

        return {
            "branch": "Global Macro & Cross-Asset",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
