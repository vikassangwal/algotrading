import logging

logger = logging.getLogger("elco.module.quant.statarb")

class StatArbEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            pair_z_score = self.data.get("pair_spread_z_score")
            if pair_z_score is not None:
                if pair_z_score > 2.5:
                    score -= 0.2
                    reasons.append(f"Stat Arb (Pairs): Spread Z-Score is +{pair_z_score:.1f}. Asset is overvalued relative to its cointegrated pair. (Mean Reversion Short)")
                elif pair_z_score < -2.5:
                    score += 0.2
                    reasons.append(f"Stat Arb (Pairs): Spread Z-Score is {pair_z_score:.1f}. Asset is undervalued relative to its cointegrated pair. (Mean Reversion Long)")

            bid_ask_imbalance = self.data.get("bid_ask_imbalance")
            if bid_ask_imbalance is not None:
                if bid_ask_imbalance > 0.6:
                    score += 0.15
                    reasons.append("Microstructure: Massive Institutional Bid Liquidity detected (Strong Support Wall).")
                elif bid_ask_imbalance < -0.6:
                    score -= 0.15
                    reasons.append("Microstructure: Massive Institutional Ask Liquidity detected (Strong Resistance Wall).")

            slippage_risk = self.data.get("expected_slippage_bps")
            if slippage_risk is not None:
                if slippage_risk > 10.0:
                    score -= 0.1
                    reasons.append(f"Microstructure: High Execution Risk. Expected Slippage is {slippage_risk} bps.")

        except Exception as e:
            logger.error(f"Error in StatArbEngine: {e}")
            reasons.append("Stat Arb Engine: Error modeling microstructure.")

        return {
            "branch": "Statistical Arbitrage & Microstructure",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
