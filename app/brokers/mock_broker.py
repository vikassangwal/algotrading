from typing import Any, Dict, List, Optional
import uuid
import datetime
from app.brokers.base import BaseBroker

class MockBroker(BaseBroker):
    """
    A simulated broker for paper trading and backtesting.
    Does not require any real API credentials.
    """
    def __init__(self, starting_capital: float = 1000000.0):
        self.capital = starting_capital
        self.used_margin = 0.0
        self.orders = {}
        self.positions = {}
        self.trades = []
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def get_profile(self) -> Dict[str, Any]:
        return {"user_id": "MOCK_USER_001", "name": "Mock Trading Account", "broker": "PaperTrader"}

    def get_funds(self) -> Dict[str, Any]:
        available = self.capital - self.used_margin
        return {
            "net": self.capital,
            "available_cash": available,
            "used_margin": self.used_margin
        }

    def place_order(
        self, symbol: str, quantity: int, side: str, order_type: str,
        price: Optional[float] = None, trigger_price: Optional[float] = None, **kwargs
    ) -> Dict[str, Any]:
        
        order_id = f"MOCK_{uuid.uuid4().hex[:8].upper()}"
        
        # Estimate margin requirement (mock 100% margin for simplicity)
        est_price = price if price else 100.0 # arbitrary market price fallback
        margin_required = est_price * quantity
        
        if side.upper() == "BUY" and margin_required > (self.capital - self.used_margin):
            return {"status": "rejected", "order_id": order_id, "reason": "Insufficient Funds"}

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "side": side.upper(),
            "order_type": order_type.upper(),
            "price": price,
            "status": "FILLED", # Auto-fill in mock mode
            "timestamp": datetime.datetime.now().isoformat(),
            "average_price": est_price
        }
        
        self.orders[order_id] = order
        
        # Adjust margins & positions
        if side.upper() == "BUY":
            self.used_margin += margin_required
            pos = self.positions.get(symbol, {"quantity": 0, "average_price": 0})
            total_cost = (pos["quantity"] * pos["average_price"]) + margin_required
            pos["quantity"] += quantity
            pos["average_price"] = total_cost / pos["quantity"]
            self.positions[symbol] = pos
        else:
            self.used_margin -= margin_required
            pos = self.positions.get(symbol, {"quantity": 0, "average_price": 0})
            pos["quantity"] -= quantity
            if pos["quantity"] == 0:
                del self.positions[symbol]
            else:
                self.positions[symbol] = pos
                
        self.trades.append(order)

        return {"status": "success", "order_id": order_id, "message": "Order Placed Successfully"}

    def modify_order(self, order_id: str, **kwargs) -> Dict[str, Any]:
        if order_id in self.orders and self.orders[order_id]["status"] == "PENDING":
            return {"status": "success", "order_id": order_id}
        return {"status": "rejected", "reason": "Order already filled or cancelled"}

    def cancel_order(self, order_id: str, **kwargs) -> Dict[str, Any]:
        if order_id in self.orders and self.orders[order_id]["status"] == "PENDING":
            self.orders[order_id]["status"] = "CANCELLED"
            return {"status": "success", "order_id": order_id}
        return {"status": "rejected", "reason": "Cannot cancel completed order"}

    def get_order_history(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if order_id:
            return [self.orders.get(order_id)] if order_id in self.orders else []
        return list(self.orders.values())

    def get_trades(self) -> List[Dict[str, Any]]:
        return self.trades

    def get_positions(self) -> List[Dict[str, Any]]:
        return [{"symbol": k, **v} for k, v in self.positions.items()]

    def get_holdings(self) -> List[Dict[str, Any]]:
        return []

    def get_historical_data(self, symbol, interval, start_time, end_time, **kwargs) -> List:
        return []

    def get_live_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        return {s: {"last_price": 100.0} for s in symbols}
