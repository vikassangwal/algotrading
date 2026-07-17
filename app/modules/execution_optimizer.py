import time
import logging
import asyncio

logger = logging.getLogger(__name__)

class ExecutionOptimizer:
    """
    Execution Optimizer handles:
    - Slippage tracking
    - Estimated brokerage calculations
    - Auto-reconnect logic if WebSocket/Broker connection drops
    """
    
    def __init__(self, broker_client=None, config=None):
        self.broker_client = broker_client
        self.config = config or {}
        
        # Slippage stats
        self.total_slippage = 0.0
        self.trades_tracked = 0
        
        # Brokerage rates (example defaults, can be overridden by config)
        self.brokerage_rates = self.config.get('brokerage_rates', {
            'equity': 0.0001,  # 0.01%
            'options': 20.0,   # Flat 20 per trade
            'futures': 0.0001  # 0.01%
        })
        
        # Reconnect parameters
        self.max_retries = self.config.get('max_retries', 5)
        self.base_retry_delay = self.config.get('base_retry_delay', 1.0)
        
    def track_slippage(self, expected_price: float, executed_price: float, quantity: int, side: str) -> float:
        """
        Calculates and tracks slippage for a given trade.
        Positive slippage means unfavorable movement, negative means price improvement.
        """
        if side.lower() == 'buy':
            slippage = (executed_price - expected_price) * quantity
        elif side.lower() == 'sell':
            slippage = (expected_price - executed_price) * quantity
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'.")
            
        self.total_slippage += slippage
        self.trades_tracked += 1
        
        logger.info(f"Slippage tracked: {slippage:.2f} (Expected: {expected_price}, Executed: {executed_price}, Qty: {quantity}, Side: {side})")
        logger.info(f"Total Slippage so far: {self.total_slippage:.2f} over {self.trades_tracked} trades.")
        
        return slippage

    def calculate_estimated_brokerage(self, trade_value: float, asset_class: str = 'equity', quantity: int = 1) -> float:
        """
        Calculates estimated brokerage based on asset class.
        """
        asset_class = asset_class.lower()
        if asset_class not in self.brokerage_rates:
            logger.warning(f"Asset class '{asset_class}' not found in rates, returning 0.0")
            return 0.0
            
        rate = self.brokerage_rates[asset_class]
        
        # For simplicity: if rate > 1, it's considered flat rate (e.g. per order/lot)
        # If rate < 1, it's considered a percentage of trade value
        if asset_class == 'options':
            brokerage = rate # Flat rate per order
        else:
            brokerage = trade_value * rate
            
        logger.info(f"Estimated brokerage for {asset_class} trade of value {trade_value}: {brokerage:.2f}")
        return brokerage

    async def auto_reconnect(self, connection_func, *args, **kwargs):
        """
        Attempts to reconnect to a dropped connection using exponential backoff.
        connection_func should be an async function that establishes the connection and returns True on success.
        """
        retries = 0
        delay = self.base_retry_delay
        
        while retries < self.max_retries:
            try:
                logger.info(f"Attempting connection... (Attempt {retries + 1}/{self.max_retries})")
                success = await connection_func(*args, **kwargs)
                
                if success:
                    logger.info("Connection established successfully.")
                    return True
                else:
                    logger.warning("Connection function returned False.")
                    
            except Exception as e:
                logger.error(f"Connection error: {e}")
                
            retries += 1
            if retries < self.max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
                
        logger.critical("Max reconnect attempts reached. Could not establish connection.")
        return False
        
    def get_stats(self):
        """
        Returns execution statistics.
        """
        return {
            "total_slippage": self.total_slippage,
            "trades_tracked": self.trades_tracked,
            "average_slippage": self.total_slippage / self.trades_tracked if self.trades_tracked > 0 else 0.0
        }
