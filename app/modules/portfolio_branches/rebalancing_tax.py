import logging
from typing import Dict, Any

logger = logging.getLogger("elco.module.portfolio.rebalancing_tax")

class RebalancingTaxEngine:
    """
    Sub-engine: Uses live unrealized P&L to suggest Tax Loss Harvesting.
    """
    def __init__(self, portfolio_state: Dict[str, Any]):
        self.portfolio = portfolio_state

    def analyze(self) -> dict:
        reasons = []
        
        losses = self.portfolio.get("unrealized_short_term_losses", 0.0)
        gains = self.portfolio.get("unrealized_short_term_gains", 0.0)
        
        # Suggest harvesting if losses are above 10,000 and we have gains to offset
        if losses > 10000 and gains > 10000:
            reasons.append(f"[TAX HARVESTING] ALERT: You have ₹{losses:,.2f} in unrealized losses and ₹{gains:,.2f} in gains. Consider Tax Loss Harvesting.")
        else:
            reasons.append(f"[TAX HARVESTING] PASS: No immediate tax harvesting needed.")

        return {
            "approved": True,  # Tax engine doesn't block trades
            "reasons": reasons
        }
