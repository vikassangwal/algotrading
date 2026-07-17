"""
Module for calculating market breadth indicators.
"""

def calculate_advance_decline_ratio(advancing_stocks: int, declining_stocks: int) -> float:
    """
    Calculate the Advance/Decline (A/D) Ratio.
    
    The A/D Ratio is a market breadth indicator that compares the number of 
    stocks that closed higher against the number of stocks that closed lower.
    
    Args:
        advancing_stocks (int): Number of advancing stocks.
        declining_stocks (int): Number of declining stocks.
        
    Returns:
        float: The A/D Ratio. Returns 0.0 if both are 0. If declining_stocks is 0 
               and advancing_stocks > 0, returns float('inf').
    """
    if advancing_stocks < 0 or declining_stocks < 0:
        raise ValueError("Stock counts cannot be negative.")
        
    if declining_stocks == 0:
        if advancing_stocks == 0:
            return 0.0
        return float('inf')
        
    return advancing_stocks / declining_stocks

def calculate_advance_decline_spread(advancing_stocks: int, declining_stocks: int) -> int:
    """
    Calculate the Advance/Decline Spread.
    
    Args:
        advancing_stocks (int): Number of advancing stocks.
        declining_stocks (int): Number of declining stocks.
        
    Returns:
        int: The difference between advancing and declining stocks.
    """
    if advancing_stocks < 0 or declining_stocks < 0:
        raise ValueError("Stock counts cannot be negative.")
        
    return advancing_stocks - declining_stocks
