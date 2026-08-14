"""
Order Management System (OMS) Engine - Advanced Features
Implements Bracket Orders, Trailing Stop Loss, and Scale In/Out logic.
"""

from typing import List, Dict, Optional
import uuid

class OrderStatus:
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType:
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"

class Order:
    def __init__(self, symbol: str, quantity: float, side: str, order_type: str, price: Optional[float] = None, parent_id: Optional[str] = None):
        self.order_id = str(uuid.uuid4())
        self.parent_id = parent_id
        self.symbol = symbol
        self.quantity = quantity
        self.side = side  # "BUY" or "SELL"
        self.order_type = order_type
        self.price = price
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.average_price = 0.0

class BracketOrder:
    """
    Bracket order encapsulates a main order and its associated profit target and stop loss orders.
    """
    def __init__(self, main_order: Order, take_profit_price: float, stop_loss_price: float):
        self.main_order = main_order
        self.take_profit_order = Order(
            symbol=main_order.symbol,
            quantity=main_order.quantity,
            side="SELL" if main_order.side == "BUY" else "BUY",
            order_type=OrderType.TAKE_PROFIT,
            price=take_profit_price,
            parent_id=main_order.order_id
        )
        self.stop_loss_order = Order(
            symbol=main_order.symbol,
            quantity=main_order.quantity,
            side="SELL" if main_order.side == "BUY" else "BUY",
            order_type=OrderType.STOP_LOSS,
            price=stop_loss_price,
            parent_id=main_order.order_id
        )
        self.status = OrderStatus.PENDING
        
class IcebergOrder:
    """
    Iceberg order splits a large quantity into smaller chunks (display quantity).
    """
    def __init__(self, symbol: str, total_quantity: float, side: str, order_type: str, price: Optional[float], display_quantity: float):
        self.iceberg_id = str(uuid.uuid4())
        self.symbol = symbol
        self.total_quantity = total_quantity
        self.side = side
        self.order_type = order_type
        self.price = price
        self.display_quantity = display_quantity
        self.filled_quantity = 0.0
        self.active_child_order: Optional[Order] = None
        self.status = OrderStatus.PENDING

    def get_next_child_order(self) -> Optional[Order]:
        remaining = self.total_quantity - self.filled_quantity
        if remaining <= 0:
            return None
        qty = min(remaining, self.display_quantity)
        self.active_child_order = Order(
            self.symbol, qty, self.side, self.order_type, self.price, parent_id=self.iceberg_id
        )
        return self.active_child_order
        
class TrailingStopOrder(Order):
    """
    Trailing stop loss order.
    """
    def __init__(self, symbol: str, quantity: float, side: str, trail_amount: float, is_percent: bool = False, current_market_price: Optional[float] = None, parent_id: Optional[str] = None):
        super().__init__(symbol, quantity, side, OrderType.TRAILING_STOP, parent_id=parent_id)
        self.trail_amount = trail_amount
        self.is_percent = is_percent
        
        # Calculate initial stop price based on current market price
        if current_market_price is not None:
            self._update_stop_price(current_market_price)
        else:
            self.price = None

    def _update_stop_price(self, current_market_price: float):
        trail_value = self.trail_amount
        if self.is_percent:
            trail_value = current_market_price * (self.trail_amount / 100.0)
            
        if self.side == "SELL":
            # For a long position, stop loss is below current price
            new_stop_price = current_market_price - trail_value
            if self.price is None or new_stop_price > self.price:
                self.price = new_stop_price
        else:
            # For a short position, stop loss is above current price
            new_stop_price = current_market_price + trail_value
            if self.price is None or new_stop_price < self.price:
                self.price = new_stop_price

    def update_market_price(self, current_market_price: float):
        """Called when market price updates to potentially adjust the trailing stop."""
        self._update_stop_price(current_market_price)


class ScaleStrategy:
    """
    Logic for scaling in or scaling out of a position.
    """
    def __init__(self, symbol: str, total_quantity: float, side: str, steps: int, price_step: float, initial_price: float):
        self.symbol = symbol
        self.total_quantity = total_quantity
        self.side = side
        self.steps = steps
        self.price_step = price_step
        self.initial_price = initial_price
        self.orders: List[Order] = []
        self._generate_orders()

    def _generate_orders(self):
        qty_per_step = self.total_quantity / self.steps
        for i in range(self.steps):
            # For scaling in (buy), prices typically go down. For scaling out (sell), prices typically go up.
            price_adjustment = i * self.price_step
            if self.side == "BUY":
                # Assuming scaling in on a pullback
                step_price = self.initial_price - price_adjustment 
            else:
                # Assuming scaling out on a rally
                step_price = self.initial_price + price_adjustment
                
            order = Order(
                symbol=self.symbol,
                quantity=qty_per_step,
                side=self.side,
                order_type=OrderType.LIMIT,
                price=step_price
            )
            self.orders.append(order)

    def get_orders(self) -> List[Order]:
        return self.orders


