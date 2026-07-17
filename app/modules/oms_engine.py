from enum import Enum
from typing import Dict, Optional
import uuid
import datetime

class OrderState(Enum):
    PENDING = "Pending"
    FILLED = "Filled"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"

class OrderType(Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    BRACKET = "Bracket"
    TRAILING_STOP = "Trailing_Stop"
    SCALE = "Scale"

class OrderAction(Enum):
    BUY = "Buy"
    SELL = "Sell"

class Order:
    def __init__(self, symbol: str, action: OrderAction, order_type: OrderType, quantity: int, price: Optional[float] = None,
                 target_price: Optional[float] = None, stop_loss_price: Optional[float] = None,
                 trailing_amount: Optional[float] = None, scale_steps: Optional[int] = None,
                 scale_price_increment: Optional[float] = None, parent_order_id: Optional[str] = None):
        self.order_id = str(uuid.uuid4())
        self.symbol = symbol
        self.action = action
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.target_price = target_price
        self.stop_loss_price = stop_loss_price
        self.trailing_amount = trailing_amount
        self.scale_steps = scale_steps
        self.scale_price_increment = scale_price_increment
        self.parent_order_id = parent_order_id
        self.state = OrderState.PENDING
        self.timestamp = datetime.datetime.now()
        self.filled_quantity = 0
        self.average_price = 0.0
        self.rejection_reason = ""

class OrderManagementSystem:
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        # Placeholders for account balance and margins
        self.available_margin = 100000.0
        self.price_limits = {
            "MIN_PRICE": 0.01,
            "MAX_PRICE": 100000.0
        }

    def place_order(self, order: Order) -> str:
        if not self._validate_order(order):
            order.state = OrderState.REJECTED
            self.orders[order.order_id] = order
            return order.order_id
        
        self.orders[order.order_id] = order
        
        # Handle Scale In/Out by generating child limit orders
        if order.order_type == OrderType.SCALE and order.scale_steps and order.scale_price_increment:
            base_qty = order.quantity // order.scale_steps
            rem_qty = order.quantity % order.scale_steps
            base_price = order.price or 0.0
            
            for i in range(order.scale_steps):
                qty = base_qty + (rem_qty if i == order.scale_steps - 1 else 0)
                # Adjust price: e.g. Buy scale down, Sell scale up
                price_adj = (order.scale_price_increment * i) * (-1 if order.action == OrderAction.BUY else 1)
                child_price = base_price + price_adj
                
                child_order = Order(
                    symbol=order.symbol, action=order.action, order_type=OrderType.LIMIT,
                    quantity=qty, price=child_price, parent_order_id=order.order_id
                )
                self.orders[child_order.order_id] = child_order
                self._route_to_matching_engine(child_order)
            
            # The parent scale order itself tracks its children and is considered conceptually filled/active
            order.state = OrderState.FILLED
            return order.order_id

        self._route_to_matching_engine(order)
        return order.order_id

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.state == OrderState.PENDING:
                order.state = OrderState.CANCELLED
                return True
        return False

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)

    def _validate_order(self, order: Order) -> bool:
        # Price limit check for limit, bracket, and scale orders
        if order.order_type in [OrderType.LIMIT, OrderType.BRACKET, OrderType.SCALE]:
            if order.price is None:
                order.rejection_reason = f"Price required for {order.order_type.name} order"
                return False
            if order.price < self.price_limits["MIN_PRICE"] or order.price > self.price_limits["MAX_PRICE"]:
                order.rejection_reason = "Price out of bounds"
                return False

        # Bracket Order specific validation
        if order.order_type == OrderType.BRACKET:
            if order.target_price is None or order.stop_loss_price is None:
                order.rejection_reason = "Target and Stop Loss prices required for BRACKET order"
                return False

        # Trailing Stop specific validation
        if order.order_type == OrderType.TRAILING_STOP:
            if order.trailing_amount is None or order.trailing_amount <= 0:
                order.rejection_reason = "Valid trailing amount required for TRAILING_STOP order"
                return False

        # Scale Order specific validation
        if order.order_type == OrderType.SCALE:
            if not order.scale_steps or order.scale_steps <= 1:
                order.rejection_reason = "Scale steps must be > 1 for SCALE order"
                return False
            if not order.scale_price_increment or order.scale_price_increment <= 0:
                order.rejection_reason = "Valid scale price increment required for SCALE order"
                return False

        # Margin check (simplified)
        estimated_cost = 0.0
        if order.order_type in [OrderType.LIMIT, OrderType.BRACKET, OrderType.SCALE]:
            estimated_cost = order.quantity * (order.price or 0.0)
        elif order.order_type in [OrderType.MARKET, OrderType.TRAILING_STOP]:
            # Assumed cost for market/trailing stop order validation placeholder
            estimated_cost = order.quantity * 100.0 

        if order.action == OrderAction.BUY and estimated_cost > self.available_margin:
            order.rejection_reason = "Insufficient margin"
            return False
            
        if order.quantity <= 0:
            order.rejection_reason = "Quantity must be greater than zero"
            return False

        return True

    def _route_to_matching_engine(self, order: Order):
        """
        Routes the order to the active broker.
        """
        print(f"Routing order {order.order_id} to active broker.")
        from app.brokers.factory import BrokerFactory
        # In a real app, config would be passed down. Defaulting to mock for safety.
        broker = BrokerFactory.get_broker("mock")
        broker.connect()
        
        response = broker.place_order(
            symbol=order.symbol,
            quantity=order.quantity,
            side=order.action.value,
            order_type=order.order_type.value,
            price=order.price
        )
        
        if response.get("status") == "success":
            order.state = OrderState.FILLED
            order.filled_quantity = order.quantity
            order.average_price = order.price if order.price else 100.0
        else:
            order.state = OrderState.REJECTED
            order.rejection_reason = response.get("reason", "Broker rejected order")
            
        # We handle OCO Bracket generation below if filled
        if order.state == OrderState.FILLED:
            if order.action == OrderAction.BUY:
                self.available_margin -= (order.filled_quantity * order.average_price)
            elif order.action == OrderAction.SELL:
                self.available_margin += (order.filled_quantity * order.average_price)

            # Generate OCO (Target + SL) child orders for BRACKET orders once filled
            if order.order_type == OrderType.BRACKET and order.target_price and order.stop_loss_price:
                exit_action = OrderAction.SELL if order.action == OrderAction.BUY else OrderAction.BUY
                
                # Target Limit Order
                target_order = Order(
                    symbol=order.symbol, action=exit_action, order_type=OrderType.LIMIT,
                    quantity=order.filled_quantity, price=order.target_price, parent_order_id=order.order_id
                )
                self.orders[target_order.order_id] = target_order
                print(f"Generated Target Order {target_order.order_id} at {order.target_price} for Bracket Order {order.order_id}")
                
                # Stop Loss Order (simplified as LIMIT here for demonstration)
                stop_loss_order = Order(
                    symbol=order.symbol, action=exit_action, order_type=OrderType.LIMIT,
                    quantity=order.filled_quantity, price=order.stop_loss_price, parent_order_id=order.order_id
                )
                self.orders[stop_loss_order.order_id] = stop_loss_order
                print(f"Generated Stop Loss Order {stop_loss_order.order_id} at {order.stop_loss_price} for Bracket Order {order.order_id}")
