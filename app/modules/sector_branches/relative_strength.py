import logging

logger = logging.getLogger("elco.module.sector.relative")

class RelativeStrengthEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            sector_alpha_1m = self.data.get("sector_alpha_1m")
            if sector_alpha_1m is not None:
                if sector_alpha_1m > 0.03:
                    score += 0.25
                    reasons.append(f"Relative Strength: Sector is generating strong Alpha vs Nifty50 (+{sector_alpha_1m*100:.1f}% in 1M). High Momentum.")
                elif sector_alpha_1m < -0.03:
                    score -= 0.25
                    reasons.append(f"Relative Strength: Sector is severely underperforming Nifty50 ({sector_alpha_1m*100:.1f}% in 1M). Lagging sector.")
                else:
                    reasons.append(f"Relative Strength: Sector is performing in-line with the broader market.")

            rotation_status = self.data.get("inter_sector_rotation")
            if rotation_status is not None:
                if rotation_status == "Inflow":
                    score += 0.2
                    reasons.append("Sector Rotation: Quantitative Ratio Charts indicate Smart Money is rotating INTO this sector.")
                elif rotation_status == "Outflow":
                    score -= 0.2
                    reasons.append("Sector Rotation: Quantitative Ratio Charts indicate Smart Money is rotating OUT of this sector.")

            sector_breadth_pct = self.data.get("sector_stocks_above_200dma")
            if sector_breadth_pct is not None:
                if sector_breadth_pct > 0.8:
                    score += 0.15
                    reasons.append(f"Sector Breadth: Extremely strong internals ({sector_breadth_pct*100:.0f}% of stocks > 200 DMA).")
                elif sector_breadth_pct < 0.2:
                    score -= 0.15
                    reasons.append(f"Sector Breadth: Extremely weak internals ({sector_breadth_pct*100:.0f}% of stocks > 200 DMA).")

        except Exception as e:
            logger.error(f"Error in RelativeStrengthEngine: {e}")
            reasons.append("Relative Strength Engine: Error analyzing quantitative ratios.")

        return {
            "branch": "Relative Strength & Sector Breadth",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
