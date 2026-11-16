"""
Real-Time P&L/Risk Streaming Engine
=====================================
Sub-second latency streaming for:
- P&L updates (realized + unrealized)
- Position changes
- Risk metrics (VaR, drawdown, exposure)
- Order status updates
- Account/margin updates
- Market data snapshots

Uses WebSocket with automatic reconnection, message batching,
and delta compression for minimal bandwidth.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set
from collections import defaultdict, deque
import weakref

logger = logging.getLogger(__name__)


class StreamMessageType(Enum):
    """Message types for streaming"""
    # Market data
    TICK = "tick"
    QUOTE = "quote"
    DEPTH = "depth"
    TRADE = "trade"

    # Account
    PNL_UPDATE = "pnl_update"
    POSITION_UPDATE = "position_update"
    ACCOUNT_UPDATE = "account_update"
    MARGIN_UPDATE = "margin_update"

    # Orders
    ORDER_UPDATE = "order_update"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"

    # Risk
    RISK_UPDATE = "risk_update"
    VAR_UPDATE = "var_update"
    DRAWDOWN_UPDATE = "drawdown_update"
    EXPOSURE_UPDATE = "exposure_update"
    LIMIT_BREACH = "limit_breach"
    CIRCUIT_BREAKER = "circuit_breaker"

    # System
    HEARTBEAT = "heartbeat"
    SUBSCRIPTION_ACK = "subscription_ack"
    SUBSCRIPTION_NACK = "subscription_nack"
    ERROR = "error"
    RECONNECT = "reconnect"


@dataclass
class StreamMessage:
    """Stream message envelope"""
    type: StreamMessageType
    payload: Dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence: int = 0
    correlation_id: Optional[str] = None
    compression: bool = False


@dataclass
class Subscription:
    """Client subscription"""
    client_id: str
    topics: Set[str]
    filters: Dict = field(default_factory=dict)
    last_sequence: int = 0
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)


class StreamPublisher:
    """
    High-performance message publisher with:
    - Topic-based routing
    - Message batching
    - Delta compression
    - Backpressure handling
    """

    def __init__(self, batch_size: int = 100, batch_timeout: float = 0.05):
        self.subscriptions: Dict[str, Subscription] = {}
        self.topic_subscribers: Dict[str, Set[str]] = defaultdict(set)

        self.batch_size = batch_size
        self.batch_timeout = batch_timeout

        # Outbound queues per client
        self.client_queues: Dict[str, asyncio.Queue] = {}

        # Message sequence
        self.sequence = 0

        # Batching
        self._pending_batches: Dict[str, List[StreamMessage]] = defaultdict(list)
        self._batch_timers: Dict[str, asyncio.Task] = {}

        # Metrics
        self.metrics = {
            'messages_published': 0,
            'messages_delivered': 0,
            'messages_dropped': 0,
            'active_subscriptions': 0,
            'avg_latency_ms': 0.0,
        }

        # Delta compression cache
        self._last_state: Dict[str, Dict] = {}

        self._running = False
        self._publisher_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start publisher"""
        self._running = True
        self._publisher_task = asyncio.create_task(self._publisher_loop())
        logger.info("Stream publisher started")

    async def stop(self):
        """Stop publisher"""
        self._running = False
        if self._publisher_task:
            self._publisher_task.cancel()
            try:
                await self._publisher_task
            except asyncio.CancelledError:
                pass

        # Flush pending
        for client_id, batch in self._pending_batches.items():
            if batch:
                await self._send_batch(client_id, batch)

        logger.info("Stream publisher stopped")

    def subscribe(self, client_id: str, topics: List[str], filters: Dict = None) -> Subscription:
        """Subscribe client to topics"""
        sub = Subscription(
            client_id=client_id,
            topics=set(topics),
            filters=filters or {}
        )
        self.subscriptions[client_id] = sub

        for topic in topics:
            self.topic_subscribers[topic].add(client_id)

        # Create client queue
        self.client_queues[client_id] = asyncio.Queue(maxsize=10000)

        self.metrics['active_subscriptions'] = len(self.subscriptions)
        logger.info(f"Client {client_id} subscribed to {topics}")

        return sub

    def unsubscribe(self, client_id: str):
        """Unsubscribe client"""
        sub = self.subscriptions.pop(client_id, None)
        if sub:
            for topic in sub.topics:
                self.topic_subscribers[topic].discard(client_id)

            # Clean up queue
            queue = self.client_queues.pop(client_id, None)
            if queue:
                # Drain queue
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

        self.metrics['active_subscriptions'] = len(self.subscriptions)
        logger.info(f"Client {client_id} unsubscribed")

    async def publish(self, topic: str, payload: Dict, correlation_id: str = None,
                     compress: bool = True, priority: bool = False):
        """Publish message to topic subscribers"""
        self.sequence += 1

        # Delta compression
        if compress and topic in self._last_state:
            delta = self._compute_delta(self._last_state[topic], payload)
            if delta is not None:
                payload = {'_delta': True, 'data': delta}

        # Store full state for next delta
        self._last_state[topic] = payload.copy()

        msg = StreamMessage(
            type=StreamMessageType(topic.upper()) if topic.upper() in StreamMessageType.__members__
                 else StreamMessageType.TICK,
            payload=payload,
            sequence=self.sequence,
            correlation_id=correlation_id,
            compression=compress
        )

        # Get subscribers
        subscribers = self.topic_subscribers.get(topic, set())

        for client_id in subscribers:
            if priority:
                # Immediate send for priority messages
                await self._send_message(client_id, msg)
            else:
                # Batch
                self._pending_batches[client_id].append(msg)

                # Schedule batch flush
                if client_id not in self._batch_timers:
                    self._batch_timers[client_id] = asyncio.create_task(
                        self._flush_batch_after_timeout(client_id)
                    )

        self.metrics['messages_published'] += 1

    def _compute_delta(self, old: Dict, new: Dict) -> Optional[Dict]:
        """Compute delta between two states"""
        if old == new:
            return None  # No change

        delta = {}
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)

            if old_val != new_val:
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    nested_delta = self._compute_delta(old_val, new_val)
                    if nested_delta is not None:
                        delta[key] = nested_delta
                else:
                    delta[key] = new_val

        return delta if delta else None

    async def _flush_batch_after_timeout(self, client_id: str):
        """Flush batch after timeout"""
        await asyncio.sleep(self.batch_timeout)
        await self._flush_batch(client_id)
        self._batch_timers.pop(client_id, None)

    async def _flush_batch(self, client_id: str):
        """Flush pending batch for client"""
        batch = self._pending_batches.pop(client_id, [])
        if not batch:
            return

        queue = self.client_queues.get(client_id)
        if not queue:
            return

        # Combine batch into single message if multiple
        if len(batch) == 1:
            await self._send_message(client_id, batch[0])
        else:
            # Multi-message batch
            batch_msg = StreamMessage(
                type=StreamMessageType.TICK,  # Generic batch type
                payload={'_batch': True, 'messages': [m.payload for m in batch]},
                sequence=batch[-1].sequence,
                compression=True
            )
            await self._send_message(client_id, batch_msg)

    async def _send_message(self, client_id: str, msg: StreamMessage):
        """Send message to client queue"""
        queue = self.client_queues.get(client_id)
        if not queue:
            return

        try:
            await asyncio.wait_for(queue.put(msg), timeout=0.1)
            self.metrics['messages_delivered'] += 1
        except asyncio.TimeoutError:
            self.metrics['messages_dropped'] += 1
            logger.warning(f"Queue full for client {client_id}, dropping message")

    async def _publisher_loop(self):
        """Background publisher loop"""
        while self._running:
            try:
                # Send heartbeats
                for client_id, sub in self.subscriptions.items():
                    if (datetime.utcnow() - sub.last_heartbeat).seconds > 30:
                        await self.publish(
                            'heartbeat',
                            {'timestamp': datetime.utcnow().isoformat()},
                            priority=True
                        )
                        sub.last_heartbeat = datetime.utcnow()

                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Publisher loop error: {e}")
                await asyncio.sleep(1)

    def get_client_queue(self, client_id: str) -> Optional[asyncio.Queue]:
        """Get client message queue"""
        return self.client_queues.get(client_id)

    def get_metrics(self) -> Dict:
        return {
            **self.metrics,
            'queue_sizes': {cid: q.qsize() for cid, q in self.client_queues.items()},
            'pending_batches': {cid: len(b) for cid, b in self._pending_batches.items()}
        }


