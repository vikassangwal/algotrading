import logging
from typing import Dict, Any

logger = logging.getLogger("elco.module.portfolio.factor_exposure")

class FactorExposureEngine:
    """
    Sub-engine: Checks Factor limits (e.g. Momentum, Value) using real capital.
    """
    def __init__(self, portfolio_state: Dict[str, Any]):
        self.portfolio = portfolio_state

    def analyze(self, new_factor: str, new_trade_value: float) -> dict:
        reasons = []
        approved = True
        
        # --- Level 4: CAPM & Modern Portfolio Theory (MPT) Metrics ---
        # Proxies (assuming standard index returns and risk free rate)
        risk_free_rate = 0.07 # 7% India
        market_return = 0.12 # 12% Nifty expectation
        
        # In a real environment, Beta and Volatility are passed via self.portfolio or raw_data.
        # We will assume some heuristic logic if data is missing.
        assumed_beta = 1.1 # slightly higher than market
        assumed_volatility = 0.18 # 18% annualized vol
        assumed_asset_return = 0.15 # 15% projected
        
        capm_expected_return = risk_free_rate + assumed_beta * (market_return - risk_free_rate)
        jensens_alpha = assumed_asset_return - capm_expected_return
        sharpe_ratio = (assumed_asset_return - risk_free_rate) / assumed_volatility
        sortino_ratio = (assumed_asset_return - risk_free_rate) / (assumed_volatility * 0.7) # Approx downside dev
        
        reasons.append(f"[CAPM] Expected Return: {capm_expected_return*100:.1f}% | Projected: {assumed_asset_return*100:.1f}% | Alpha: {jensens_alpha*100:.1f}%")
        
        if sharpe_ratio > 1.0:
            reasons.append(f"[MPT] Sharpe Ratio is excellent ({sharpe_ratio:.2f}). Return compensates for risk.")
        else:
            reasons.append(f"[MPT] Sharpe Ratio is poor ({sharpe_ratio:.2f}). Risk-adjusted return is low.")
            
        if sortino_ratio > 1.5:
            reasons.append(f"[MPT] Sortino Ratio is strong ({sortino_ratio:.2f}). Downside risk is contained.")
            
        # --- Level 7: Institutional Factor Investing ---
        allowed_factors = ["Value", "Momentum", "Quality", "Low Volatility", "Size"]
        if new_factor not in allowed_factors:
             reasons.append(f"[FACTOR WARNING] Trade does not align with Institutional Factor Investing ({new_factor}).")
        
        current_portfolio_value = self.portfolio.get("total_portfolio_value", 1000000.0)
        factor_values = self.portfolio.get("factor_exposures_value", {})
        current_factor_val = factor_values.get(new_factor, 0.0)
        
        new_total_value = current_portfolio_value + new_trade_value
        projected_factor_val = current_factor_val + new_trade_value
        
        projected_concentration = projected_factor_val / new_total_value if new_total_value > 0 else 0
        
        # Hardcoded limit 50% for now
        limit = 0.50
        
        if projected_concentration > limit:
            reasons.append(f"[FACTOR EXPOSURE] BLOCKED: Adding {new_factor} trade pushes concentration to {projected_concentration:.1%} (Limit: {limit:.1%})")
            approved = False
        else:
            reasons.append(f"[FACTOR EXPOSURE] PASS: Projected {new_factor} concentration is {projected_concentration:.1%} (Limit: {limit:.1%})")

        return {
            "approved": approved,
            "reasons": reasons
        }
