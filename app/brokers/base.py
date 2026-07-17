from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseBroker(ABC):
    """
    Abstract base class for multi-broker integration.
    All broker implementations should inherit from this class and implement its abstract methods.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Authenticate and establish a connection with the broker."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Close the connection with the broker."""
        pass

    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """Fetch the user profile and account details."""
        pass

    @abstractmethod
    def get_funds(self) -> Dict[str, Any]:
        """Fetch available funds and margin details."""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Place a new order.
        
        :param symbol: The trading symbol.
        :param quantity: The number of shares/contracts.
        :param side: 'BUY' or 'SELL'.
        :param order_type: 'MARKET', 'LIMIT', 'SL', etc.
        :param price: The limit price (required for LIMIT orders).
        :param trigger_price: The trigger price (required for SL orders).
        :param kwargs: Additional broker-specific parameters.
        :return: A dictionary containing the order ID and other details.
        """
        pass

    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Modify an existing open order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Cancel an open order."""
        pass

    @abstractmethod
    def get_order_history(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch the details of a specific order or all orders for the day."""
        pass

    @abstractmethod
    def get_trades(self) -> List[Dict[str, Any]]:
        """Fetch the executed trades for the day."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch the current open positions."""
        pass

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Fetch the portfolio holdings."""
        pass

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        interval: str,
        start_time: str,
        end_time: str,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Fetch historical price data (candles)."""
        pass

    @abstractmethod
    def get_live_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch live market quotes for the given symbols."""
        pass
