"""
Advanced Risk Management System (RMS)
Handles Daily Loss Limits, Drawdown Protection, and an Emergency Kill Switch.
"""

from typing import Dict, Any
from datetime import datetime

class RiskManagementSystem:
    def __init__(
        self,
        daily_loss_limit: float = 1000.0,
        max_drawdown_percent: float = 5.0,
        initial_equity: float = 100000.0
    ):
        """
        Initialize the Risk Management System.
        
        :param daily_loss_limit: Maximum allowed loss in a single day.
        :param max_drawdown_percent: Maximum allowed drawdown percentage from peak equity.
        :param initial_equity: Starting equity of the account.
        """
        self.daily_loss_limit = daily_loss_limit
        self.max_drawdown_percent = max_drawdown_percent
        self.initial_equity = initial_equity
        
        # State variables
        self.current_equity = initial_equity
        self.peak_equity = initial_equity
        self.daily_loss = 0.0
        
        # Kill switch state
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.kill_switch_timestamp = None

    def update_equity(self, current_equity: float) -> None:
        """
        Update the current equity and recalculate peak equity.
        """
        self.current_equity = current_equity
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

    def add_trade_pnl(self, pnl: float) -> None:
        """
        Add the PnL of a closed trade. 
        Updates the daily loss if the PnL is negative.
        """
        if pnl < 0:
            self.daily_loss += abs(pnl)

    def activate_kill_switch(self, reason: str = "Manual Intervention") -> None:
        """
        Activate the emergency kill switch to halt all trading.
        """
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        self.kill_switch_timestamp = datetime.now()
        
    def deactivate_kill_switch(self) -> None:
        """
        Deactivate the emergency kill switch.
        """
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.kill_switch_timestamp = None

    def reset_daily_metrics(self) -> None:
        """
        Reset daily tracking metrics (e.g., at the start of a new trading day).
        """
        self.daily_loss = 0.0

    def check_drawdown(self) -> bool:
        """
        Check if the current drawdown exceeds the maximum allowed drawdown.
        
        :return: True if drawdown limit is breached, False otherwise.
        """
        if self.peak_equity <= 0:
            return False
            
        drawdown_amount = self.peak_equity - self.current_equity
        drawdown_percent = (drawdown_amount / self.peak_equity) * 100.0
        
        return drawdown_percent >= self.max_drawdown_percent

    def check_daily_loss(self) -> bool:
        """
        Check if the daily loss limit has been breached.
        
        :return: True if daily loss limit is breached, False otherwise.
        """
        return self.daily_loss >= self.daily_loss_limit

    def is_trading_allowed(self) -> Dict[str, Any]:
        """
        Comprehensive check to determine if trading should be allowed.
        
        :return: A dictionary containing the status and reason if halted.
        """
        if self.kill_switch_active:
            return {
                "allowed": False,
                "reason": f"Kill Switch Active: {self.kill_switch_reason} at {self.kill_switch_timestamp}"
            }
            
        if self.check_daily_loss():
            return {
                "allowed": False,
                "reason": f"Daily Loss Limit Breached: {self.daily_loss} >= {self.daily_loss_limit}"
            }
            
        if self.check_drawdown():
            drawdown_amount = self.peak_equity - self.current_equity
            drawdown_percent = (drawdown_amount / self.peak_equity) * 100.0 if self.peak_equity > 0 else 0
            return {
                "allowed": False,
                "reason": f"Max Drawdown Breached: {drawdown_percent:.2f}% >= {self.max_drawdown_percent}%"
            }
            
        return {
            "allowed": True,
            "reason": "Risk parameters within acceptable limits."
        }