# ============================================================
# Real-Time Data Aggregators
# ============================================================

class RealTimeAggregator:
    """
    Real-time data aggregation for streaming.
    Maintains live state for:
    - P&L (realized + unrealized)
    - Positions
    - Risk metrics
    - Account info
    """

    def __init__(self, publisher: StreamPublisher):
        self.publisher = publisher

        # State
        self.positions: Dict[str, Dict] = {}
        self.account: Dict = {}
        self.pnl: Dict = {
            'realized': 0.0,
            'unrealized': 0.0,
            'daily': 0.0,
            'by_symbol': {},
            'by_strategy': {}
        }
        self.risk_metrics: Dict = {}
        self.orders: Dict[str, Dict] = {}

        # Market data cache
        self.market_data: Dict[str, Dict] = {}

        # Update throttling
        self._update_timers: Dict[str, asyncio.Task] = {}
        self._throttle_ms = 100  # Max 10 updates/sec per topic

    async def on_tick(self, tick: Dict):
        """Process incoming tick"""
        symbol = tick.get('symbol')
        if not symbol:
            return

        # Update market data
        self.market_data[symbol] = {
            'ltp': tick.get('ltp', 0),
            'bid': tick.get('bid'),
            'ask': tick.get('ask'),
            'volume': tick.get('volume', 0),
            'timestamp': tick.get('timestamp', datetime.utcnow().isoformat())
        }

        # Update position unrealized P&L
        await self._update_position_pnl(symbol, tick.get('ltp', 0))

        # Throttled publish
        await self._throttled_publish('tick', tick)

    async def on_quote(self, quote: Dict):
        """Process quote update"""
        await self._throttled_publish('quote', quote)

    async def on_position_update(self, position: Dict):
        """Process position update"""
        symbol = position.get('symbol')
        if symbol:
            self.positions[symbol] = position
            await self._throttled_publish('position_update', position)

    async def on_order_update(self, order: Dict):
        """Process order update"""
        order_id = order.get('order_id')
        if order_id:
            self.orders[order_id] = order
            await self._throttled_publish('order_update', order)

    async def on_account_update(self, account: Dict):
        """Process account update"""
        self.account = account
        await self._throttled_publish('account_update', account)

    async def on_margin_update(self, margin: Dict):
        """Process margin update"""
        await self._throttled_publish('margin_update', margin)

    async def _update_position_pnl(self, symbol: str, ltp: float):
        """Update unrealized P&L for position"""
        pos = self.positions.get(symbol)
        if not pos or ltp <= 0:
            return

        qty = pos.get('net_quantity', 0)
        avg_price = pos.get('average_price', 0)

        if qty == 0 or avg_price == 0:
            return

        # Calculate unrealized
        if qty > 0:  # Long
            unrealized = (ltp - avg_price) * qty
        else:  # Short
            unrealized = (avg_price - ltp) * abs(qty)

        pos['unrealized_pnl'] = unrealized
        pos['last_price'] = ltp
        pos['updated_at'] = datetime.utcnow().isoformat()

        # Update aggregate P&L
        old_unrealized = self.pnl['by_symbol'].get(symbol, {}).get('unrealized', 0)
        self.pnl['unrealized'] += unrealized - old_unrealized
        self.pnl['by_symbol'][symbol] = {
            'unrealized': unrealized,
            'realized': pos.get('realized_pnl', 0),
            'quantity': qty
        }
        self.pnl['daily'] = self.pnl['realized'] + self.pnl['unrealized']

        # Publish P&L update
        await self._throttled_publish('pnl_update', {
            'total': self.pnl['daily'],
            'realized': self.pnl['realized'],
            'unrealized': self.pnl['unrealized'],
            'by_symbol': self.pnl['by_symbol']
        })

    async def _throttled_publish(self, topic: str, payload: Dict):
        """Publish with throttling"""
        if topic in self._update_timers:
            # Cancel existing timer
            self._update_timers[topic].cancel()

        async def delayed_publish():
            await asyncio.sleep(self._throttle_ms / 1000)
            await self.publisher.publish(topic, payload)
            self._update_timers.pop(topic, None)

        self._update_timers[topic] = asyncio.create_task(delayed_publish())

    def get_state(self) -> Dict:
        """Get current aggregate state"""
        return {
            'positions': self.positions,
            'account': self.account,
            'pnl': self.pnl,
            'risk_metrics': self.risk_metrics,
            'orders': self.orders,
            'market_data': self.market_data
        }


