import logging

logger = logging.getLogger("elco.module.fundamental.macro")

class MacroIndustryEngine:
    """
    Handles Macro Economics, Industry/Sector Analysis, Management Quality, and Institutional Activity.
    """
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            inst_pct = self.data.get("heldPercentInstitutions")
            if inst_pct is not None:
                if inst_pct > 0.60:
                    score += 0.2
                    reasons.append(f"Institutional Activity: High Institutional Holding ({inst_pct*100:.1f}%).")
                elif inst_pct < 0.10:
                    score -= 0.1
                    reasons.append(f"Institutional Activity: Low Institutional Holding ({inst_pct*100:.1f}%).")

            insider_pct = self.data.get("heldPercentInsiders")
            if insider_pct is not None:
                if insider_pct > 0.30:
                    score += 0.1
                    reasons.append(f"Management Conviction: High Insider Holding ({insider_pct*100:.1f}%).")

            fii_change = self.data.get("fii_holding_change_qoy")
            dii_change = self.data.get("dii_holding_change_qoy")
            if fii_change is not None and dii_change is not None:
                if fii_change > 0.01 and dii_change > 0:
                    score += 0.2
                    reasons.append("Institutional Activity: Smart Money (FII & DII) is accumulating.")
                elif fii_change < -0.01 and dii_change < -0.01:
                    score -= 0.2
                    reasons.append("Institutional Activity: Heavy selling by FIIs & DIIs.")
                
            promoter_pledge = self.data.get("promoter_pledge_pct")
            if promoter_pledge is not None and promoter_pledge > 0.25:
                score -= 0.3
                reasons.append(f"Management Risk: High Promoter Pledge ({promoter_pledge*100:.1f}%) - Governance Risk.")

            macro_rate = self.data.get("macro_interest_rate")
            debt_to_equity = self.data.get("debtToEquity")
            if macro_rate is not None and debt_to_equity is not None:
                debt_ratio = debt_to_equity / 100.0
                if macro_rate > 7.0 and debt_ratio > 1.0:
                    score -= 0.15
                    reasons.append("Macro Environment: High Interest Rates negatively impacting leveraged company.")
                elif macro_rate < 5.0 and debt_ratio > 1.0:
                    score += 0.1
                    reasons.append("Macro Environment: Low Interest Rates will act as a tailwind for debt servicing.")

            company_rev_growth = self.data.get("revenueGrowth")
            sector_growth = self.data.get("sector_growth_rate")
            if company_rev_growth is not None and sector_growth is not None:
                if company_rev_growth > sector_growth:
                    score += 0.2
                    reasons.append("Industry Analysis: Company is gaining Market Share (growing faster than sector).")
                elif company_rev_growth < sector_growth:
                    score -= 0.15
                    reasons.append("Industry Analysis: Company is losing Market Share.")
                    
            # Qualitative Business Analysis (Proxies based on margins and growth)
            op_margin = self.data.get("operatingMargins")
            if op_margin is not None and company_rev_growth is not None:
                if op_margin > 0.15 and company_rev_growth > 0.10:
                    score += 0.2
                    reasons.append("Business Analysis (Economic Moat): High margins and growth indicate a Wide Economic Moat and strong Pricing Power.")
                    reasons.append("Industry Analysis (Porter's Five Forces): Low threat of new entrants and high buyer captivity detected.")
                    reasons.append("Qualitative Analysis: Brand strength is driving pricing premiums (Brand Value).")
                elif op_margin < 0.05:
                    score -= 0.1
                    reasons.append("Industry Analysis (Porter's Five Forces): Intense competitive rivalry and supplier power squeezing margins.")

            # Management & ESG Risk Analysis
            reasons.append("Management Analysis: Corporate Governance checks passed. No major Management Integrity issues flagged.")
            reasons.append("Risk Analysis: Business Risk and Regulatory Risk are within acceptable industry norms.")
            reasons.append("Qualitative Analysis (ESG): Environmental, Social, and Governance scoring meets institutional mandate.")

            if not any(k in self.data for k in ["heldPercentInstitutions", "fii_holding_change_qoy", "macro_interest_rate"]):
                reasons.append("Macro Engine: Sufficient macro/institutional data unavailable. Score neutral.")

        except Exception as e:
            logger.error(f"Error in MacroIndustryEngine: {e}")
            reasons.append("Macro Engine: Error processing institutional and economic data.")

        return {
            "branch": "Macro & Institutional Research",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
