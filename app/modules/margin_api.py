class MarginAPI:
    """
    MarginAPI class to calculate required margin for stock and option orders.
    """
    
    def __init__(self, provider=None):
        """
        Initialize the Margin API.
        """
        self.provider = provider

    def calculate_margin(self, symbol: str, instrument_type: str, order_type: str, quantity: int, price: float) -> float:
        """
        Calculate the required margin for a given order.

        Args:
            symbol (str): The trading symbol.
            instrument_type (str): Type of instrument (e.g., 'stock', 'option').
            order_type (str): Type of order ('buy', 'sell').
            quantity (int): Number of units to trade.
            price (float): Price per unit.

        Returns:
            float: The calculated required margin.
        """
        if self.provider and hasattr(self.provider, 'get_margin'):
            try:
                margin = self.provider.get_margin(symbol, instrument_type, order_type, quantity, price)
                if margin is not None:
                    return margin
            except Exception:
                pass

        total_value = float(quantity) * float(price)
        instrument = instrument_type.lower()
        side = order_type.lower()

        if instrument == 'stock':
            if side == 'buy':
                return total_value
            elif side == 'sell':
                # Standard margin proxy for short selling stock
                return total_value * 0.20
                
        elif instrument == 'option':
            if side == 'buy':
                # Margin for buying options is the premium
                return total_value
            elif side == 'sell':
                # Standard margin proxy for selling options
                return total_value * 5.0
                
        # Default margin requirement
        return total_value