# ============================================================
# WebSocket Server
# ============================================================

class StreamingServer:
    """
    WebSocket server for real-time streaming.
    Handles:
    - Client connections
    - Authentication
    - Subscription management
    - Message routing
    - Heartbeats
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8001,
        auth_callback: Callable = None
    ):
        self.host = host
        self.port = port
        self.auth_callback = auth_callback

        self.publisher = StreamPublisher()
        self.aggregator = RealTimeAggregator(self.publisher)

        self.clients: Dict[str, Dict] = {}
        self.server = None

    async def start(self):
        """Start WebSocket server"""
        import websockets

        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            max_size=10**6,
            max_queue=1000
        )

        await self.publisher.start()
        logger.info(f"Streaming server started on {self.host}:{self.port}")

    async def stop(self):
        """Stop server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        await self.publisher.stop()
        logger.info("Streaming server stopped")

    async def _handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        client_id = str(uuid.uuid4())[:8]

        try:
            # Authenticate
            if self.auth_callback:
                auth_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                auth_data = json.loads(auth_msg)

                if not await self.auth_callback(auth_data):
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Authentication failed'
                    }))
                    return

            # Register client
            self.clients[client_id] = {
                'websocket': websocket,
                'connected_at': datetime.utcnow(),
                'subscriptions': set()
            }

            logger.info(f"Client connected: {client_id}")

            # Start message handling
            await self._handle_messages(client_id, websocket)

        except Exception as e:
            logger.error(f"Connection error for {client_id}: {e}")
        finally:
            await self._cleanup_client(client_id)

    async def _handle_messages(self, client_id: str, websocket):
        """Handle incoming messages from client"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_client_message(client_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {client_id}")
                except Exception as e:
                    logger.error(f"Message processing error for {client_id}: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _process_client_message(self, client_id: str, data: Dict):
        """Process client message"""
        msg_type = data.get('type')

        if msg_type == 'subscribe':
            topics = data.get('topics', [])
            filters = data.get('filters', {})

            self.publisher.subscribe(client_id, topics, filters)
            self.clients[client_id]['subscriptions'].update(topics)

            # Send ack
            await self._send_to_client(client_id, {
                'type': 'subscription_ack',
                'topics': topics,
                'sequence': self.publisher.sequence
            })

            # Send current state for subscribed topics
            await self._send_initial_state(client_id, topics)

        elif msg_type == 'unsubscribe':
            topics = data.get('topics', [])
            for topic in topics:
                self.publisher.topic_subscribers[topic].discard(client_id)
                self.clients[client_id]['subscriptions'].discard(topic)

        elif msg_type == 'heartbeat':
            if client_id in self.publisher.subscriptions:
                self.publisher.subscriptions[client_id].last_heartbeat = datetime.utcnow()

        elif msg_type == 'ping':
            await self._send_to_client(client_id, {'type': 'pong', 'timestamp': datetime.utcnow().isoformat()})

    async def _send_initial_state(self, client_id: str, topics: List[str]):
        """Send current state for subscribed topics"""
        state = self.aggregator.get_state()

        for topic in topics:
            if topic == 'positions':
                await self._send_to_client(client_id, {
                    'type': 'position_update',
                    'payload': state['positions'],
                    'initial': True
                })
            elif topic == 'pnl':
                await self._send_to_client(client_id, {
                    'type': 'pnl_update',
                    'payload': state['pnl'],
                    'initial': True
                })
            elif topic == 'account':
                await self._send_to_client(client_id, {
                    'type': 'account_update',
                    'payload': state['account'],
                    'initial': True
                })
            elif topic == 'risk':
                await self._send_to_client(client_id, {
                    'type': 'risk_update',
                    'payload': state['risk_metrics'],
                    'initial': True
                })
            elif topic == 'orders':
                await self._send_to_client(client_id, {
                    'type': 'order_update',
                    'payload': state['orders'],
                    'initial': True
                })
            elif topic == 'market':
                await self._send_to_client(client_id, {
                    'type': 'market_snapshot',
                    'payload': state['market_data'],
                    'initial': True
                })

    async def _send_to_client(self, client_id: str, message: Dict):
        """Send message to specific client"""
        client = self.clients.get(client_id)
        if not client:
            return

        try:
            await client['websocket'].send(json.dumps(message))
        except Exception as e:
            logger.error(f"Send error to {client_id}: {e}")

    async def _cleanup_client(self, client_id: str):
        """Clean up client on disconnect"""
        self.clients.pop(client_id, None)
        self.publisher.unsubscribe(client_id)
        logger.info(f"Client disconnected: {client_id}")

    # ============================================================
    # Public API for pushing data
    # ============================================================

    async def push_tick(self, tick: Dict):
        """Push tick to all subscribers"""
        await self.aggregator.on_tick(tick)

    async def push_position(self, position: Dict):
        """Push position update"""
        await self.aggregator.on_position_update(position)

    async def push_order(self, order: Dict):
        """Push order update"""
        await self.aggregator.on_order_update(order)

    async def push_account(self, account: Dict):
        """Push account update"""
        await self.aggregator.on_account_update(account)

    async def push_risk(self, risk: Dict):
        """Push risk metrics"""
        await self.publisher.publish('risk_update', risk)

    async def push_pnl(self, pnl: Dict):
        """Push P&L update"""
        await self.publisher.publish('pnl_update', pnl)

    def get_metrics(self) -> Dict:
        return {
            'clients': len(self.clients),
            'publisher': self.publisher.get_metrics(),
            'aggregator': {
                'positions': len(self.aggregator.positions),
                'orders': len(self.aggregator.orders),
                'market_symbols': len(self.aggregator.market_data)
            }
        }


# ============================================================
# Client Helper
# ============================================================

class StreamingClient:
    """
    High-level streaming client for strategies/services.
    """

    def __init__(
        self,
        url: str,
        token: str = None,
        auto_reconnect: bool = True
    ):
        self.url = url
        self.token = token
        self.auto_reconnect = auto_reconnect

        self.websocket = None
        self.connected = False
        self.subscriptions: Set[str] = set()

        # Callbacks
        self.on_tick: Optional[Callable] = None
        self.on_position: Optional[Callable] = None
        self.on_order: Optional[Callable] = None
        self.on_pnl: Optional[Callable] = None
        self.on_risk: Optional[Callable] = None
        self.on_account: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None

        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to streaming server"""
        import websockets

        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.websocket = await websockets.connect(
            self.url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=10
        )

        # Authenticate
        if self.token:
            await self.websocket.send(json.dumps({
                'type': 'auth',
                'token': self.token
            }))

        self.connected = True
        self._running = True

        # Start tasks
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        if self.on_connect:
            await self.on_connect()

    async def disconnect(self):
        """Disconnect from server"""
        self._running = False
        self.connected = False

        if self._receive_task:
            self._receive_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        if self.websocket:
            await self.websocket.close()

        if self.on_disconnect:
            await self.on_disconnect()

    async def subscribe(self, topics: List[str], filters: Dict = None):
        """Subscribe to topics"""
        if not self.connected:
            raise RuntimeError("Not connected")

        await self.websocket.send(json.dumps({
            'type': 'subscribe',
            'topics': topics,
            'filters': filters or {}
        }))

        self.subscriptions.update(topics)

    async def unsubscribe(self, topics: List[str]):
        """Unsubscribe from topics"""
        if not self.connected:
            return

        await self.websocket.send(json.dumps({
            'type': 'unsubscribe',
            'topics': topics
        }))

        self.subscriptions.difference_update(topics)

    async def _receive_loop(self):
        """Receive messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Receive error: {e}")
            if self.auto_reconnect:
                await self._reconnect()

    async def _handle_message(self, data: Dict):
        """Handle incoming message"""
        msg_type = data.get('type')

        if msg_type == 'tick' and self.on_tick:
            await self.on_tick(data.get('payload', data))
        elif msg_type == 'position_update' and self.on_position:
            await self.on_position(data.get('payload', data))
        elif msg_type == 'order_update' and self.on_order:
            await self.on_order(data.get('payload', data))
        elif msg_type == 'pnl_update' and self.on_pnl:
            await self.on_pnl(data.get('payload', data))
        elif msg_type == 'risk_update' and self.on_risk:
            await self.on_risk(data.get('payload', data))
        elif msg_type == 'account_update' and self.on_account:
            await self.on_account(data.get('payload', data))
        elif msg_type == 'error' and self.on_error:
            await self.on_error(data.get('message', data))

    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self._running:
            try:
                await asyncio.sleep(25)
                if self.connected:
                    await self.websocket.send(json.dumps({'type': 'heartbeat'}))
            except Exception:
                break

    async def _reconnect(self):
        """Attempt reconnection"""
        for attempt in range(10):
            try:
                await asyncio.sleep(2 ** attempt)
                await self.connect()
                # Re-subscribe
                if self.subscriptions:
                    await self.subscribe(list(self.subscriptions))
                return
            except Exception as e:
                logger.warning(f"Reconnect attempt {attempt + 1} failed: {e}")

        logger.error("Max reconnection attempts reached")


# ============================================================
# Factory
# ============================================================

async def create_streaming_server(
    host: str = "0.0.0.0",
    port: int = 8001,
    auth_callback: Callable = None
) -> StreamingServer:
    """Create and start streaming server"""
    server = StreamingServer(host, port, auth_callback)
    await server.start()
    return server


async def create_streaming_client(
    url: str,
    token: str = None,
    **callbacks
) -> StreamingClient:
    """Create and connect streaming client"""
    client = StreamingClient(url, token)
    for key, value in callbacks.items():
        setattr(client, key, value)
    await client.connect()
    return client


__all__ = [
    'StreamMessageType', 'StreamMessage', 'Subscription',
    'StreamPublisher', 'RealTimeAggregator', 'StreamingServer',
    'StreamingClient', 'create_streaming_server', 'create_streaming_client'
]