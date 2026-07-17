import logging

logger = logging.getLogger("elco.module.risk.position")

class PositionSizingEngine:
    """
    Handles Capital Allocation, Position Sizing, and Risk-Reward Ratios.
    """
    def __init__(self, risk_params: dict):
        self.params = risk_params

    def analyze(self, entry_price: float, stop_loss: float, target: float, market_regime: str = "TRENDING") -> dict:
        result = {
            "approved": False,
            "quantity": 0,
            "reasons": []
        }
        
        try:
            capital = self.params.get("total_capital", 1000000) # 10 Lakhs
            base_risk_pct = self.params.get("risk_per_trade_pct", 0.01) # 1% Risk
            
            # Dynamic Risk Adjustment based on Regime
            if market_regime == "HIGH_VOLATILITY":
                risk_per_trade_pct = base_risk_pct * 0.5 # Half size in high volatility
                result["reasons"].append(f"Dynamic Sizing: Regime is HIGH_VOLATILITY. Risk scaled down to {risk_per_trade_pct*100}%.")
            elif market_regime == "RANGE_BOUND":
                risk_per_trade_pct = base_risk_pct * 0.75
                result["reasons"].append(f"Dynamic Sizing: Regime is RANGE_BOUND. Risk scaled down to {risk_per_trade_pct*100}%.")
            else:
                risk_per_trade_pct = base_risk_pct
                result["reasons"].append(f"Dynamic Sizing: Regime is TRENDING. Using base risk {risk_per_trade_pct*100}%.")

            min_rr_ratio = self.params.get("min_rr_ratio", 2.0) # 1:2 Minimum
            
            # 1. Risk vs Reward Calculation
            potential_loss = entry_price - stop_loss
            potential_profit = target - entry_price
            
            if potential_loss <= 0:
                result["reasons"].append("Position Sizing: Invalid Stop Loss (must be below entry for long).")
                return result
                
            rr_ratio = potential_profit / potential_loss
            
            if rr_ratio < min_rr_ratio:
                result["reasons"].append(f"Position Sizing REJECTED: Risk:Reward is 1:{rr_ratio:.1f}, which is below the minimum 1:{min_rr_ratio}.")
                return result
                
            # 2. Position Size Calculation
            max_loss_amount = capital * risk_per_trade_pct
            quantity = int(max_loss_amount / potential_loss)
            
            # Ensure quantity doesn't exceed total capital (unleveraged)
            max_qty_by_capital = int(capital / entry_price)
            final_quantity = min(quantity, max_qty_by_capital)
            
            if final_quantity <= 0:
                result["reasons"].append("Position Sizing REJECTED: Calculated quantity is 0 or negative.")
                return result
                
            result["approved"] = True
            result["quantity"] = final_quantity
            result["reasons"].append(f"Position Sizing APPROVED: Qty = {final_quantity} shares. (Risking ₹{max_loss_amount:,.2f} / {risk_per_trade_pct*100}% of Capital). R:R = 1:{rr_ratio:.1f}.")

        except Exception as e:
            logger.error(f"Error in PositionSizingEngine: {e}")
            result["reasons"].append("Position Sizing: Mathematical Error.")

        return result
