import logging

logger = logging.getLogger("elco.module.sector.structure")

class IndustryStructureEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            theme_momentum = self.data.get("theme_momentum")
            theme_name = self.data.get("active_theme", "Unknown Theme")
            
            if theme_momentum is not None:
                if theme_momentum == "High":
                    score += 0.25
                    reasons.append(f"Thematic Engine: The sector is riding a massive structural mega-trend ({theme_name}). Growth visibility is very high.")
                elif theme_momentum == "Low":
                    score -= 0.15
                    reasons.append(f"Thematic Engine: The sector is facing structural headwinds ({theme_name} decline). Avoid long-term allocation.")

            entry_barriers = self.data.get("industry_entry_barriers")
            pricing_power = self.data.get("industry_pricing_power")
            
            if entry_barriers is not None and pricing_power is not None:
                if entry_barriers == "High" and pricing_power == "High":
                    score += 0.2
                    reasons.append("Industry Structure: High Entry Barriers & Strong Pricing Power. Incumbents have a wide economic moat.")
                elif entry_barriers == "Low" and pricing_power == "Low":
                    score -= 0.2
                    reasons.append("Industry Structure: Low Entry Barriers & Weak Pricing Power. Highly fragmented and commoditized industry.")

            govt_support = self.data.get("government_policy_support")
            if govt_support is not None:
                if govt_support == "Favorable":
                    score += 0.15
                    reasons.append("Qualitative Analysis: Sector enjoys strong Government Policy Support (e.g. PLI schemes, tax breaks).")
                elif govt_support == "Unfavorable":
                    score -= 0.2
                    reasons.append("Qualitative Analysis: Sector faces high Regulatory Headwinds or punitive taxation.")

        except Exception as e:
            logger.error(f"Error in IndustryStructureEngine: {e}")
            reasons.append("Industry Structure Engine: Error evaluating qualitative themes.")

        return {
            "branch": "Industry Structure & Themes",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
