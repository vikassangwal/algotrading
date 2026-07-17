"""
Corporate Actions Engine

This module provides a standalone engine to handle corporate actions 
such as Dividends and Stock Splits.
"""

from enum import Enum
from typing import Dict, List
from datetime import date

class ActionType(Enum):
    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"

class CorporateAction:
    def __init__(self, action_type: ActionType, symbol: str, ex_date: date):
        self.action_type = action_type
        self.symbol = symbol
        self.ex_date = ex_date

class Dividend(CorporateAction):
    def __init__(self, symbol: str, ex_date: date, amount: float):
        """
        :param amount: Cash amount per share.
        """
        super().__init__(ActionType.DIVIDEND, symbol, ex_date)
        self.amount = amount

class StockSplit(CorporateAction):
    def __init__(self, symbol: str, ex_date: date, ratio: float):
        """
        :param ratio: Number of new shares per old share (e.g., 2.0 for a 2-for-1 split).
        """
        super().__init__(ActionType.SPLIT, symbol, ex_date)
        self.ratio = ratio

class CorporateActionEngine:
    def __init__(self):
        self.actions: List[CorporateAction] = []

    def add_action(self, action: CorporateAction):
        """Register a new corporate action."""
        self.actions.append(action)

    def apply_to_portfolio(self, portfolio: Dict[str, Dict[str, float]], current_date: date):
        """
        Applies registered corporate actions to a portfolio for a specific date.
        
        :param portfolio: Dictionary mapping symbol to position details 
                          e.g. {"AAPL": {"shares": 100.0, "cash_dividend": 0.0}}
        :param current_date: The date to process actions for.
        """
        for action in self.actions:
            if action.ex_date == current_date and action.symbol in portfolio:
                position = portfolio[action.symbol]
                
                if action.action_type == ActionType.DIVIDEND:
                    dividend = action  # type: Dividend
                    current_div = position.get("cash_dividend", 0.0)
                    position["cash_dividend"] = current_div + (position["shares"] * dividend.amount)
                    
                elif action.action_type == ActionType.SPLIT:
                    split = action  # type: StockSplit
                    position["shares"] *= split.ratio

    def adjust_historical_prices(self, symbol: str, historical_prices: Dict[date, float]) -> Dict[date, float]:
        """
        Adjusts historical prices backward for splits and dividends.
        
        :param symbol: Ticker symbol to adjust.
        :param historical_prices: Dictionary of {date: close_price}.
        :return: A new dictionary with adjusted prices.
        """
        adjusted_prices = historical_prices.copy()
        
        # Sort actions by ex_date descending
        symbol_actions = sorted(
            [a for a in self.actions if a.symbol == symbol],
            key=lambda x: x.ex_date,
            reverse=True
        )
        
        for action in symbol_actions:
            for p_date in list(adjusted_prices.keys()):
                if p_date < action.ex_date:
                    if action.action_type == ActionType.DIVIDEND:
                        dividend = action  # type: Dividend
                        # Absolute adjustment for dividends
                        adjusted_prices[p_date] -= dividend.amount
                    elif action.action_type == ActionType.SPLIT:
                        split = action  # type: StockSplit
                        adjusted_prices[p_date] /= split.ratio
                        
        return adjusted_prices