class AdvancedOMSEngine:
    def __init__(self):
        self.active_orders: Dict[str, Order] = {}
        self.bracket_orders: Dict[str, BracketOrder] = {}
        self.trailing_stops: Dict[str, TrailingStopOrder] = {}
        self.iceberg_orders: Dict[str, IcebergOrder] = {}

    def place_iceberg_order(self, symbol: str, total_quantity: float, side: str, order_type: str, price: float, display_quantity: float) -> IcebergOrder:
        iceberg = IcebergOrder(symbol, total_quantity, side, order_type, price, display_quantity)
        self.iceberg_orders[iceberg.iceberg_id] = iceberg
        child = iceberg.get_next_child_order()
        if child:
            self.active_orders[child.order_id] = child
        print(f"Iceberg order placed. ID: {iceberg.iceberg_id}, Total: {total_quantity}, Display: {display_quantity}")
        return iceberg

    def place_bracket_order(self, main_order: Order, take_profit_price: float, stop_loss_price: float) -> BracketOrder:
        bracket = BracketOrder(main_order, take_profit_price, stop_loss_price)
        self.bracket_orders[bracket.main_order.order_id] = bracket
        self.active_orders[bracket.main_order.order_id] = bracket.main_order
        # Note: Take profit and stop loss orders are typically held pending until main order is filled
        print(f"Bracket order placed. Main Order ID: {main_order.order_id}")
        return bracket

    def place_trailing_stop(self, symbol: str, quantity: float, side: str, trail_amount: float, is_percent: bool, current_market_price: float) -> TrailingStopOrder:
        ts_order = TrailingStopOrder(symbol, quantity, side, trail_amount, is_percent, current_market_price)
        self.trailing_stops[ts_order.order_id] = ts_order
        self.active_orders[ts_order.order_id] = ts_order
        print(f"Trailing stop order placed. Order ID: {ts_order.order_id}, Initial Stop Price: {ts_order.price}")
        return ts_order

    def execute_scale_in_out(self, strategy: ScaleStrategy):
        orders = strategy.get_orders()
        for order in orders:
            self.active_orders[order.order_id] = order
            print(f"Scale order placed: {order.side} {order.quantity} @ {order.price} (ID: {order.order_id})")

    def update_market_price(self, symbol: str, current_price: float):
        """Update market price to trigger/adjust trailing stops or limits."""
        for ts_id, ts_order in self.trailing_stops.items():
            if ts_order.symbol == symbol and ts_order.status in [OrderStatus.PENDING, OrderStatus.OPEN]:
                old_price = ts_order.price
                ts_order.update_market_price(current_price)
                if old_price != ts_order.price:
                    print(f"Trailing Stop {ts_order.order_id} updated to {ts_order.price}")

    def on_order_fill(self, order_id: str):
        """Handle order fills, especially useful for bracket orders (OCO logic)."""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order.status = OrderStatus.FILLED
            print(f"Order {order_id} FILLED.")
            
            # OCO Logic for bracket orders
            parent_id = order.parent_id
            if parent_id and parent_id in self.bracket_orders:
                bracket = self.bracket_orders[parent_id]
                if order.order_type == OrderType.TAKE_PROFIT:
                    bracket.stop_loss_order.status = OrderStatus.CANCELLED
                    print(f"Take profit hit. Cancelling Stop Loss {bracket.stop_loss_order.order_id}")
                elif order.order_type == OrderType.STOP_LOSS:
                    bracket.take_profit_order.status = OrderStatus.CANCELLED
                    print(f"Stop loss hit. Cancelling Take Profit {bracket.take_profit_order.order_id}")
            
            # If main order in bracket is filled, activate TP/SL
            if order_id in self.bracket_orders:
                bracket = self.bracket_orders[order_id]
                self.active_orders[bracket.take_profit_order.order_id] = bracket.take_profit_order
                self.active_orders[bracket.stop_loss_order.order_id] = bracket.stop_loss_order
                print(f"Main bracket order filled. Activated TP ({bracket.take_profit_order.order_id}) and SL ({bracket.stop_loss_order.order_id}).")

            # Iceberg logic: if a child order fills, create the next one
            if parent_id and parent_id in self.iceberg_orders:
                iceberg = self.iceberg_orders[parent_id]
                iceberg.filled_quantity += order.quantity
                if iceberg.filled_quantity >= iceberg.total_quantity:
                    iceberg.status = OrderStatus.FILLED
                    print(f"Iceberg order {iceberg.iceberg_id} fully FILLED.")
                else:
                    next_child = iceberg.get_next_child_order()
                    if next_child:
                        self.active_orders[next_child.order_id] = next_child
                        print(f"Iceberg {iceberg.iceberg_id} spawned next child order {next_child.order_id} for qty {next_child.quantity}.")
