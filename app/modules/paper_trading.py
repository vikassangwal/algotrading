import time
import random
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

# Setup basic logging
logger = logging.getLogger(__name__)

@dataclass
class Order:
    order_id: str
    symbol: str
    order_type: str  # 'MARKET', 'LIMIT'
    side: str  # 'BUY', 'SELL'
    quantity: float
    price: Optional[float]
    status: str = 'PENDING'
    created_at: float = field(default_factory=time.time)
    executed_at: Optional[float] = None
    executed_price: Optional[float] = None

class Simulator:
    def __init__(self, base_latency_ms: float = 50.0, latency_jitter_ms: float = 20.0, slippage_pct: float = 0.0001):
        """
        Initialize the Paper Trading Simulator.
        
        :param base_latency_ms: Base latency in milliseconds.
        :param latency_jitter_ms: Random jitter added to base latency in milliseconds.
        :param slippage_pct: Slippage percentage applied to market orders (e.g., 0.0001 for 1 bps).
        """
        self.base_latency_ms = base_latency_ms
        self.latency_jitter_ms = latency_jitter_ms
        self.slippage_pct = slippage_pct
        
        self.orders: Dict[str, Order] = {}
        self.latest_ticks: Dict[str, dict] = {}
        self.positions: Dict[str, float] = {}
        self.cash = 100000.0  # Initial cash
        
    def _generate_order_id(self) -> str:
        return f"ORDER_{int(time.time()*1000)}_{random.randint(1000, 9999)}"

    def on_tick(self, symbol: str, timestamp: float, bid: float, ask: float, last_price: float, volume: float):
        """
        Update the simulator with the latest tick data.
        """
        self.latest_ticks[symbol] = {
            'timestamp': timestamp,
            'bid': bid,
            'ask': ask,
            'last_price': last_price,
            'volume': volume
        }
        self._process_pending_orders(symbol)
        
    def place_order(self, symbol: str, order_type: str, side: str, quantity: float, price: Optional[float] = None) -> str:
        """
        Place a simulated order.
        """
        order_id = self._generate_order_id()
        order = Order(
            order_id=order_id,
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price
        )
        self.orders[order_id] = order
        logger.info(f"Placed {order_type} {side} order for {quantity} {symbol}. ID: {order_id}")
        
        # Try to process immediately if we have tick data
        if symbol in self.latest_ticks:
            self._process_pending_orders(symbol)
            
        return order_id
        
    def _calculate_latency(self) -> float:
        """Calculate simulated latency in seconds."""
        latency_ms = self.base_latency_ms + random.uniform(-self.latency_jitter_ms, self.latency_jitter_ms)
        return max(0.0, latency_ms / 1000.0)

    def _calculate_slippage(self, price: float, side: str) -> float:
        """Calculate execution price with slippage."""
        # Slippage usually worsens the execution price
        slippage_amount = price * self.slippage_pct
        if side == 'BUY':
            return price + slippage_amount
        else:
            return price - slippage_amount

    def _process_pending_orders(self, symbol: str):
        """
        Check pending orders and execute them if conditions are met, incorporating latency and slippage.
        """
        tick = self.latest_ticks.get(symbol)
        if not tick:
            return
            
        current_time = time.time()
        
        for order in self.orders.values():
            if order.symbol != symbol or order.status != 'PENDING':
                continue
                
            # Check latency
            latency = self._calculate_latency()
            if current_time - order.created_at < latency:
                continue  # Latency period hasn't passed yet
                
            # Try to execute
            if order.order_type == 'MARKET':
                # Execute at current bid/ask with slippage
                if order.side == 'BUY':
                    base_price = tick['ask'] if tick['ask'] > 0 else tick['last_price']
                else:
                    base_price = tick['bid'] if tick['bid'] > 0 else tick['last_price']
                    
                exec_price = self._calculate_slippage(base_price, order.side)
                self._execute_order(order, exec_price, current_time)
                
            elif order.order_type == 'LIMIT':
                if order.price is None:
                    order.status = 'REJECTED'
                    logger.error(f"Limit order {order.order_id} rejected due to missing price.")
                    continue
                    
                # Execute if limit price is reached (simplified matching without queue position)
                if order.side == 'BUY' and tick['ask'] <= order.price:
                    self._execute_order(order, order.price, current_time)
                elif order.side == 'SELL' and tick['bid'] >= order.price:
                    self._execute_order(order, order.price, current_time)

    def _execute_order(self, order: Order, price: float, current_time: float):
        """Execute the order and update positions and cash."""
        order.status = 'FILLED'
        order.executed_at = current_time
        order.executed_price = price
        
        # Update position
        current_pos = self.positions.get(order.symbol, 0.0)
        pos_change = order.quantity if order.side == 'BUY' else -order.quantity
        self.positions[order.symbol] = current_pos + pos_change
        
        # Update cash
        cash_change = - (pos_change * price)
        self.cash += cash_change
        
        logger.info(f"Order {order.order_id} FILLED at {price:.2f}. "
                    f"Position: {self.positions[order.symbol]}, Cash: {self.cash:.2f}")

    def get_order_status(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)
        
    def get_position(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0)
