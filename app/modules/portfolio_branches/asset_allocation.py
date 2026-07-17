import logging
from typing import Dict, Any

logger = logging.getLogger("elco.module.portfolio.asset_allocation")

class AssetAllocationEngine:
    """
    Sub-engine: Calculates sector exposure using live monetary values instead of hardcoded percentages.
    """
    def __init__(self, portfolio_state: Dict[str, Any]):
        self.portfolio = portfolio_state

    def analyze(self, new_symbol: str, sector: str, new_trade_value: float) -> dict:
        reasons = []
        approved = True
        
        limit = self.portfolio.get("max_sector_weight_limit", 0.25)
        current_portfolio_value = self.portfolio.get("total_portfolio_value", 1000000.0)
        sector_values = self.portfolio.get("sector_exposures_value", {})
        
        current_sector_val = sector_values.get(sector, 0.0)
        
        # Calculate what the exposure WILL be if we take this trade
        new_total_value = current_portfolio_value + new_trade_value
        projected_sector_val = current_sector_val + new_trade_value
        
        projected_exposure = projected_sector_val / new_total_value if new_total_value > 0 else 0
        
        if projected_exposure > limit:
            reasons.append(f"[ASSET ALLOCATION] BLOCKED: Adding {new_symbol} pushes {sector} exposure to {projected_exposure:.1%} (Limit: {limit:.1%})")
            approved = False
        else:
            reasons.append(f"[ASSET ALLOCATION] PASS: Projected {sector} exposure is {projected_exposure:.1%} (Limit: {limit:.1%})")
            
        return {
            "approved": approved,
            "reasons": reasons
        }
