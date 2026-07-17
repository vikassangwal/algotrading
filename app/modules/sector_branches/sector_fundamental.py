import logging

logger = logging.getLogger("elco.module.sector.fundamental")

class SectorFundamentalEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            current_pe = self.data.get("sector_current_pe")
            historical_pe = self.data.get("sector_historical_avg_pe")
            
            if current_pe is not None and historical_pe is not None:
                if current_pe < historical_pe * 0.8:
                    score += 0.25
                    reasons.append(f"Sector Fundamentals: Sector is trading at a deep discount (Current P/E: {current_pe:.1f} vs Avg: {historical_pe:.1f}). Deep Value.")
                elif current_pe > historical_pe * 1.3:
                    score -= 0.25
                    reasons.append(f"Sector Fundamentals: Sector is severely overvalued (Current P/E: {current_pe:.1f} vs Avg: {historical_pe:.1f}). Risk of de-rating.")

            roe_trend = self.data.get("sector_roe_trend")
            if roe_trend is not None:
                if roe_trend == "Expanding":
                    score += 0.2
                    reasons.append("Sector Fundamentals: Overall Sector Return on Equity (ROE) and Margins are Expanding.")
                elif roe_trend == "Contracting":
                    score -= 0.2
                    reasons.append("Sector Fundamentals: Overall Sector Return on Equity (ROE) and Margins are Contracting.")

            eps_growth = self.data.get("sector_eps_growth_pct")
            if eps_growth is not None:
                if eps_growth > 0.15:
                    score += 0.15
                    reasons.append(f"Sector Fundamentals: Sector is experiencing high Earnings Growth (+{eps_growth*100:.1f}% EPS).")
                elif eps_growth < 0.05:
                    score -= 0.15
                    reasons.append(f"Sector Fundamentals: Sector Earnings Growth is stagnating (+{eps_growth*100:.1f}% EPS).")

        except Exception as e:
            logger.error(f"Error in SectorFundamentalEngine: {e}")
            reasons.append("Sector Fundamental Engine: Error calculating aggregated sector metrics.")

        return {
            "branch": "Quantitative Sector Fundamentals",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
