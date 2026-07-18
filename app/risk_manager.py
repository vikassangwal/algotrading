import logging
from typing import Dict

from .config import config, AutoTradeState
from .engine import FusedSignal

logger = logging.getLogger("elco.risk")

class RiskManager:
    def __init__(self):
        # State tracking for mock portfolio
        self.portfolio_exposure = 0.0 # INR currently deployed
        self.daily_pnl = 0.0          # INR P&L for today

    def calculate_position_size(self, signal: FusedSignal, market_regime: str = None) -> float:
        """
        Calculates the optimal position size (in INR) based on the Kelly Criterion.
        Returns 0.0 if the trade is rejected due to risk limits.

        market_regime (optional): "HIGH_VOLATILITY" | "RANGE_BOUND" | "TRENDING" |
        "TRANSITIONING". When supplied, scales the allocation down in choppier /
        more volatile regimes (dynamic position sizing).
        """
        if config.auto_trade != AutoTradeState.ACTIVE:
            logger.warning("Trade rejected: AutoTrade is not ACTIVE.")
            return 0.0

        if signal.action == "NEUTRAL":
            return 0.0

        # 1. Check Daily Loss Limit (Hard Auto-Stop)
        max_daily_loss = config.capital * (config.risk.daily_loss_limit_pct / 100.0)
        if self.daily_pnl <= -max_daily_loss:
            logger.error(f"HARD AUTO-STOP: Daily loss limit reached ({-max_daily_loss}). Halting system.")
            self.trigger_system_halt("Daily loss limit breached")
            return 0.0

        # 2. Kelly Criterion for Position Sizing
        # Kelly % = W - [(1 - W) / R]
        # Where:
        # W = Win probability (we use signal.overall_confidence)
        # R = Reward:Risk ratio (Assume a conservative baseline of 1.5 for the system)

        W = signal.overall_confidence
        R = 1.5

        # If win prob is very low, Kelly might be negative.
        kelly_pct = W - ((1.0 - W) / R)

        # Half-Kelly is often used in practice to reduce volatility
        half_kelly_pct = kelly_pct / 2.0

        if half_kelly_pct <= 0:
            logger.warning(f"Trade rejected: Kelly Criterion indicates negative edge (W={W:.2f}).")
            return 0.0

        # Value at Risk (VaR) check: Ensure Kelly doesn't suggest too much
        max_kelly_pct = 0.20 # Cap at 20% of capital per trade max
        safe_alloc_pct = min(half_kelly_pct, max_kelly_pct)

        requested_allocation = config.capital * safe_alloc_pct

        # 3. Check Max Position Size Limit (User configuration)
        max_alloc_allowed = config.capital * (config.risk.max_position_pct / 100.0)
        requested_allocation = min(requested_allocation, max_alloc_allowed)

        # 3b. Dynamic sizing: scale the final allocation by the market regime
        # (applied AFTER the position cap so choppier regimes genuinely trade smaller).
        regime_multiplier = self._regime_multiplier(market_regime)
        if regime_multiplier != 1.0:
            requested_allocation *= regime_multiplier
            logger.info(f"Dynamic sizing: regime={market_regime} → allocation scaled ×{regime_multiplier}.")

        # 4. Check Portfolio Exposure Limit
        new_exposure = self.portfolio_exposure + requested_allocation
        max_exposure_allowed = config.capital * (config.risk.max_portfolio_exposure_pct / 100.0)
        if new_exposure > max_exposure_allowed:
            # Scale down to whatever is left
            requested_allocation = max(0.0, max_exposure_allowed - self.portfolio_exposure)

            if requested_allocation == 0.0:
                logger.warning("Trade rejected: Max portfolio exposure reached.")
                return 0.0

        return requested_allocation

    @staticmethod
    def _regime_multiplier(market_regime: str) -> float:
        """Dynamic position-sizing multiplier by regime. Smaller size when the
        market is volatile or range-bound (lower edge / higher whipsaw risk)."""
        return {
            "HIGH_VOLATILITY": 0.5,
            "RANGE_BOUND": 0.75,
            "TRANSITIONING": 0.85,
            "TRENDING": 1.0,
        }.get(market_regime, 1.0)

    def process_crash_risk_radar(self, crash_risk_score: float):
        """
        Takes the NLP + market risk score from Module 7 (News & Crash-Risk Radar).
        If it exceeds the threshold, halt the system immediately.
        """
        if crash_risk_score >= config.risk.crash_risk_halt_threshold:
            logger.error(
                f"CRITICAL: Crash-Risk Radar triggered at score {crash_risk_score}. "
                f"Threshold is {config.risk.crash_risk_halt_threshold}."
            )
            self.trigger_system_halt(f"Crash-Risk Radar score: {crash_risk_score}")

    def trigger_system_halt(self, reason: str):
        """Halts all automated trading activities immediately and requests manual override."""
        config.auto_trade = AutoTradeState.HALTED
        logger.critical(f"SYSTEM HALTED. Reason: {reason}")
        try:
            from .alerts import alert_halt
            alert_halt(reason)
        except Exception:
            pass
        
        # Create a Workflow Approval Request for manual override
        try:
            from .db import SessionLocal, WorkflowApproval
            import uuid
            db = SessionLocal()
            
            # Generate a unique request ID
            req_id = f"REQ-{str(uuid.uuid4().int)[:6]}"
            
            new_req = WorkflowApproval(
                id=req_id,
                type="System Auto-Resume",
                details=f"System halted due to: {reason}. Requesting 4-eyes approval to resume AutoTrade.",
                initiator="RiskManager AI",
                riskLevel="Critical",
                status="pending"
            )
            db.add(new_req)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to create Workflow Approval Request: {e}")

# Singleton instance for the process
risk_manager = RiskManager()
