import logging

logger = logging.getLogger("elco.module.sentiment.darkpool")

class InstitutionalDarkpoolEngine:
    """
    Handles Highest-Level Sentiment: Dark Pools, Dealer GEX (Gamma Exposure), and COT Data.
    """
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. Dark Pool Activity
            dark_pool_buy_volume = self.data.get("dark_pool_buy_volume")
            dark_pool_sell_volume = self.data.get("dark_pool_sell_volume")
            
            if dark_pool_buy_volume is not None and dark_pool_sell_volume is not None:
                dp_ratio = dark_pool_buy_volume / max(dark_pool_sell_volume, 1)
                if dp_ratio > 1.5:
                    score += 0.2
                    reasons.append(f"Dark Pool Activity: Massive hidden BUYING (Ratio: {dp_ratio:.2f}). Institutions accumulating.")
                elif dp_ratio < 0.6:
                    score -= 0.2
                    reasons.append(f"Dark Pool Activity: Massive hidden SELLING (Ratio: {dp_ratio:.2f}). Institutions distributing.")
            else:
                reasons.append("Dark Pool Activity: Dark pool volume data unavailable.")

            # 2. Dealer Gamma Exposure (GEX)
            gex = self.data.get("dealer_gex")
            if gex is not None:
                if gex < -100000:
                    score -= 0.15
                    reasons.append(f"Dealer Positioning: GEX is deeply NEGATIVE ({gex}). Dealers will amplify market moves.")
                elif gex > 100000:
                    score += 0.1
                    reasons.append(f"Dealer Positioning: GEX is strongly POSITIVE ({gex}). Dealers will suppress volatility.")
            else:
                reasons.append("Dealer Positioning: GEX data unavailable.")

            # 3. COT (Commitment of Traders) Index
            cot_commercial_net = self.data.get("cot_commercial_net")
            if cot_commercial_net is not None:
                if cot_commercial_net > 0.8:
                    score += 0.2
                    reasons.append(f"COT Data: Commercial Hedgers at extreme NET LONG levels ({cot_commercial_net:.2f}).")
                elif cot_commercial_net < -0.8:
                    score -= 0.2
                    reasons.append(f"COT Data: Commercial Hedgers at extreme NET SHORT levels ({cot_commercial_net:.2f}).")
            else:
                reasons.append("COT Data: Commercial net positioning unavailable.")

            # 4. FII / DII Flow Analysis
            fii_net = self.data.get("fii_net_buying")
            dii_net = self.data.get("dii_net_buying")
            if fii_net is not None and dii_net is not None:
                if fii_net > 0 and dii_net > 0:
                    score += 0.25
                    reasons.append(f"Institutional Flow: Both FIIs (+{fii_net}) and DIIs (+{dii_net}) are NET BUYERS. Highly Bullish.")
                elif fii_net < 0 and dii_net < 0:
                    score -= 0.25
                    reasons.append(f"Institutional Flow: Both FIIs ({fii_net}) and DIIs ({dii_net}) are NET SELLERS. Highly Bearish.")
                elif fii_net > 0 and dii_net < 0:
                    score += 0.1
                    reasons.append("Institutional Flow: FIIs Buying, DIIs Selling. Smart money inflow.")
                elif fii_net < 0 and dii_net > 0:
                    score -= 0.1
                    reasons.append("Institutional Flow: FIIs Selling, DIIs Buying. Smart money outflow.")
            else:
                reasons.append("Institutional Flow: FII/DII net buying data unavailable.")

            # 5. Block / Bulk Deals
            block_deals = self.data.get("block_deals_sentiment")
            if block_deals == "Bullish":
                score += 0.15
                reasons.append("Block Deals: Significant Promoter/Institutional Block Buying detected.")
            elif block_deals == "Bearish":
                score -= 0.15
                reasons.append("Block Deals: Significant Promoter/Institutional Block Selling detected.")

        except Exception as e:
            logger.error(f"Error in InstitutionalDarkpoolEngine: {e}")
            reasons.append("Dark Pool Engine: Error analyzing complex institutional positioning.")

        return {
            "branch": "Dark Pools & Dealer Positioning",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
