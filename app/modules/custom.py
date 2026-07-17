from typing import List, Dict, Any
from .base import AnalysisModule, ModuleSignal
from ..config import config

class CustomStrategyModule(AnalysisModule):
    @property
    def name(self) -> str:
        return "custom_strategies"

    def analyze(self, symbol: str, **kwargs: Any) -> ModuleSignal:
        if not config.custom_strategies:
            return ModuleSignal(
                score=0.0,
                confidence=0.0,
                reasons=["No custom strategies defined."]
            )

        # Get latest data
        try:
            quote = self.provider.get_quote(symbol)
            ltp = quote.ltp
        except Exception:
            ltp = 0.0
            
        data_points = {
            "LTP": ltp,
            "RSI": 50.0, 
            "MACD": 1.0,
            "VOLUME": 1000000
        }
        
        buy_votes = 0
        sell_votes = 0
        reasons = []

        for strat in config.custom_strategies:
            indicator = strat.get("indicator", "LTP").upper()
            operator = strat.get("operator", "==")
            value = float(strat.get("value", 0))
            action = strat.get("action", "BUY").upper()
            
            actual_val = data_points.get(indicator, 0)
            
            condition_met = False
            if operator == ">" and actual_val > value: condition_met = True
            elif operator == "<" and actual_val < value: condition_met = True
            elif operator == "==" and actual_val == value: condition_met = True
            
            if condition_met:
                reasons.append(f"Custom Rule Met: {strat.get('name', 'Rule')} ({indicator} {operator} {value}) -> {action}")
                if action == "BUY":
                    buy_votes += 1
                elif action == "SELL":
                    sell_votes += 1
                    
        total_votes = buy_votes + sell_votes
        if total_votes == 0:
            return ModuleSignal(score=0.0, confidence=0.0, reasons=["No custom rules triggered."])
            
        score = (buy_votes - sell_votes) / total_votes
        
        return ModuleSignal(
            score=score,
            confidence=0.9,
            reasons=reasons
        )
