import logging

logger = logging.getLogger("elco.module.macro.business_cycle")

class BusinessCycleEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. Business Cycle Phase
            cycle_phase = self.data.get("business_cycle_phase")
            if cycle_phase is not None:
                if cycle_phase == "Expansion":
                    score += 0.3
                    reasons.append("Business Cycle: Economy is in EXPANSION phase. Extremely Bullish for Equities.")
                elif cycle_phase == "Recovery":
                    score += 0.2
                    reasons.append("Business Cycle: Economy is in RECOVERY phase. Early Bull market dynamics active.")
                elif cycle_phase == "Slowdown":
                    score -= 0.15
                    reasons.append("Business Cycle: Economy is in SLOWDOWN phase. Shift to defensive sectors (FMCG/Pharma).")
                elif cycle_phase == "Recession":
                    score -= 0.4
                    reasons.append("Business Cycle: Economy is in RECESSION! Extreme Risk-Off environment. Heavy Cash / Short bias needed.")
            else:
                reasons.append("Business Cycle: Phase data is unavailable.")

            # 2. Financial Stability / Systemic Risk
            systemic_risk = self.data.get("systemic_risk_level")
            if systemic_risk is not None:
                if systemic_risk == "High":
                    score -= 0.3
                    reasons.append("Financial Stability: High Systemic/Banking Risk detected. Contagion risk is elevated.")
                else:
                    score += 0.1
                    reasons.append("Financial Stability: Systemic/Banking Risk appears controlled.")
            else:
                reasons.append("Financial Stability: Risk level data is unavailable.")

            # 3. Macro Sector Rotation
            target_asset_sector = self.data.get("asset_sector")
            if target_asset_sector is not None and cycle_phase is not None:
                favored_sectors = []
                if cycle_phase in ["Expansion", "Recovery"]:
                    favored_sectors = ["Banking", "Auto", "Realty", "Metals", "IT"]
                elif cycle_phase in ["Slowdown", "Recession"]:
                    favored_sectors = ["FMCG", "Pharma", "Utilities", "Gold"]
                    
                if target_asset_sector in favored_sectors:
                    score += 0.15
                    reasons.append(f"Sector Rotation: The target sector ({target_asset_sector}) is highly favorable during a {cycle_phase} phase.")
                else:
                    score -= 0.1
                    reasons.append(f"Sector Rotation: The target sector ({target_asset_sector}) typically underperforms during a {cycle_phase} phase.")
            else:
                reasons.append("Sector Rotation: Sector or Phase data is unavailable.")

        except Exception as e:
            logger.error(f"Error in BusinessCycleEngine: {e}")
            reasons.append("Business Cycle Engine: Error modeling macroeconomic cycle.")

        return {
            "branch": "Business Cycle & Sector Rotation",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
