from typing import Any, Dict, List, Optional
from app.brokers.base import BaseBroker
import logging
import requests

logger = logging.getLogger("elco.broker.dhan")

class DhanBroker(BaseBroker):
    """
    DhanHQ Integration supporting both REST API and dhanhq package.
    """
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id or ""
        self.access_token = access_token or ""
        self.dhan = None
        self._connected = False

    def connect(self) -> bool:
        if not self.client_id or not self.access_token:
            logger.warning("Missing Dhan Client ID or Access Token")
            return False

        # Try direct REST API call to Dhan HQ
        try:
            headers = {
                "access-token": self.access_token,
                "client-id": self.client_id,
                "Content-Type": "application/json"
            }
            res = requests.get("https://api.dhan.co/fundlimit", headers=headers, timeout=8)
            if res.status_code == 200:
                self._connected = True
                logger.info("DhanHQ REST API connected successfully.")
                return True
            else:
                logger.warning(f"Dhan REST API response {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Dhan REST API ping error: {e}")

        # Fallback to dhanhq package
        try:
            from dhanhq import dhanhq
            self.dhan = dhanhq(self.client_id, self.access_token)
            self._connected = True
            logger.info("DhanHQ library connected successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect DhanHQ: {e}")
            return False

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def get_profile(self) -> Dict[str, Any]:
        return {"broker": "Dhan", "client_id": self.client_id}

    def get_funds(self) -> Dict[str, Any]:
        if not self.client_id or not self.access_token:
            return {"net": 0, "available_cash": 0, "used_margin": 0}

        try:
            headers = {
                "access-token": self.access_token,
                "client-id": self.client_id,
                "Content-Type": "application/json"
            }
            res = requests.get("https://api.dhan.co/fundlimit", headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json().get("data", {})
                return {
                    "net": data.get("availabelBalance", 0),
                    "available_cash": data.get("availabelBalance", 0),
                    "used_margin": data.get("utilizedAmount", 0)
                }
        except Exception as e:
            logger.error(f"Funds error: {e}")

        return {"net": 0, "available_cash": 0, "used_margin": 0}

    def place_order(self, symbol: str, action: str, qty: int, order_type: str = "MARKET", price: float = 0.0) -> Dict[str, Any]:
        if not self.client_id or not self.access_token:
            return {"status": "FAILED", "reason": "Missing Dhan credentials"}

        try:
            headers = {
                "access-token": self.access_token,
                "client-id": self.client_id,
                "Content-Type": "application/json"
            }
            payload = {
                "dhanClientId": self.client_id,
                "transactionType": action.upper(),
                "exchangeSegment": "NSE_EQ",
                "productType": "INTRADAY",
                "orderType": order_type.upper(),
                "validity": "DAY",
                "tradingSymbol": symbol.replace(".NS", ""),
                "quantity": qty,
                "price": price if order_type.upper() == "LIMIT" else 0
            }
            res = requests.post("https://api.dhan.co/orders", headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return {"status": "SUCCESS", "order_id": data.get("orderId"), "response": data}
            else:
                return {"status": "FAILED", "reason": res.text}
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            return {"status": "FAILED", "reason": str(e)}

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_orders(self) -> List[Dict[str, Any]]:
        return []
