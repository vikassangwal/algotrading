import logging

logger = logging.getLogger("elco.module.fundamental.financials")

class FinancialEngine:
    """
    Handles Basic Fundamentals, Financial Statements, Ratios, Earnings, and Cash Flow Analysis.
    """
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            roe = self.data.get("returnOnEquity")
            if roe is not None:
                if roe > 0.15:
                    score += 0.2
                    reasons.append(f"Profitability: Excellent Return on Equity (ROE) at {roe*100:.1f}%.")
                elif roe < 0.05:
                    score -= 0.2
                    reasons.append(f"Profitability: Poor Return on Equity (ROE) at {roe*100:.1f}%.")
            
            roce = self.data.get("returnOnAssets")
            if roce is not None:
                if roce > 0.10:
                    score += 0.1
                    reasons.append(f"Profitability: Strong Return on Assets at {roce*100:.1f}%.")
                elif roce < 0.02:
                    score -= 0.1
                    reasons.append(f"Profitability: Poor Return on Assets at {roce*100:.1f}%.")

            debt_to_equity = self.data.get("debtToEquity")
            if debt_to_equity is not None:
                debt_ratio = debt_to_equity / 100.0
                if debt_ratio < 0.5:
                    score += 0.15
                    reasons.append(f"Leverage: Low Debt-to-Equity ratio ({debt_ratio:.2f}).")
                elif debt_ratio > 2.0:
                    score -= 0.2
                    reasons.append(f"Leverage: High Debt-to-Equity ratio ({debt_ratio:.2f}) (High Risk).")
                
            current_ratio = self.data.get("currentRatio")
            if current_ratio is not None:
                if current_ratio > 1.5:
                    score += 0.1
                    reasons.append(f"Liquidity: Healthy Current Ratio ({current_ratio:.1f}).")
                elif current_ratio < 1.0:
                    score -= 0.1
                    reasons.append(f"Liquidity: Poor Current Ratio ({current_ratio:.1f}), struggling to meet short-term liabilities.")

            eps_growth = self.data.get("earningsGrowth")
            if eps_growth is not None:
                if eps_growth > 0.15:
                    score += 0.2
                    reasons.append(f"Earnings: Strong YoY EPS Growth of {eps_growth*100:.1f}%.")
                elif eps_growth < 0:
                    score -= 0.2
                    reasons.append(f"Earnings: Negative YoY EPS Growth ({eps_growth*100:.1f}%).")
                
            fcf = self.data.get("freeCashflow")
            if fcf is not None:
                if fcf > 0:
                    score += 0.15
                    reasons.append("Cash Flow: Company is generating Positive Free Cash Flow (FCF).")
                else:
                    score -= 0.15
                    reasons.append("Cash Flow: Company is burning cash (Negative FCF).")
                
            operating_margin = self.data.get("operatingMargins")
            if operating_margin is not None:
                if operating_margin > 0.20:
                    score += 0.1
                    reasons.append(f"Profitability: Wide Moat indicated by high Operating Margins ({operating_margin*100:.1f}%).")
                    
            gross_margin = self.data.get("grossMargins")
            profit_margin = self.data.get("profitMargins")
            if gross_margin is not None and profit_margin is not None:
                if profit_margin > 0.15:
                    score += 0.1
                    reasons.append(f"Profitability: Excellent Net Profit Margin ({profit_margin*100:.1f}%).")
                elif profit_margin < 0.0:
                    score -= 0.15
                    reasons.append(f"Profitability: Company is running at a Net Loss ({profit_margin*100:.1f}%).")

            quick_ratio = self.data.get("quickRatio")
            if quick_ratio is not None:
                if quick_ratio > 1.0:
                    reasons.append(f"Liquidity: Healthy Quick Ratio ({quick_ratio:.1f}) - Can pay immediate obligations without selling inventory.")
                elif quick_ratio < 0.5:
                    reasons.append(f"Liquidity: Poor Quick Ratio ({quick_ratio:.1f}) - High reliance on inventory sales.")

            ocf = self.data.get("operatingCashflow")
            if ocf is not None:
                if ocf > 0:
                    reasons.append(f"Cash Flow Analysis: Company generates positive Operating Cash Flow (OCF).")

            payout_ratio = self.data.get("payoutRatio")
            if payout_ratio is not None:
                if 0.10 < payout_ratio < 0.60:
                    score += 0.1
                    reasons.append(f"Capital Allocation: Healthy and sustainable Dividend Payout Ratio ({payout_ratio*100:.1f}%).")
                elif payout_ratio > 0.90:
                    score -= 0.1
                    reasons.append(f"Capital Allocation: Unsustainable Dividend Payout Ratio ({payout_ratio*100:.1f}%).")

            # Institutional Metrics: ROIC & EVA Proxies
            total_assets = self.data.get("totalAssets")
            if roe is not None and debt_to_equity is not None:
                # Rough ROIC Proxy = ROE * (1 - Debt/Capital) assuming debt cost is lower. 
                # Better proxy if we had EBIT and Tax rate, but we will use ROA + margin
                roic_proxy = roce * 1.2 if roce else (roe * 0.8) # Heuristic
                if roic_proxy > 0.15:
                    score += 0.2
                    reasons.append(f"Institutional Metrics: High Return on Invested Capital (ROIC Proxy: {roic_proxy*100:.1f}%). Efficient Capital Allocator.")
                
                wacc_proxy = 0.10 # 10% cost of capital
                eva_spread = roic_proxy - wacc_proxy
                if eva_spread > 0:
                    score += 0.15
                    reasons.append(f"Institutional Metrics (EVA): Positive Economic Value Added Spread (+{eva_spread*100:.1f}%). Creating shareholder wealth.")
                else:
                    reasons.append(f"Institutional Metrics (EVA): Negative Economic Value Added Spread ({eva_spread*100:.1f}%). Destroying shareholder wealth.")

            if not any(k in self.data for k in ["returnOnEquity", "debtToEquity", "earningsGrowth"]):
                reasons.append("Financial Engine: Missing key financial data. Score neutral.")

        except Exception as e:
            logger.error(f"Error in FinancialEngine: {e}")
            reasons.append("Financial Engine: Error analyzing fundamental metrics.")

        return {
            "branch": "Core Financials & Ratios",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
