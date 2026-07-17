from typing import Optional
from app.brokers.base import BaseBroker
from app.brokers.mock_broker import MockBroker
from app.brokers.zerodha_broker import ZerodhaBroker
from app.brokers.dhan_broker import DhanBroker

class BrokerFactory:
    """
    Factory to instantiate the appropriate broker based on configuration.
    """
    @staticmethod
    def get_broker(broker_name: str, **kwargs) -> BaseBroker:
        broker_name = broker_name.lower().strip()
        
        if broker_name == "zerodha":
            return ZerodhaBroker(
                api_key=kwargs.get("api_key"),
                api_secret=kwargs.get("api_secret")
            )
        elif broker_name == "dhan":
            return DhanBroker(
                client_id=kwargs.get("api_key"),
                access_token=kwargs.get("api_secret")
            )
        elif broker_name == "mock" or not broker_name:
            return MockBroker(starting_capital=kwargs.get("capital", 1000000.0))
        else:
            raise ValueError(f"Unsupported broker: {broker_name}")
