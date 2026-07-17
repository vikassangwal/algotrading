import pandas as pd
import numpy as np

class TCAEngine:
    """
    Transaction Cost Analysis (TCA) Engine.
    Calculates slippage and market impact.
    """
    
    def __init__(self):
        pass

    def calculate_slippage(self, expected_price: float, execution_price: float, side: str) -> float:
        """
        Calculate slippage for a trade.
        Slippage is the difference between the expected price and the execution price.
        Positive slippage means the execution was worse than expected.
        Negative slippage (price improvement) means the execution was better than expected.
        
        Args:
            expected_price (float): The price the trade was expected to execute at (e.g., arrival price).
            execution_price (float): The actual executed price.
            side (str): 'buy' or 'sell'.
            
        Returns:
            float: Slippage in basis points (bps).
        """
        if side.lower() == 'buy':
            slippage = (execution_price - expected_price) / expected_price
        elif side.lower() == 'sell':
            slippage = (expected_price - execution_price) / expected_price
        else:
            raise ValueError("Side must be 'buy' or 'sell'")
            
        return slippage * 10000  # Convert to basis points (bps)

    def calculate_market_impact(self, trade_size: float, adv: float, volatility: float, side: str = 'buy') -> float:
        """
        Calculate estimated market impact using a simple square root model.
        Model: Impact = volatility * sqrt(trade_size / ADV) * some_constant
        
        Args:
            trade_size (float): Size of the trade in shares/contracts.
            adv (float): Average Daily Volume of the asset.
            volatility (float): Daily volatility of the asset (in decimal, e.g., 0.02 for 2%).
            side (str): 'buy' or 'sell'.
            
        Returns:
            float: Estimated market impact in basis points (bps).
        """
        if adv <= 0:
            return 0.0
            
        # Constant for the impact model, typically empirically derived.
        gamma = 0.1 
        
        participation_rate = trade_size / adv
        impact = gamma * volatility * np.sqrt(participation_rate)
        
        return impact * 10000 # Convert to bps
        
    def analyze_trade_execution(self, trade_data: dict) -> dict:
        """
        Analyze a full trade execution to provide a TCA summary.
        
        Args:
            trade_data (dict): Dictionary containing trade details:
                - 'expected_price'
                - 'execution_price'
                - 'side'
                - 'trade_size'
                - 'adv'
                - 'volatility'
                
        Returns:
            dict: TCA results including slippage and impact.
        """
        required_keys = ['expected_price', 'execution_price', 'side', 'trade_size', 'adv', 'volatility']
        for key in required_keys:
            if key not in trade_data:
                raise ValueError(f"Missing required key in trade_data: {key}")
                
        slippage_bps = self.calculate_slippage(
            trade_data['expected_price'], 
            trade_data['execution_price'], 
            trade_data['side']
        )
        
        impact_bps = self.calculate_market_impact(
            trade_data['trade_size'],
            trade_data['adv'],
            trade_data['volatility'],
            trade_data['side']
        )
        
        return {
            'slippage_bps': slippage_bps,
            'estimated_market_impact_bps': impact_bps,
            'total_cost_bps': slippage_bps + impact_bps
        }
