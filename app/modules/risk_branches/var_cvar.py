import logging
import math

logger = logging.getLogger("elco.module.risk.var")

class VaRCVaREngine:
    """
    Handles Institutional Value at Risk (VaR) and Conditional VaR (Expected Shortfall).
    """
    def __init__(self, risk_params: dict):
        self.params = risk_params

    def analyze(self, current_exposure: float, volatility: float) -> dict:
        result = {
            "approved": False,
            "reasons": []
        }
        
        try:
            # Simple Parametric VaR calculation (Mock implementation for 95% Confidence)
            # z-score for 95% is approx 1.645
            z_score_95 = 1.645
            var_95 = current_exposure * volatility * z_score_95
            
            # CVaR (Expected Shortfall) is usually higher than VaR
            cvar_95 = var_95 * 1.25 # Simplified proxy for tail risk
            
            max_allowed_var = self.params.get("max_portfolio_var", 50000) # ₹50,000 max daily risk
            
            if var_95 > max_allowed_var:
                result["reasons"].append(f"Risk Block: 95% VaR (₹{var_95:,.2f}) exceeds max allowed limit (₹{max_allowed_var:,.2f}). Trade Rejected.")
                return result
                
            result["approved"] = True
            result["reasons"].append(f"VaR Check Passed: 95% VaR is ₹{var_95:,.2f}. In 95% of scenarios, daily loss will not exceed this.")
            result["reasons"].append(f"CVaR Warning: In the worst 5% of cases (Black Swan), expected loss is around ₹{cvar_95:,.2f}.")

        except Exception as e:
            logger.error(f"Error in VaRCVaREngine: {e}")
            result["reasons"].append("VaR Engine: Error calculating tail risk.")

        return result
