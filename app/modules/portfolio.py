import logging
import yfinance as yf
from .base import AnalysisModule, ModuleSignal

# Import the Portfolio sub-engines
from .portfolio_branches.asset_allocation import AssetAllocationEngine
from .portfolio_branches.factor_exposure import FactorExposureEngine
from .portfolio_branches.rebalancing_tax import RebalancingTaxEngine
from app.data.portfolio_manager import PortfolioManager

logger = logging.getLogger("elco.module.portfolio.master")

class PortfolioManagementModule:
    """
    The 10th Master Engine: The Portfolio Supervisor.
    Works alongside Risk Management to ensure the overall basket of trades is healthy.
    Now integrated with real live data using yfinance and PortfolioManager.
    """
    def __init__(self, provider):
        self.provider = provider
        self.portfolio_manager = PortfolioManager()
        
    def _compute_live_portfolio_state(self) -> dict:
        """Fetches live prices for existing positions and calculates real portfolio state."""
        portfolio_state = self.portfolio_manager.load_portfolio()
        positions = portfolio_state.get("positions", [])
        cash = portfolio_state.get("cash_balance", 0.0)
        
        # If no positions, just return empty state
        if not positions:
            return {
                "max_sector_weight_limit": portfolio_state.get("max_sector_weight_limit", 0.25),
                "max_stock_weight_limit": portfolio_state.get("max_stock_weight_limit", 0.10),
                "sector_exposures_value": {},
                "factor_exposures_value": {},
                "total_portfolio_value": cash,
                "unrealized_short_term_losses": 0.0,
                "unrealized_short_term_gains": 0.0,
                "cash_balance": cash
            }
            
        # Fetch live prices for all held symbols using yfinance batch download
        symbols = [p["symbol"] for p in positions]
        try:
            # Download recent data, get the last close
            data = yf.download(symbols, period="5d", group_by="ticker", auto_adjust=False, progress=False)
            
            # Helper to extract latest price depending on how yfinance structures single vs multi-ticker download
            def get_latest_price(sym):
                if len(symbols) == 1:
                    return float(data['Close'].iloc[-1])
                else:
                    return float(data[sym]['Close'].iloc[-1])
                    
            live_prices = {sym: get_latest_price(sym) for sym in symbols}
        except Exception as e:
            logger.error(f"Failed to fetch live prices for portfolio: {e}")
            live_prices = {p["symbol"]: p["average_price"] for p in positions} # Fallback
            
        total_value = cash
        sector_values = {}
        factor_values = {}
        unrealized_gains = 0.0
        unrealized_losses = 0.0
        
        for pos in positions:
            sym = pos["symbol"]
            qty = pos["quantity"]
            avg_price = pos["average_price"]
            sector = pos.get("sector", "Unknown")
            factor = pos.get("factor", "Unknown")
            
            live_price = live_prices.get(sym, avg_price)
            position_value = qty * live_price
            
            # PnL
            unrealized_pnl = (live_price - avg_price) * qty
            if unrealized_pnl > 0:
                unrealized_gains += unrealized_pnl
            else:
                unrealized_losses += abs(unrealized_pnl)
                
            total_value += position_value
            
            # Aggregations
            sector_values[sector] = sector_values.get(sector, 0.0) + position_value
            factor_values[factor] = factor_values.get(factor, 0.0) + position_value
            
        computed_state = {
            "max_sector_weight_limit": portfolio_state.get("max_sector_weight_limit", 0.25),
            "max_stock_weight_limit": portfolio_state.get("max_stock_weight_limit", 0.10),
            "sector_exposures_value": sector_values,
            "factor_exposures_value": factor_values,
            "total_portfolio_value": total_value,
            "unrealized_short_term_losses": unrealized_losses,
            "unrealized_short_term_gains": unrealized_gains,
            "cash_balance": cash
        }
        return computed_state

    def evaluate_portfolio_fit(self, new_trade_symbol: str, new_trade_sector: str, new_trade_factor: str, new_trade_price: float = 0.0, new_trade_qty: int = 0) -> dict:
        reasons = []
        reasons.append("--- 10th MASTER ENGINE: PORTFOLIO ANALYSIS INITIALIZED ---")
        
        is_approved = True
        
        # 1. Fetch live portfolio state
        live_portfolio_state = self._compute_live_portfolio_state()
        
        new_trade_value = new_trade_price * new_trade_qty
        
        # ==========================================
        # ENGINE 1: Asset Allocation & Correlation
        # ==========================================
        allocation_engine = AssetAllocationEngine(live_portfolio_state)
        alloc_res = allocation_engine.analyze(new_trade_symbol, new_trade_sector, new_trade_value)
        reasons.extend(alloc_res['reasons'])
        if not alloc_res['approved']:
            is_approved = False

        # ==========================================
        # ENGINE 2: Factor Exposure
        # ==========================================
        factor_engine = FactorExposureEngine(live_portfolio_state)
        factor_res = factor_engine.analyze(new_trade_factor, new_trade_value)
        reasons.extend(factor_res['reasons'])
        if not factor_res['approved']:
            is_approved = False

        # ==========================================
        # ENGINE 3: Rebalancing & Tax Harvesting
        # ==========================================
        rebalance_engine = RebalancingTaxEngine(live_portfolio_state)
        reb_res = rebalance_engine.analyze()
        reasons.extend(reb_res['reasons'])

        # ==========================================
        # FINAL SUPERVISOR DECISION
        # ==========================================
        if is_approved:
            reasons.insert(1, f"PORTFOLIO STATUS: HEALTHY. Adding {new_trade_symbol} keeps diversification intact.")
            status = "APPROVED"
        else:
            reasons.insert(1, f"PORTFOLIO STATUS: BLOCKED. Adding {new_trade_symbol} destroys portfolio balance.")
            status = "BLOCKED"

        return {
            "status": status,
            "reasons": reasons
        }
