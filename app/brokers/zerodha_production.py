"""
Zerodha Kite Connect Production Implementation
===============================================
Production-ready Zerodha broker with:
- Kite Connect REST API v3
- Kite Ticker WebSocket for real-time data
- Proper signature generation
- Instrument token mapping
- Order state machine compliance
- Rate limiting (10 req/sec, 200 req/min)
"""

import asyncio
import json
import logging
import time
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import aiohttp
import websockets
from kiteconnect import KiteConnect, KiteTicker

from .production_base import (
    ProductionBrokerBase, Order, Position, AccountInfo,
    OrderStatus, OrderSide, OrderType, OrderValidity,
    CircuitBreaker, RateLimiter, RetryPolicy,
    AuthenticationError, RateLimitError, OrderRejectedError,
    ConnectionError, BrokerFactory
)

logger = logging.getLogger(__name__)


# Zerodha constants
KITE_API_URL = "https://api.kite.trade"
KITE_WS_URL = "wss://ws.kite.trade"

# Rate limits: 10 req/sec, 200 req/min
ZERODHA_RATE_LIMIT = 10
ZERODHA_RATE_BURST = 20
ZERODHA_MINUTE_LIMIT = 200

# Order status mapping
KITE_TO_INTERNAL_STATUS = {
    'OPEN': OrderStatus.ACKED,
    'COMPLETE': OrderStatus.FILLED,
    'REJECTED': OrderStatus.REJECTED,
    'CANCELLED': OrderStatus.CANCELLED,
    'TRIGGER PENDING': OrderStatus.SENT,
    'OPEN PENDING': OrderStatus.SENT,
    'MODIFIED': OrderStatus.ACKED,
}

KITE_TO_SIDE = {
    'BUY': 'buy',
    'SELL': 'sell',
}

INTERNAL_TO_KITE_SIDE = {v: k for k, v in KITE_TO_SIDE.items()}

INTERNAL_TO_KITE_TYPE = {
    'market': 'MARKET',
    'limit': 'LIMIT',
    'sl': 'SL',
    'slm': 'SL-M',
}

INTERNAL_TO_KITE_VALIDITY = {
    'day': 'DAY',
    'ioc': 'IOC',
    'gtd': 'GTT',
}


