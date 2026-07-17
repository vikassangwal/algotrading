import logging

logger = logging.getLogger("elco.module.risk.metrics")

class PerformanceMetricsEngine:
    """
    Handles Portfolio Risk Metrics: Sharpe, Sortino, Drawdown, Beta, Alpha.
    """
    def __init__(self, risk_params: dict):
        self.params = risk_params

    def analyze(self, current_drawdown: float, sharpe_ratio: float, beta: float,
                returns=None) -> dict:
        result = {
            "approved": False,
            "reasons": []
        }

        try:
            max_drawdown_limit = self.params.get("max_drawdown_limit", 0.15) # 15% Max DD
            min_sharpe = self.params.get("min_sharpe_ratio", 1.0)

            # Real Sortino and Calmar when a returns series is supplied; otherwise
            # fall back to the (rough) Sharpe-proxy so legacy callers still work.
            if returns is not None and len(returns) >= 2:
                from ..quant_metrics import sortino_ratio as _sortino, calmar_ratio as _calmar
                sortino_ratio = _sortino(returns)
                calmar_ratio = _calmar(returns)
            else:
                sortino_ratio = sharpe_ratio * 1.3  # proxy: no returns series provided
                calmar_ratio = sharpe_ratio / (current_drawdown * 10) if current_drawdown > 0 else sharpe_ratio * 2
            
            # 1. Maximum Drawdown Check (The Ultimate Kill Switch)
            if current_drawdown > max_drawdown_limit:
                result["reasons"].append(f"CRITICAL RISK BLOCK: Current Drawdown ({current_drawdown*100:.1f}%) exceeds max limit ({max_drawdown_limit*100:.1f}%). Trading Halted to protect capital.")
                return result
                
            result["reasons"].append(f"Drawdown Check Passed: Current DD is {current_drawdown*100:.1f}% (Limit: {max_drawdown_limit*100:.1f}%).")
            
            # 2. Sharpe & Sortino Ratio Check
            if sharpe_ratio < min_sharpe:
                result["reasons"].append(f"Warning: Portfolio Sharpe Ratio ({sharpe_ratio:.2f}) is below target ({min_sharpe}). Risk-adjusted returns are poor.")
            else:
                result["reasons"].append(f"Sharpe Check Passed: Portfolio Sharpe Ratio is healthy ({sharpe_ratio:.2f}).")
                
            result["reasons"].append(f"Advanced Quant Ratios: Sortino Ratio ({sortino_ratio:.2f}), Calmar Ratio ({calmar_ratio:.2f}).")
                
            # 3. Beta / Volatility Alert
            if beta > 1.5:
                result["reasons"].append(f"Beta Warning: Portfolio Beta is {beta:.1f}. 50% more volatile than Nifty50. High Systematic Risk.")
            elif beta < 0.5:
                result["reasons"].append(f"Beta Note: Portfolio Beta is {beta:.1f}. Highly defensive positioning against market crashes.")
                
            result["approved"] = True

        except Exception as e:
            logger.error(f"Error in PerformanceMetricsEngine: {e}")
            result["reasons"].append("Performance Metrics Engine: Error calculating DD, Sharpe, Sortino or Calmar.")

        return result
