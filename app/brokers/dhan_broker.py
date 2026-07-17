from typing import Any, Dict, List, Optional
from app.brokers.base import BaseBroker
import logging

logger = logging.getLogger("elco.broker.dhan")

class DhanBroker(BaseBroker):
    """
    DhanHQ Integration.
    Requires `dhanhq` python package.
    """
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.dhan = None
        self._connected = False

    def connect(self) -> bool:
        try:
            from dhanhq import dhanhq
            self.dhan = dhanhq(self.client_id, self.access_token)
            self._connected = True
            logger.info("DhanHQ connected successfully.")
            return True
        except ImportError:
            logger.error("dhanhq package not installed. Run: pip install dhanhq")
            return False
        except Exception as e:
            logger.error(f"Failed to connect DhanHQ: {e}")
            return False

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def get_profile(self) -> Dict[str, Any]:
        return {"broker": "Dhan"}

    def get_funds(self) -> Dict[str, Any]:
        if not self.dhan: return {"net": 0, "available_cash": 0, "used_margin": 0}
        try:
            funds = self.dhan.get_fund_limits()
            data = funds.get("data", {})
            return {
                "net": data.get("availabelBalance", 0),
                "available_cash": data.get("availabelBalance", 0),
                "used_margin": data.get("utilizedAmount", 0)
            }
        except Exception as e:
            logger.error(f"Funds error: {e}")
            return {"net": 0, "available_cash": 0, "used_margin": 0}

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str, price: Optional[float] = None, trigger_price: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        if not self.dhan: return {"status": "rejected", "reason": "Not connected"}
        try:
            order_id = self.dhan.place_order(
                security_id=symbol, # Requires Dhan specific security ID lookup in real env
                exchange_segment=self.dhan.NSE,
                transaction_type=self.dhan.BUY if side.upper() == "BUY" else self.dhan.SELL,
                quantity=quantity,
                order_type=self.dhan.MARKET if order_type.upper() == "MARKET" else self.dhan.LIMIT,
                product_type=self.dhan.INTRADAY,
                price=price or 0
            )
            return {"status": "success", "order_id": order_id}
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return {"status": "rejected", "reason": str(e)}

    def modify_order(self, order_id: str, **kwargs) -> Dict[str, Any]:
        pass

    def cancel_order(self, order_id: str, **kwargs) -> Dict[str, Any]:
        pass

    def get_order_history(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_trades(self) -> List[Dict[str, Any]]:
        return []

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        return []

    def get_historical_data(self, symbol, interval, start_time, end_time, **kwargs) -> List:
        return []

    def get_live_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        return {}
