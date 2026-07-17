import logging
from .base import AnalysisModule, ModuleSignal

from .risk_branches.position_sizing import PositionSizingEngine
from .risk_branches.var_cvar import VaRCVaREngine
from .risk_branches.performance_metrics import PerformanceMetricsEngine
from .risk_branches.stress_testing import StressTestingEngine

logger = logging.getLogger("elco.module.risk.master")

class RiskManagementModule:
    name = "risk_manager"
    def __init__(self, provider):
        self.provider = provider
        self.risk_params = {
            "total_capital": 1000000,
            "risk_per_trade_pct": 0.01,
            "min_rr_ratio": 2.0,
            "max_portfolio_var": 25000,
            "max_drawdown_limit": 0.15,
            "min_sharpe_ratio": 1.2,
            "max_stress_loss": 300000
        }
        
    def evaluate_trade(self, symbol: str, entry_price: float, stop_loss: float, target: float, current_portfolio_exposure: float = 200000, portfolio_volatility: float = 0.02) -> dict:
        reasons = []
        reasons.append("--- 9th MASTER ENGINE: RISK MANAGEMENT GATEKEEPER INITIALIZED ---")
        
        is_approved = True
        final_quantity = 0
        total_score = 0.0
        
        raw_data = {}
        try:
            if hasattr(self.provider, 'get_quant_data'):
                raw_data = self.provider.get_quant_data(symbol) or {}
        except Exception as e:
            logger.warning(f"Failed to fetch risk/quant data for {symbol}: {e}")

        reasons.append("--- MASTER 4-LEVEL RISK & MONEY MANAGEMENT ENGINE INITIALIZED ---")
        
        # ENGINE 1: Position Sizing & Stop Loss
        pos_engine = PositionSizingEngine(self.risk_params)
        pos_res = pos_engine.analyze(entry_price, stop_loss, target)
        if not pos_res.get('approved', False):
            is_approved = False
        final_quantity = pos_res.get('quantity', 0)
        reasons.extend(pos_res.get('reasons', []))

        # ENGINE 2: VaR & CVaR (Tail Risk)
        var_engine = VaRCVaREngine(self.risk_params)
        var_res = var_engine.analyze(current_portfolio_exposure, portfolio_volatility)
        if not var_res.get('approved', False):
            is_approved = False
        reasons.extend(var_res.get('reasons', []))

        # ENGINE 3: Performance Metrics
        current_drawdown = raw_data.get('current_drawdown', 0.05)
        sharpe_ratio = raw_data.get('sharpe_ratio', 1.5)
        beta = raw_data.get('beta', 1.0)
        
        perf_engine = PerformanceMetricsEngine(self.risk_params)
        perf_res = perf_engine.analyze(current_drawdown, sharpe_ratio, beta)
        if not perf_res.get('approved', False):
            is_approved = False
        reasons.extend(perf_res.get('reasons', []))

        # ENGINE 4: Stress Testing & Monte Carlo
        stress_engine = StressTestingEngine(self.risk_params)
        stress_res = stress_engine.analyze(current_portfolio_exposure)
        if not stress_res.get('approved', False):
            is_approved = False
        reasons.extend(stress_res.get('reasons', []))

        if is_approved:
            reasons.insert(1, f"GATEKEEPER STATUS: TRADE APPROVED. Final Quantity: {final_quantity} shares.")
            status = "APPROVED"
        else:
            reasons.insert(1, "GATEKEEPER STATUS: TRADE BLOCKED. Risk Limits Exceeded.")
            status = "BLOCKED"
            final_quantity = 0

        return {
            "status": status,
            "quantity": final_quantity,
            "reasons": reasons
        }
