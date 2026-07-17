import logging

logger = logging.getLogger("elco.module.fundamental.forensic")

class ForensicQuantEngine:
    """
    Handles Forensic Accounting (Altman Z-Score, Beneish M-Score, Piotroski F-Score).
    Note: Requires explicit pre-calculated data or external provider.
    """
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # Dynamically calculate proxies if data is available from yfinance info
            z_score = self.data.get("altman_z_score")
            f_score = self.data.get("piotroski_f_score")
            
            if z_score is None:
                # Proxy Altman Z-Score
                # Depends on Working Capital, Retained Earnings, EBIT, Market Cap, Total Liabilities
                # We will approximate based on Debt/Equity and Current Ratio
                cr = self.data.get("currentRatio")
                de = self.data.get("debtToEquity")
                if cr is not None and de is not None:
                    # Very rough heuristic:
                    # High CR (> 1.5) and Low D/E (< 100) -> Safe
                    if cr > 1.5 and de < 50:
                        z_score = 3.5
                    elif cr < 1.0 and de > 150:
                        z_score = 1.2
                    else:
                        z_score = 2.5

            if f_score is None:
                # Proxy Piotroski F-Score (0-9)
                # Depends on ROA, OCF, Change in ROA, Accruals, Change in Leverage/Liquidity/Margins/Turnover
                roa = self.data.get("returnOnAssets")
                op_margin = self.data.get("operatingMargins")
                if roa is not None and op_margin is not None:
                    base_f_score = 5
                    if roa > 0.05: base_f_score += 1
                    if roa > 0.10: base_f_score += 1
                    if op_margin > 0.10: base_f_score += 1
                    if op_margin > 0.20: base_f_score += 1
                    f_score = base_f_score

            if z_score is not None:
                if z_score > 3.0:
                    score += 0.2
                    reasons.append(f"Forensic (Z-Score): {z_score:.2f} (Proxy) - 'Safe Zone' (No Bankruptcy Risk).")
                elif z_score < 1.8:
                    score -= 0.4
                    reasons.append(f"Forensic (Z-Score): {z_score:.2f} (Proxy) - 'Distress Zone' (HIGH BANKRUPTCY RISK).")

            if f_score is not None:
                if f_score >= 7:
                    score += 0.3
                    reasons.append(f"Forensic (F-Score): {f_score}/9 (Proxy) - Outstanding financial strength.")
                elif f_score <= 3:
                    score -= 0.3
                    reasons.append(f"Forensic (F-Score): {f_score}/9 (Proxy) - Extremely poor financial health.")

            m_score = self.data.get("beneish_m_score")
            if m_score is not None:
                if m_score > -1.78:
                    score -= 0.5 
                    reasons.append(f"Forensic (M-Score): {m_score:.2f} - RED FLAG! High probability of Earnings Manipulation.")
                else:
                    score += 0.1
                    reasons.append(f"Forensic (M-Score): {m_score:.2f} - No evidence of manipulation.")

            if z_score is None and f_score is None:
                reasons.append("Forensic Engine: Data unavailable. Cannot evaluate fraud or bankruptcy risk.")

        except Exception as e:
            logger.error(f"Error in ForensicQuantEngine: {e}")
            reasons.append("Forensic Engine: Error calculating quantitative forensic scores.")

        return {
            "branch": "Forensic & Quantitative Analysis",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
