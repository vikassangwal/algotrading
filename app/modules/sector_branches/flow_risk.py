import logging

logger = logging.getLogger("elco.module.sector.flow")

class SectorFlowRiskEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            fii_sector_flow = self.data.get("fii_sector_net_flow")
            dii_sector_flow = self.data.get("dii_sector_net_flow")
            
            if fii_sector_flow is not None and dii_sector_flow is not None:
                if fii_sector_flow == "Buying" and dii_sector_flow == "Buying":
                    score += 0.3
                    reasons.append("Flow Analysis: Both FIIs and DIIs are aggressively BUYING this sector (Massive Liquidity Tailwind).")
                elif fii_sector_flow == "Selling" and dii_sector_flow == "Selling":
                    score -= 0.3
                    reasons.append("Flow Analysis: Both FIIs and DIIs are aggressively SELLING this sector (Massive Liquidity Headwind).")
                elif fii_sector_flow == "Buying":
                    score += 0.1
                    reasons.append("Flow Analysis: FIIs are accumulating this sector.")

            sector_risk_level = self.data.get("sector_specific_risk")
            if sector_risk_level is not None:
                if sector_risk_level == "High":
                    score -= 0.2
                    reasons.append("Risk Analysis: Sector is facing HIGH specific risks (e.g. Regulatory crackdowns, input cost spikes).")
                elif sector_risk_level == "Low":
                    score += 0.1
                    reasons.append("Risk Analysis: Sector-specific operating environment is stable (Low Risk).")

        except Exception as e:
            logger.error(f"Error in SectorFlowRiskEngine: {e}")
            reasons.append("Flow & Risk Engine: Error tracking institutional flows.")

        return {
            "branch": "Institutional Flows & Sector Risk",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
