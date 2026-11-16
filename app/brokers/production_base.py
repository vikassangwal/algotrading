"""
Production-Ready Broker Base Classes
=====================================
Institutional-grade broker abstraction with:
- Order state machine (pending → sent → acked → partial → filled/rejected/cancelled)
- Idempotency keys for duplicate protection
- Exponential backoff retry with jitter
- WebSocket reconnection with heartbeat
- Rate limiting compliance per broker
- Structured logging with correlation IDs
- Circuit breaker pattern
"""

import asyncio
import uuid
import time
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
import hashlib
import hmac
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order lifecycle states"""
    PENDING = "pending"           # Created locally, not sent
    SENT = "sent"                 # Sent to broker, awaiting ack
    ACKED = "acked"               # Broker acknowledged
    PARTIAL = "partial"           # Partially filled
    FILLED = "filled"             # Fully filled
    REJECTED = "rejected"         # Rejected by broker/exchange
    CANCELLED = "cancelled"       # Cancelled by user/system
    EXPIRED = "expired"           # Expired (IOC/GTD)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    SL = "sl"           # Stop Loss
    SLM = "slm"         # Stop Loss Market


class OrderValidity(Enum):
    DAY = "day"
    IOC = "ioc"         # Immediate or Cancel
    GTD = "gtd"         # Good Till Date


@dataclass
class Order:
    """Production order with full lifecycle tracking"""
    # Identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    broker_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None

    # Order details
    symbol: str = ""
    exchange: str = "NSE"
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: float = 0.0
    trigger_price: float = 0.0  # For SL/SLM
    validity: OrderValidity = OrderValidity.DAY
    disclosed_quantity: int = 0

    # Execution tracking
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: float = 0.0
    last_fill_price: float = 0.0
    last_fill_quantity: int = 0
    last_fill_time: Optional[datetime] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None
    first_fill_at: Optional[datetime] = None
    last_fill_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error tracking
    reject_reason: Optional[str] = None
    reject_code: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None

    # Metadata
    strategy_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    # Risk
    pre_trade_checks_passed: bool = False
    risk_check_details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'idempotency_key': self.idempotency_key,
            'broker_order_id': self.broker_order_id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'validity': self.validity.value,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'pending_quantity': self.quantity - self.filled_quantity,
            'average_price': self.average_price,
            'created_at': self.created_at.isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        }

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.SENT, OrderStatus.ACKED, OrderStatus.PARTIAL)

    @property
    def is_terminal(self) -> bool:
        return self.status in (OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED)

    @property
    def fill_rate(self) -> float:
        return self.filled_quantity / self.quantity if self.quantity > 0 else 0.0


@dataclass
class Position:
    """Real-time position tracking"""
    symbol: str
    exchange: str = "NSE"
    net_quantity: int = 0
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_value: float = 0.0
    sell_value: float = 0.0
    average_buy_price: float = 0.0
    average_sell_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    last_price: float = 0.0
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def average_price(self) -> float:
        if self.net_quantity > 0:
            return self.buy_value / self.buy_quantity if self.buy_quantity > 0 else 0.0
        elif self.net_quantity < 0:
            return self.sell_value / self.sell_quantity if self.sell_quantity > 0 else 0.0
        return 0.0


@dataclass
class AccountInfo:
    """Account and margin information"""
    account_id: str
    broker: str
    equity: float = 0.0
    margin_used: float = 0.0
    margin_available: float = 0.0
    span_margin: float = 0.0
    exposure_margin: float = 0.0
    var_margin: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    currency: str = "INR"
    updated_at: datetime = field(default_factory=datetime.utcnow)


class CircuitBreaker:
    """Circuit breaker pattern for broker resilience"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
        self.half_open_calls = 0

    def call(self, func: Callable, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                self.half_open_calls = 0
                logger.info("Circuit breaker entering half-open state")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        if self.state == "half_open" and self.half_open_calls >= self.half_open_max_calls:
            raise CircuitBreakerOpenError("Half-open call limit reached")

        try:
            if self.state == "half_open":
                self.half_open_calls += 1
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    async def acall(self, func: Callable, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                self.half_open_calls = 0
                logger.info("Circuit breaker entering half-open state")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        if self.state == "half_open" and self.half_open_calls >= self.half_open_max_calls:
            raise CircuitBreakerOpenError("Half-open call limit reached")

        try:
            if self.state == "half_open":
                self.half_open_calls += 1
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        self.failure_count = 0
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= 2:
                self.state = "closed"
                self.success_count = 0
                logger.info("Circuit breaker closed")

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class CircuitBreakerOpenError(Exception):
    pass


class RateLimiter:
    """Token bucket rate limiter per broker"""

    def __init__(self, rate: int, per: int = 1, burst: int = None):
        self.rate = rate
        self.per = per
        self.burst = burst or rate
        self.tokens = self.burst
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        async with self._lock:
            while self.tokens < tokens:
                self._refill()
                if self.tokens < tokens:
                    wait_time = (tokens - self.tokens) * self.per / self.rate
                    await asyncio.sleep(min(wait_time, 1.0))
            self.tokens -= tokens

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.rate / self.per
        self.tokens = min(self.burst, self.tokens + new_tokens)
        self.last_update = now


class RetryPolicy:
    """Exponential backoff with jitter"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: float = 0.1
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        # Add jitter
        jitter_range = delay * self.jitter
        return delay + (hashlib.md5(str(attempt).encode()).digest()[0] / 255 - 0.5) * 2 * jitter_range

    async def execute(self, func: Callable, *args, **kwargs):
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
        raise last_exception


class BrokerError(Exception):
    """Base broker exception"""
    def __init__(self, message: str, code: str = None, recoverable: bool = True):
        super().__init__(message)
        self.code = code
        self.recoverable = recoverable


class AuthenticationError(BrokerError):
    def __init__(self, message: str):
        super().__init__(message, code="AUTH_ERROR", recoverable=False)


class RateLimitError(BrokerError):
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, code="RATE_LIMIT", recoverable=True)
        self.retry_after = retry_after


class OrderRejectedError(BrokerError):
    def __init__(self, message: str, reject_code: str = None):
        super().__init__(message, code="ORDER_REJECTED", recoverable=False)
        self.reject_code = reject_code


class ConnectionError(BrokerError):
    def __init__(self, message: str):
        super().__init__(message, code="CONNECTION_ERROR", recoverable=True)


class ProductionBrokerBase(ABC):
    """
    Production-ready broker base class.
    All broker implementations must inherit from this.
    """

    def __init__(
        self,
        broker_name: str,
        api_key: str,
        api_secret: str,
        config: Dict = None
    ):
        self.broker_name = broker_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = config or {}

        # State
        self.connected = False
        self.authenticated = False
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.account: Optional[AccountInfo] = None

        # Resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.get('circuit_breaker_threshold', 5),
            recovery_timeout=self.config.get('circuit_breaker_timeout', 60)
        )
        self.rate_limiter = RateLimiter(
            rate=self.config.get('rate_limit', 10),
            per=1,
            burst=self.config.get('rate_limit_burst', 20)
        )
        self.retry_policy = RetryPolicy(
            max_retries=self.config.get('max_retries', 3),
            base_delay=self.config.get('retry_base_delay', 1.0),
            max_delay=self.config.get('retry_max_delay', 60.0)
        )

        # WebSocket
        self.ws = None
        self.ws_connected = False
        self.ws_reconnect_attempts = 0
        self.max_ws_reconnect_attempts = self.config.get('max_ws_reconnect', 10)
        self.ws_heartbeat_interval = self.config.get('ws_heartbeat', 30)
        self._ws_heartbeat_task = None
        self._ws_reconnect_task = None

        # Callbacks
        self.on_order_update: Optional[Callable] = None
        self.on_position_update: Optional[Callable] = None
        self.on_account_update: Optional[Callable] = None
        self.on_tick: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Idempotency store
        self._idempotency_store: Dict[str, Order] = {}

        # Metrics
        self.metrics = {
            'orders_sent': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'orders_cancelled': 0,
            'api_calls': 0,
            'api_errors': 0,
            'ws_reconnects': 0,
            'avg_latency_ms': 0.0,
        }

        logger.info(f"Initialized {broker_name} production broker")

    # ============================================================
    # Abstract methods - must be implemented by subclasses
    # ============================================================

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with broker API"""
        pass

    @abstractmethod
    async def place_order(self, order: Order) -> Order:
        """Place order with broker"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        pass

    @abstractmethod
    async def modify_order(self, order_id: str, **kwargs) -> Order:
        """Modify order"""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        pass

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get account info"""
        pass

    @abstractmethod
    async def connect_websocket(self) -> bool:
        """Connect to broker WebSocket for real-time data"""
        pass

    @abstractmethod
    async def disconnect_websocket(self):
        """Disconnect WebSocket"""
        pass

    @abstractmethod
    async def subscribe_market_data(self, symbols: List[str]):
        """Subscribe to market data"""
        pass

    @abstractmethod
    async def unsubscribe_market_data(self, symbols: List[str]):
        """Unsubscribe from market data"""
        pass

    # ============================================================
    # Production-ready wrapper methods
    # ============================================================

    async def place_order_safe(self, order: Order) -> Order:
        """Place order with full production safeguards"""
        start_time = time.time()

        # 1. Validate order
        self._validate_order(order)

        # 2. Check idempotency
        if order.idempotency_key in self._idempotency_store:
            existing = self._idempotency_store[order.idempotency_key]
            logger.warning(f"Duplicate order idempotency key: {order.idempotency_key}")
            return existing

        # 3. Rate limiting
        await self.rate_limiter.acquire()

        # 4. Circuit breaker
        async def _place():
            return await self.circuit_breaker.acall(self._place_order_internal, order)

        try:
            result = await self.retry_policy.execute(_place)

            # Track metrics
            latency = (time.time() - start_time) * 1000
            self.metrics['orders_sent'] += 1
            self.metrics['api_calls'] += 1
            self._update_avg_latency(latency)

            # Store for idempotency
            self._idempotency_store[order.idempotency_key] = result

            return result

        except CircuitBreakerOpenError:
            self.metrics['api_errors'] += 1
            raise ConnectionError(f"{self.broker_name} circuit breaker open")
        except RateLimitError as e:
            self.metrics['api_errors'] += 1
            await asyncio.sleep(e.retry_after)
            return await self.place_order_safe(order)
        except Exception as e:
            self.metrics['api_errors'] += 1
            logger.error(f"Order placement failed: {e}")
            raise

    async def _place_order_internal(self, order: Order) -> Order:
        """Internal order placement with state management"""
        # Update order state
        order.status = OrderStatus.SENT
        order.sent_at = datetime.utcnow()
        self.orders[order.id] = order

        # Call broker-specific implementation
        result = await self.place_order(order)

        # Update state based on result
        if result.status == OrderStatus.ACKED:
            order.acked_at = datetime.utcnow()
            order.broker_order_id = result.broker_order_id
        elif result.status == OrderStatus.REJECTED:
            order.reject_reason = result.reject_reason
            order.reject_code = result.reject_code
            self.metrics['orders_rejected'] += 1

        # Notify callback
        if self.on_order_update:
            await self._safe_callback(self.on_order_update, result)

        return result

    async def cancel_order_safe(self, order_id: str) -> bool:
        """Cancel order with safeguards"""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if not order.is_active:
            raise ValueError(f"Order not active: {order.status}")

        await self.rate_limiter.acquire()

        try:
            result = await self.retry_policy.execute(
                lambda: self.circuit_breaker.acall(self.cancel_order, order_id)
            )

            if result:
                order.status = OrderStatus.CANCELLED
                order.completed_at = datetime.utcnow()
                self.metrics['orders_cancelled'] += 1

                if self.on_order_update:
                    await self._safe_callback(self.on_order_update, order)

            return result

        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            raise

    async def get_order_status_safe(self, order_id: str) -> Order:
        """Get order status with caching"""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if order.is_terminal:
            return order

        await self.rate_limiter.acquire()

        try:
            updated = await self.retry_policy.execute(
                lambda: self.circuit_breaker.acall(self.get_order_status, order_id)
            )

            # Update local copy
            self.orders[order_id] = updated

            if self.on_order_update:
                await self._safe_callback(self.on_order_update, updated)

            return updated

        except Exception as e:
            logger.error(f"Get order status failed: {e}")
            raise

    # ============================================================
    # WebSocket management
    # ============================================================

    async def start_websocket(self, symbols: List[str] = None):
        """Start WebSocket with auto-reconnect"""
        if self.ws_connected:
            logger.warning("WebSocket already connected")
            return

        success = await self.connect_websocket()
        if not success:
            raise ConnectionError("Failed to connect WebSocket")

        if symbols:
            await self.subscribe_market_data(symbols)

        # Start heartbeat
        self._ws_heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"{self.broker_name} WebSocket started")

    async def stop_websocket(self):
        """Stop WebSocket cleanly"""
        if self._ws_heartbeat_task:
            self._ws_heartbeat_task.cancel()
            try:
                await self._ws_heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._ws_reconnect_task:
            self._ws_reconnect_task.cancel()
            try:
                await self._ws_reconnect_task
            except asyncio.CancelledError:
                pass

        await self.disconnect_websocket()
        self.ws_connected = False
        logger.info(f"{self.broker_name} WebSocket stopped")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.ws_connected:
            try:
                await asyncio.sleep(self.ws_heartbeat_interval)
                if self.ws_connected:
                    await self._send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await self._handle_ws_error(e)

    async def _handle_ws_error(self, error: Exception):
        """Handle WebSocket errors with reconnection"""
        logger.error(f"WebSocket error: {error}")
        self.ws_connected = False

        if self._ws_reconnect_task and not self._ws_reconnect_task.done():
            return  # Reconnection already in progress

        self._ws_reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """Exponential backoff reconnection"""
        while self.ws_reconnect_attempts < self.max_ws_reconnect_attempts:
            self.ws_reconnect_attempts += 1
            delay = min(2 ** self.ws_reconnect_attempts, 60)

            logger.info(f"Reconnecting in {delay}s (attempt {self.ws_reconnect_attempts})")
            await asyncio.sleep(delay)

            try:
                success = await self.connect_websocket()
                if success:
                    self.ws_reconnect_attempts = 0
                    self.ws_connected = True
                    self.metrics['ws_reconnects'] += 1
                    logger.info("WebSocket reconnected successfully")

                    # Re-subscribe
                    symbols = list(set(
                        pos.symbol for pos in self.positions.values()
                    ))
                    if symbols:
                        await self.subscribe_market_data(symbols)

                    if self._ws_heartbeat_task and self._ws_heartbeat_task.done():
                        self._ws_heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    return

            except Exception as e:
                logger.error(f"Reconnection failed: {e}")

        logger.error("Max reconnection attempts reached")
        if self.on_error:
            await self._safe_callback(self.on_error, ConnectionError("Max reconnection attempts reached"))

    @abstractmethod
    async def _send_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        pass

    # ============================================================
    # Helper methods
    # ============================================================

    def _validate_order(self, order: Order):
        """Validate order before sending"""
        if not order.symbol:
            raise ValueError("Symbol required")
        if order.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if order.order_type in (OrderType.LIMIT, OrderType.SL) and order.price <= 0:
            raise ValueError("Price required for limit orders")
        if order.order_type in (OrderType.SL, OrderType.SLM) and order.trigger_price <= 0:
            raise ValueError("Trigger price required for stop orders")

    def _update_avg_latency(self, latency: float):
        """Update running average latency"""
        n = self.metrics['orders_sent']
        if n == 1:
            self.metrics['avg_latency_ms'] = latency
        else:
            self.metrics['avg_latency_ms'] = (
                (self.metrics['avg_latency_ms'] * (n - 1) + latency) / n
            )

    async def _safe_callback(self, callback: Callable, *args, **kwargs):
        """Safely execute callback with error handling"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def get_metrics(self) -> Dict:
        """Get broker metrics"""
        return {
            'broker': self.broker_name,
            'connected': self.connected,
            'ws_connected': self.ws_connected,
            'authenticated': self.authenticated,
            'orders_count': len(self.orders),
            'active_orders': sum(1 for o in self.orders.values() if o.is_active),
            'positions_count': len(self.positions),
            **self.metrics
        }

    async def health_check(self) -> Dict:
        """Health check for monitoring"""
        return {
            'broker': self.broker_name,
            'status': 'healthy' if self.connected else 'unhealthy',
            'ws_status': 'connected' if self.ws_connected else 'disconnected',
            'circuit_breaker': self.circuit_breaker.state,
            'metrics': self.get_metrics()
        }

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info(f"Shutting down {self.broker_name} broker")
        await self.stop_websocket()

        # Cancel all active orders if configured
        if self.config.get('cancel_on_shutdown', False):
            for order in self.orders.values():
                if order.is_active:
                    try:
                        await self.cancel_order_safe(order.id)
                    except Exception as e:
                        logger.error(f"Failed to cancel order {order.id}: {e}")

        self.connected = False
        logger.info(f"{self.broker_name} broker shutdown complete")


# Factory for creating broker instances
class BrokerFactory:
    """Factory for creating broker instances"""

    _brokers = {}

    @classmethod
    def register(cls, name: str, broker_class):
        cls._brokers[name.lower()] = broker_class

    @classmethod
    def create(cls, name: str, **kwargs) -> ProductionBrokerBase:
        name = name.lower()
        if name not in cls._brokers:
            raise ValueError(f"Unknown broker: {name}. Available: {list(cls._brokers.keys())}")
        return cls._brokers[name](**kwargs)

    @classmethod
    def get_available(cls) -> List[str]:
        return list(cls._brokers.keys())


# Export all
__all__ = [
    'OrderStatus', 'OrderSide', 'OrderType', 'OrderValidity',
    'Order', 'Position', 'AccountInfo',
    'CircuitBreaker', 'RateLimiter', 'RetryPolicy',
    'BrokerError', 'AuthenticationError', 'RateLimitError',
    'OrderRejectedError', 'ConnectionError', 'CircuitBreakerOpenError',
    'ProductionBrokerBase', 'BrokerFactory'
]