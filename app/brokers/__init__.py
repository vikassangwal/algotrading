"""
Production Brokers Package
==========================
Exports all production-ready broker implementations
"""

from .production_base import (
    ProductionBrokerBase,
    BrokerFactory,
    Order,
    Position,
    AccountInfo,
    OrderStatus,
    OrderSide,
    OrderType,
    OrderValidity,
    CircuitBreaker,
    RateLimiter,
    RetryPolicy,
    BrokerError,
    AuthenticationError,
    RateLimitError,
    OrderRejectedError,
    ConnectionError,
    CircuitBreakerOpenError
)

# Import all broker implementations
from .zerodha_production import ZerodhaProductionBroker
from .dhan_production import DhanProductionBroker
from .upstox_production import UpstoxProductionBroker

# Register all brokers
BrokerFactory.register('zerodha', ZerodhaProductionBroker)
BrokerFactory.register('dhan', DhanProductionBroker)
BrokerFactory.register('upstox', UpstoxProductionBroker)

# Also keep legacy imports for backward compatibility
try:
    from .zerodha_broker import ZerodhaBroker
    from .dhan_broker import DhanBroker
    from .mock_broker import MockBroker
    from .base import BaseBroker
except ImportError:
    pass

__all__ = [
    # Base classes
    'ProductionBrokerBase',
    'BrokerFactory',
    'Order',
    'Position',
    'AccountInfo',
    'OrderStatus',
    'OrderSide',
    'OrderType',
    'OrderValidity',
    'CircuitBreaker',
    'RateLimiter',
    'RetryPolicy',
    'BrokerError',
    'AuthenticationError',
    'RateLimitError',
    'OrderRejectedError',
    'ConnectionError',
    'CircuitBreakerOpenError',

    # Production brokers
    'ZerodhaProductionBroker',
    'DhanProductionBroker',
    'UpstoxProductionBroker',

    # Legacy (if available)
    'ZerodhaBroker',
    'DhanBroker',
    'MockBroker',
    'BaseBroker',
]

# Convenience function
def create_broker(broker_name: str, **kwargs) -> ProductionBrokerBase:
    """Create a production broker instance"""
    return BrokerFactory.create(broker_name, **kwargs)

def get_available_brokers() -> list:
    """Get list of available production brokers"""
    return BrokerFactory.get_available()