class ZerodhaProductionBroker(ProductionBrokerBase):
    """
    Production-ready Zerodha Kite Connect broker
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str = None,
        config: Dict = None
    ):
        super().__init__('zerodha', api_key, api_secret, config)

        self.access_token = access_token
        self.kite = KiteConnect(api_key=api_key)
        self.kite_ticker = None

        # Session management
        self.session_expiry: Optional[datetime] = None
        self._session_refresh_task = None

        # Instrument cache
        self.instruments: Dict[str, Dict] = {}
        self.instrument_cache_time: Optional[datetime] = None

        # Rate limiting (separate for minute)
        self.minute_rate_limiter = RateLimiter(
            rate=ZERODHA_MINUTE_LIMIT,
            per=60,
            burst=ZERODHA_MINUTE_LIMIT
        )

        # Order tracking for WebSocket updates
        self._ws_order_map: Dict[str, str] = {}  # kite_order_id -> internal_id

        logger.info("Zerodha production broker initialized")

    # ============================================================
    # Authentication
    # ============================================================

    async def authenticate(self) -> bool:
        """Authenticate with Zerodha using access token"""
        try:
            if self.access_token:
                self.kite.set_access_token(self.access_token)
                # Validate token
                profile = await self._api_call(self.kite.profile)
                self.authenticated = True
                self.connected = True
                logger.info(f"Zerodha authenticated: {profile['user_name']} ({profile['user_id']})")
                return True

            # If no access token, need to generate via login flow
            logger.warning("No access token provided. Use generate_session() with request_token")
            return False

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            if "TokenException" in str(type(e)) or "403" in str(e):
                raise AuthenticationError(f"Zerodha auth failed: {e}")
            raise

    async def generate_session(self, request_token: str) -> str:
        """Generate access token from request token (login flow)"""
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data['access_token']
            self.kite.set_access_token(self.access_token)

            # Get profile
            profile = await self._api_call(self.kite.profile)
            self.authenticated = True
            self.connected = True

            # Save token for reuse
            logger.info(f"Session generated for {profile['user_name']}")
            return self.access_token

        except Exception as e:
            logger.error(f"Session generation failed: {e}")
            raise AuthenticationError(f"Failed to generate session: {e}")

    async def _ensure_authenticated(self):
        """Ensure valid authentication"""
        if not self.authenticated or not self.access_token:
            raise AuthenticationError("Not authenticated")

        # Check token expiry (Zerodha tokens expire at 7:30 AM next day)
        now = datetime.utcnow()
        if self.session_expiry and now >= self.session_expiry:
            logger.warning("Session expired, need re-authentication")
            raise AuthenticationError("Session expired")

    # ============================================================
    # API Call Wrapper with Rate Limiting & Retry
    # ============================================================

    async def _api_call(self, func, *args, **kwargs):
        """Execute API call with rate limiting, circuit breaker, retry"""
        await self.rate_limiter.acquire()
        await self.minute_rate_limiter.acquire()

        async def _call():
            return await self.circuit_breaker.acall(
                lambda: asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs)
            )

        return await self.retry_policy.execute(_call)

    # ============================================================
    # Order Management
    # ============================================================

    async def place_order(self, order: Order) -> Order:
        """Place order with Zerodha"""
        await self._ensure_authenticated()

        # Build order params
        params = self._build_order_params(order)

        try:
            response = await self._api_call(
                self.kite.place_order,
                variety=params['variety'],
                exchange=params['exchange'],
                tradingsymbol=params['tradingsymbol'],
                transaction_type=params['transaction_type'],
                quantity=params['quantity'],
                product=params['product'],
                order_type=params['order_type'],
                price=params.get('price'),
                trigger_price=params.get('trigger_price'),
                validity=params.get('validity'),
                disclosed_quantity=params.get('disclosed_quantity'),
                tag=params.get('tag')
            )

            kite_order_id = response.get('order_id')
            if not kite_order_id:
                raise OrderRejectedError("No order ID returned")

            # Update order
            order.broker_order_id = kite_order_id
            order.status = OrderStatus.SENT
            order.sent_at = datetime.utcnow()

            # Map for WebSocket updates
            self._ws_order_map[kite_order_id] = order.id

            logger.info(f"Order placed: {order.id} -> {kite_order_id}")

            # Poll for initial status
            await asyncio.sleep(0.5)
            return await self.get_order_status(order.id)

        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.reject_reason = str(e)
            order.reject_code = getattr(e, 'code', 'UNKNOWN')
            logger.error(f"Order placement failed: {e}")
            raise OrderRejectedError(str(e))

    def _build_order_params(self, order: Order) -> Dict:
        """Build Zerodha order parameters"""
        # Determine product type
        product = 'CNC'  # Default for equity delivery
        if order.tags.get('product'):
            product = order.tags['product']
        elif order.order_type in (OrderType.SL, OrderType.SLM):
            product = 'MIS'  # Intraday for stop orders

        # Variety
        variety = 'regular'
        if order.tags.get('variety'):
            variety = order.tags['variety']

        return {
            'variety': variety,
            'exchange': order.exchange,
            'tradingsymbol': order.symbol,
            'transaction_type': INTERNAL_TO_KITE_SIDE[order.side.value],
            'quantity': order.quantity,
            'product': product,
            'order_type': INTERNAL_TO_KITE_TYPE[order.order_type.value],
            'price': order.price if order.order_type != OrderType.MARKET else 0,
            'trigger_price': order.trigger_price if order.order_type in (OrderType.SL, OrderType.SLM) else 0,
            'validity': INTERNAL_TO_KITE_VALIDITY.get(order.validity.value, 'DAY'),
            'disclosed_quantity': order.disclosed_quantity or 0,
            'tag': order.correlation_id or order.id[:16]
        }

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        await self._ensure_authenticated()

        order = self.orders.get(order_id)
        if not order or not order.broker_order_id:
            raise ValueError("Order not found or no broker ID")

        try:
            await self._api_call(
                self.kite.cancel_order,
                variety='regular',
                order_id=order.broker_order_id
            )

            order.status = OrderStatus.CANCELLED
            order.completed_at = datetime.utcnow()

            # Remove from WS map
            self._ws_order_map.pop(order.broker_order_id, None)

            logger.info(f"Order cancelled: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            raise

    async def modify_order(self, order_id: str, **kwargs) -> Order:
        """Modify order"""
        await self._ensure_authenticated()

        order = self.orders.get(order_id)
        if not order or not order.broker_order_id:
            raise ValueError("Order not found")

        # Build modify params
        params = {'order_id': order.broker_order_id}
        if 'quantity' in kwargs:
            params['quantity'] = kwargs['quantity']
        if 'price' in kwargs:
            params['price'] = kwargs['price']
        if 'trigger_price' in kwargs:
            params['trigger_price'] = kwargs['trigger_price']
        if 'order_type' in kwargs:
            params['order_type'] = INTERNAL_TO_KITE_TYPE[kwargs['order_type'].value]

        try:
            await self._api_call(self.kite.modify_order, **params)
            logger.info(f"Order modified: {order_id}")

            # Refresh status
            return await self.get_order_status(order_id)

        except Exception as e:
            logger.error(f"Modify failed: {e}")
            raise

    async def get_order_status(self, order_id: str) -> Order:
        """Get order status from Zerodha"""
        await self._ensure_authenticated()

        order = self.orders.get(order_id)
        if not order or not order.broker_order_id:
            raise ValueError("Order not found")

        try:
            history = await self._api_call(self.kite.order_history, order.broker_order_id)
            if not history:
                return order

            # Get latest status
            latest = history[-1]
            self._update_order_from_kite(order, latest)

            return order

        except Exception as e:
            logger.error(f"Get order status failed: {e}")
            raise

    def _update_order_from_kite(self, order: Order, kite_data: Dict):
        """Update internal order from Kite data"""
        status = kite_data.get('status', '')
        order.status = KITE_TO_INTERNAL_STATUS.get(status, OrderStatus.ACKED)
        order.broker_order_id = kite_data.get('order_id')
        order.exchange_order_id = kite_data.get('exchange_order_id')

        # Fill data
        filled_qty = kite_data.get('filled_quantity', 0)
        pending_qty = kite_data.get('pending_quantity', 0)
        order.filled_quantity = filled_qty
        order.pending_quantity = pending_qty

        if filled_qty > 0:
            order.average_price = kite_data.get('average_price', 0)
            order.last_fill_price = kite_data.get('last_price', 0)
            order.last_fill_quantity = kite_data.get('filled_quantity', 0) - getattr(order, '_prev_filled', 0)
            order._prev_filled = filled_qty
            order.last_fill_time = datetime.utcnow()
            if not order.first_fill_at:
                order.first_fill_at = datetime.utcnow()

        if order.status == OrderStatus.FILLED:
            order.completed_at = datetime.utcnow()
            self.metrics['orders_filled'] += 1
        elif order.status == OrderStatus.REJECTED:
            order.reject_reason = kite_data.get('status_message')
            order.reject_code = kite_data.get('status_code')
            self.metrics['orders_rejected'] += 1

    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        await self._ensure_authenticated()

        try:
            data = await self._api_call(self.kite.positions)
            net_positions = data.get('net', [])

            positions = []
            for p in net_positions:
                if p['quantity'] != 0:
                    pos = Position(
                        symbol=p['tradingsymbol'],
                        exchange=p['exchange'],
                        net_quantity=p['quantity'],
                        buy_quantity=p['buy_quantity'],
                        sell_quantity=p['sell_quantity'],
                        buy_value=p['buy_value'],
                        sell_value=p['sell_value'],
                        average_buy_price=p['buy_price'] if p['buy_quantity'] > 0 else 0,
                        average_sell_price=p['sell_price'] if p['sell_quantity'] > 0 else 0,
                        unrealized_pnl=p['unrealised'],
                        realized_pnl=p['realised'],
                        last_price=p['last_price']
                    )
                    positions.append(pos)
                    self.positions[pos.symbol] = pos

            return positions

        except Exception as e:
            logger.error(f"Get positions failed: {e}")
            raise

    async def get_account(self) -> AccountInfo:
        """Get account/margin info"""
        await self._ensure_authenticated()

        try:
            margins = await self._api_call(self.kite.margins, 'equity')

            self.account = AccountInfo(
                account_id=self.kite.user_id,
                broker='zerodha',
                equity=margins.get('net', 0),
                margin_used=margins.get('utilised', {}).get('debits', 0),
                margin_available=margins.get('available', {}).get('cash', 0),
                span_margin=margins.get('utilised', {}).get('span', 0),
                exposure_margin=margins.get('utilised', {}).get('exposure', 0),
                realized_pnl=0,  # Not directly available
                unrealized_pnl=0
            )

            if self.on_account_update:
                await self._safe_callback(self.on_account_update, self.account)

            return self.account

        except Exception as e:
            logger.error(f"Get account failed: {e}")
            raise

    # ============================================================
    # WebSocket (Kite Ticker)
    # ============================================================

    async def connect_websocket(self) -> bool:
        """Connect to Kite Ticker WebSocket"""
        await self._ensure_authenticated()

        try:
            self.kite_ticker = KiteTicker(self.api_key, self.access_token)

            # Set callbacks
            self.kite_ticker.on_connect = self._on_ws_connect
            self.kite_ticker.on_close = self._on_ws_close
            self.kite_ticker.on_error = self._on_ws_error
            self.kite_ticker.on_ticks = self._on_ws_ticks
            self.kite_ticker.on_order_update = self._on_ws_order_update

            # Connect in background thread
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.kite_ticker.connect, True)

            # Wait for connection
            for _ in range(50):  # 5 second timeout
                if self.ws_connected:
                    break
                await asyncio.sleep(0.1)

            return self.ws_connected

        except Exception as e:
            logger.error(f"WebSocket connect failed: {e}")
            return False

    def _on_ws_connect(self, ws, response):
        """WebSocket connected"""
        self.ws_connected = True
        self.ws_reconnect_attempts = 0
        logger.info("Kite Ticker connected")

        # Resubscribe if needed
        if hasattr(self, '_pending_subscriptions'):
            self.kite_ticker.subscribe(self._pending_subscriptions)
            self.kite_ticker.set_mode(self.kite_ticker.MODE_FULL, self._pending_subscriptions)

    def _on_ws_close(self, ws, code, reason):
        """WebSocket closed"""
        self.ws_connected = False
        logger.warning(f"Kite Ticker closed: {code} - {reason}")

    def _on_ws_error(self, ws, code, reason):
        """WebSocket error"""
        logger.error(f"Kite Ticker error: {code} - {reason}")

    def _on_ws_ticks(self, ws, ticks):
        """Handle incoming ticks"""
        for tick in ticks:
            self._process_tick(tick)

    def _on_ws_order_update(self, ws, data):
        """Handle order updates from WebSocket"""
        order_id = data.get('order_id')
        internal_id = self._ws_order_map.get(order_id)

        if internal_id and internal_id in self.orders:
            order = self.orders[internal_id]
            self._update_order_from_kite(order, data)

            if self.on_order_update:
                asyncio.create_task(self._safe_callback(self.on_order_update, order))

    def _process_tick(self, tick: Dict):
        """Process incoming tick data"""
        symbol = tick.get('tradingsymbol') or self._get_symbol_from_token(tick.get('instrument_token'))
        if not symbol:
            return

        # Update position last price
        if symbol in self.positions:
            self.positions[symbol].last_price = tick.get('last_price', 0)
            self.positions[symbol].updated_at = datetime.utcnow()

        # Callback
        if self.on_tick:
            asyncio.create_task(self._safe_callback(self.on_tick, {
                'symbol': symbol,
                'ltp': tick.get('last_price', 0),
                'bid': tick.get('depth', {}).get('buy', [{}])[0].get('price', 0) if tick.get('depth') else 0,
                'ask': tick.get('depth', {}).get('sell', [{}])[0].get('price', 0) if tick.get('depth') else 0,
                'volume': tick.get('volume', 0),
                'timestamp': datetime.utcnow().isoformat()
            }))

    def _get_symbol_from_token(self, token: int) -> Optional[str]:
        """Get symbol from instrument token"""
        for sym, inst in self.instruments.items():
            if inst.get('instrument_token') == token:
                return sym
        return None

    async def subscribe_market_data(self, symbols: List[str]):
        """Subscribe to market data"""
        if not self.kite_ticker or not self.ws_connected:
            self._pending_subscriptions = symbols
            return

        tokens = []
        for sym in symbols:
            if sym in self.instruments:
                tokens.append(self.instruments[sym]['instrument_token'])

        if tokens:
            self.kite_ticker.subscribe(tokens)
            self.kite_ticker.set_mode(self.kite_ticker.MODE_FULL, tokens)
            logger.info(f"Subscribed to {len(tokens)} instruments")

    async def unsubscribe_market_data(self, symbols: List[str]):
        """Unsubscribe from market data"""
        if not self.kite_ticker or not self.ws_connected:
            return

        tokens = []
        for sym in symbols:
            if sym in self.instruments:
                tokens.append(self.instruments[sym]['instrument_token'])

        if tokens:
            self.kite_ticker.unsubscribe(tokens)
            logger.info(f"Unsubscribed from {len(tokens)} instruments")

    async def _send_heartbeat(self):
        """Kite Ticker handles heartbeat internally"""
        pass

    # ============================================================
    # Instrument Management
    # ============================================================

    async def load_instruments(self, exchange: str = 'NSE'):
        """Load instrument list for token mapping"""
        try:
            instruments = await self._api_call(self.kite.instruments, exchange)
            self.instruments = {
                inst['tradingsymbol']: inst
                for inst in instruments
                if inst['exchange'] == exchange
            }
            self.instrument_cache_time = datetime.utcnow()
            logger.info(f"Loaded {len(self.instruments)} instruments for {exchange}")
        except Exception as e:
            logger.error(f"Failed to load instruments: {e}")
            raise

    def get_instrument_token(self, symbol: str) -> Optional[int]:
        """Get instrument token for symbol"""
        inst = self.instruments.get(symbol)
        return inst.get('instrument_token') if inst else None

    # ============================================================
    # Historical Data
    # ============================================================

    async def get_historical_data(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = 'minute',
        continuous: bool = False
    ) -> List[Dict]:
        """Get historical OHLC data"""
        await self._ensure_authenticated()

        token = self.get_instrument_token(symbol)
        if not token:
            await self.load_instruments()
            token = self.get_instrument_token(symbol)

        if not token:
            raise ValueError(f"Instrument not found: {symbol}")

        interval_map = {
            'minute': 'minute',
            '3minute': '3minute',
            '5minute': '5minute',
            '10minute': '10minute',
            '15minute': '15minute',
            '30minute': '30minute',
            '60minute': '60minute',
            'day': 'day'
        }

        try:
            data = await self._api_call(
                self.kite.historical_data,
                token,
                from_date,
                to_date,
                interval_map.get(interval, 'minute'),
                continuous
            )
            return data
        except Exception as e:
            logger.error(f"Historical data failed: {e}")
            raise

    # ============================================================
    # Cleanup
    # ============================================================

    async def disconnect_websocket(self):
        """Disconnect Kite Ticker"""
        if self.kite_ticker:
            try:
                self.kite_ticker.close()
            except Exception as e:
                logger.error(f"WebSocket close error: {e}")
        self.ws_connected = False

    async def shutdown(self):
        """Graceful shutdown"""
        await super().shutdown()
        if self._session_refresh_task:
            self._session_refresh_task.cancel()


# Register with factory
BrokerFactory.register('zerodha', ZerodhaProductionBroker)

__all__ = ['ZerodhaProductionBroker']