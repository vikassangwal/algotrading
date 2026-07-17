import logging

logger = logging.getLogger("elco.module.macro.indicators")

class EconomicIndicatorsEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. GDP Growth
            gdp_growth = self.data.get("gdp_growth_pct")
            if gdp_growth is not None:
                if gdp_growth > 7.0:
                    score += 0.25
                    reasons.append(f"Economic Core: GDP Growth is extremely robust ({gdp_growth}%). Strong macro tailwind.")
                elif gdp_growth < 4.0:
                    score -= 0.25
                    reasons.append(f"Economic Core: GDP Growth is weak ({gdp_growth}%). Warning of economic slowdown.")
                else:
                    reasons.append(f"Economic Core: GDP Growth is moderate ({gdp_growth}%).")
            else:
                reasons.append("Economic Core: GDP Growth data is unavailable.")

            # 2. CPI Inflation
            cpi_inflation = self.data.get("cpi_inflation_pct")
            if cpi_inflation is not None:
                if cpi_inflation > 6.5:
                    score -= 0.2
                    reasons.append(f"Economic Core: CPI Inflation ({cpi_inflation}%) is above RBI tolerance band. High risk of rate hikes.")
                elif cpi_inflation < 4.5:
                    score += 0.2
                    reasons.append(f"Economic Core: CPI Inflation ({cpi_inflation}%) is well controlled. Benign environment for equities.")
                else:
                    reasons.append(f"Economic Core: CPI Inflation ({cpi_inflation}%) is within tolerance band.")
            else:
                reasons.append("Economic Core: CPI Inflation data is unavailable.")

            # 3. Manufacturing & Services PMI
            pmi_mfg = self.data.get("pmi_manufacturing")
            pmi_srv = self.data.get("pmi_services")
            
            if pmi_mfg is not None and pmi_srv is not None:
                if pmi_mfg > 50 and pmi_srv > 50:
                    score += 0.15
                    reasons.append(f"Economic Core: PMI (Mfg: {pmi_mfg}, Srv: {pmi_srv}) indicates strong business expansion.")
                elif pmi_mfg < 50 or pmi_srv < 50:
                    score -= 0.15
                    reasons.append(f"Economic Core: PMI (Mfg: {pmi_mfg}, Srv: {pmi_srv}) indicates business contraction.")
                else:
                    reasons.append(f"Economic Core: PMI (Mfg: {pmi_mfg}, Srv: {pmi_srv}) indicates neutral business environment.")
            else:
                reasons.append("Economic Core: PMI data is unavailable.")

        except Exception as e:
            logger.error(f"Error in EconomicIndicatorsEngine: {e}")
            reasons.append("Economic Core Engine: Error analyzing macro indicators.")

        return {
            "branch": "Core Economic Indicators",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
