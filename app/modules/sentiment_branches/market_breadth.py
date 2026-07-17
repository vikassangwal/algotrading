import logging

logger = logging.getLogger("elco.module.sentiment.breadth")

class MarketBreadthEngine:
    """
    Handles Market Breadth (A/D Line), Intermarket Sentiment (DXY, Bonds), and Sector Rotation.
    """
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. Advance/Decline (A/D) Ratio
            ad_ratio = self.data.get("advance_decline_ratio")
            if ad_ratio is not None:
                if ad_ratio > 2.0:
                    score += 0.2
                    reasons.append(f"Market Breadth: Extremely strong Advance/Decline Ratio ({ad_ratio:.1f}). Broad-based buying.")
                elif ad_ratio < 0.5:
                    score -= 0.2
                    reasons.append(f"Market Breadth: Extremely weak Advance/Decline Ratio ({ad_ratio:.1f}). Broad-based selling.")
            else:
                reasons.append("Market Breadth: A/D Ratio data unavailable.")

            # 2. McClellan Oscillator Proxy
            mcclellan = self.data.get("mcclellan_oscillator")
            if mcclellan is not None:
                if mcclellan > 50:
                    score += 0.15
                    reasons.append(f"Market Breadth: McClellan Oscillator > +50 ({mcclellan:.1f}). Strong Bullish Momentum.")
                elif mcclellan < -50:
                    score -= 0.15
                    reasons.append(f"Market Breadth: McClellan Oscillator < -50 ({mcclellan:.1f}). Strong Bearish Momentum.")
            else:
                reasons.append("Market Breadth: McClellan Oscillator data unavailable.")

            # 3. Intermarket Sentiment (DXY & US10Y)
            dxy_trend = self.data.get("dxy_trend_up")
            us10y_trend = self.data.get("us10y_trend_up")
            
            if dxy_trend is not None and us10y_trend is not None:
                if dxy_trend and us10y_trend:
                    score -= 0.2
                    reasons.append("Intermarket: Dollar Index (DXY) and US 10Y Yields are both trending UP (Bearish Macro).")
                elif not dxy_trend and not us10y_trend:
                    score += 0.2
                    reasons.append("Intermarket: Dollar Index (DXY) and US 10Y Yields are both trending DOWN (Bullish Macro).")
            else:
                reasons.append("Intermarket: DXY or US10Y trend data unavailable.")

            # 4. Sector Rotation Momentum
            sector_momentum = self.data.get("sector_relative_strength")
            if sector_momentum:
                if sector_momentum == "Leading":
                    score += 0.15
                    reasons.append("Sector Sentiment: The underlying sector is Leading the broader market (Alpha generation).")
                elif sector_momentum == "Lagging":
                    score -= 0.15
                    reasons.append("Sector Sentiment: The underlying sector is Lagging the broader market (Capital outflow).")
            else:
                reasons.append("Sector Sentiment: Sector momentum data unavailable.")

            # 5. TRIN (Arms Index)
            trin = self.data.get("trin_arms_index")
            if trin is not None:
                if trin < 0.5:
                    score += 0.2
                    reasons.append(f"Market Breadth: TRIN (Arms Index) is very low ({trin:.2f}), indicating strong buying pressure in advancing stocks.")
                elif trin > 2.0:
                    score -= 0.2
                    reasons.append(f"Market Breadth: TRIN (Arms Index) is very high ({trin:.2f}), indicating strong selling pressure in declining stocks.")
            else:
                reasons.append("Market Breadth: TRIN data unavailable.")

            # 6. New Highs vs New Lows (NH/NL)
            new_highs = self.data.get("new_52w_highs", 0)
            new_lows = self.data.get("new_52w_lows", 0)
            if new_highs > 0 or new_lows > 0:
                nh_nl_ratio = new_highs / max(new_lows, 1)
                if nh_nl_ratio > 3.0:
                    score += 0.15
                    reasons.append(f"Market Breadth: Strong New Highs vs New Lows ratio ({nh_nl_ratio:.1f}). Broad market participation in uptrend.")
                elif nh_nl_ratio < 0.33:
                    score -= 0.15
                    reasons.append(f"Market Breadth: Weak New Highs vs New Lows ratio ({nh_nl_ratio:.1f}). Broad market breakdown.")
            else:
                reasons.append("Market Breadth: New Highs/Lows data unavailable.")

        except Exception as e:
            logger.error(f"Error in MarketBreadthEngine: {e}")
            reasons.append("Market Breadth Engine: Error analyzing macro intermarket data.")

        return {
            "branch": "Market Breadth & Intermarket",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
