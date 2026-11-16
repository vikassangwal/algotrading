"""
Smart Order Router - Institutional Grade
=========================================
Routes orders to optimal broker/venue based on:
- Latency
- Fill rate
- Cost (commission + spread + impact)
- Available liquidity
- Failover support
- Regulatory compliance (best execution)
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict, deque
import numpy as np

logger = logging.getLogger(__name__)


class VenueType(Enum):
    BROKER = "broker"
    EXCHANGE = "exchange"
    DARK_POOL = "dark_pool"
    INTERNALIZER = "internalizer"


class RoutingStrategy(Enum):
    LATENCY = "latency"           # Fastest execution
    COST = "cost"                 # Lowest total cost
    FILL_RATE = "fill_rate"       # Highest probability of fill
    LIQUIDITY = "liquidity"       # Best available liquidity
    SMART = "smart"               # Multi-factor optimization
    VWAP = "vwap"                 # VWAP-targeted
    TWAP = "twap"                 # TWAP-targeted


@dataclass
class Venue:
    """Trading venue/broker"""
    name: str
    type: VenueType
    broker_id: str

    # Performance metrics (updated in real-time)
    avg_latency_ms: float = 10.0
    fill_rate: float = 0.95
    avg_slippage_bps: float = 5.0
    commission_bps: float = 2.0
    spread_bps: float = 2.0

    # Capacity
    max_order_size: int = 100000
    min_order_size: int = 1
    max_daily_volume: int = 10000000

    # Status
    enabled: bool = True
    healthy: bool = True
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)

    # Supported features
    supports_market: bool = True
    supports_limit: bool = True
    supports_stop: bool = True
    supports_iceberg: bool = False
    supports_twap: bool = False
    supports_vwap: bool = False

    # Metrics tracking
    orders_today: int = 0
    filled_today: int = 0
    rejected_today: int = 0
    total_latency_ms: float = 0.0

    def update_health(self, latency_ms: float, filled: bool, slippage_bps: float):
        """Update venue health metrics"""
        self.orders_today += 1
        self.total_latency_ms += latency_ms
        self.avg_latency_ms = self.total_latency_ms / self.orders_today

        if filled:
            self.filled_today += 1
        else:
            self.rejected_today += 1

        self.fill_rate = self.filled_today / max(1, self.orders_today)

        # Exponential moving average for slippage
        alpha = 0.1
        self.avg_slippage_bps = (1 - alpha) * self.avg_slippage_bps + alpha * slippage_bps

    def get_cost_estimate(self, quantity: int, price: float, side: str) -> float:
        """Estimate total cost in bps"""
        return self.commission_bps + self.spread_bps + self.avg_slippage_bps

    def get_score(self, strategy: RoutingStrategy, quantity: int, price: float) -> float:
        """Calculate venue score for routing strategy"""
        if not self.enabled or not self.healthy:
            return 0.0

        # Normalize metrics (0-1, higher is better)
        latency_score = max(0, 1 - self.avg_latency_ms / 100)  # 100ms = 0
        fill_score = self.fill_rate
        cost_score = max(0, 1 - (self.get_cost_estimate(1000, 100, 'buy') / 50))  # 50bps = 0

        weights = {
            RoutingStrategy.LATENCY: (0.6, 0.2, 0.2),
            RoutingStrategy.COST: (0.1, 0.2, 0.7),
            RoutingStrategy.FILL_RATE: (0.2, 0.7, 0.1),
            RoutingStrategy.LIQUIDITY: (0.1, 0.3, 0.6),
            RoutingStrategy.SMART: (0.3, 0.3, 0.4),
        }

        w_lat, w_fill, w_cost = weights.get(strategy, (0.3, 0.3, 0.4))

        return w_lat * latency_score + w_fill * fill_score + w_cost * cost_score


@dataclass
class RouteDecision:
    """Routing decision"""
    venue: Venue
    quantity: int
    strategy: RoutingStrategy
    confidence: float
    estimated_cost_bps: float
    estimated_latency_ms: float
    fallback_venues: List[Venue] = field(default_factory=list)
    reasoning: str = ""


class SmartOrderRouter:
    """
    Intelligent order routing with:
    - Multi-factor venue scoring
    - Real-time health monitoring
    - Automatic failover
    - Best execution compliance
    - Cost optimization
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.venues: Dict[str, Venue] = {}
        self.venue_clients: Dict[str, Any] = {}  # broker clients

        # Routing state
        self.active_orders: Dict[str, Dict] = {}
        self.order_history: deque = deque(maxlen=10000)

        # Routing strategy
        self.default_strategy = RoutingStrategy(
            self.config.get('default_strategy', 'smart')
        )

        # Failover
        self.failover_enabled = self.config.get('failover_enabled', True)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay_ms = self.config.get('retry_delay_ms', 500)

        # Cost tracking
        self.daily_costs: Dict[str, float] = defaultdict(float)
        self.daily_volume: Dict[str, int] = defaultdict(int)

        # Metrics
        self.metrics = {
            'orders_routed': 0,
            'orders_filled': 0,
            'orders_failed': 0,
            'fallback_used': 0,
            'avg_cost_bps': 0.0,
            'avg_latency_ms': 0.0,
        }

        # Health monitoring
        self._health_check_interval = 30  # seconds
        self._health_task: Optional[asyncio.Task] = None
        self._running = False

    def register_venue(self, venue: Venue, client: Any = None):
        """Register a trading venue"""
        self.venues[venue.name] = venue
        if client:
            self.venue_clients[venue.name] = client
        logger.info(f"Registered venue: {venue.name} ({venue.type.value})")

    def register_broker_client(self, venue_name: str, client: Any):
        """Register broker client for venue"""
        self.venue_clients[venue_name] = client

    async def start(self):
        """Start router"""
        self._running = True
        self._health_task = asyncio.create_task(self._health_monitor())
        logger.info("Smart Order Router started")

    async def stop(self):
        """Stop router"""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        logger.info("Smart Order Router stopped")

    async def route_order(
        self,
        order: Any,  # Order object
        strategy: RoutingStrategy = None,
        preferred_venues: List[str] = None,
        exclude_venues: List[str] = None
    ) -> RouteDecision:
        """
        Route order to optimal venue.
        """
        strategy = strategy or self.default_strategy

        # Filter available venues
        available = self._get_available_venues(
            order, preferred_venues, exclude_venues
        )

        if not available:
            raise ValueError("No available venues for order")

        # Score venues
        scored = []
        for venue in available:
            score = venue.get_score(strategy, order.quantity, order.price)
            if score > 0:
                scored.append((score, venue))

        if not scored:
            raise ValueError("No suitable venues after scoring")

        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Select primary and fallbacks
        primary_score, primary = scored[0]
        fallbacks = [v for _, v in scored[1:4]]  # Top 3 fallbacks

        # Create decision
        decision = RouteDecision(
            venue=primary,
            quantity=order.quantity,
            strategy=strategy,
            confidence=primary_score,
            estimated_cost_bps=primary.get_cost_estimate(order.quantity, order.price, order.side.value),
            estimated_latency_ms=primary.avg_latency_ms,
            fallback_venues=fallbacks,
            reasoning=self._generate_reasoning(primary, strategy, scored)
        )

        logger.info(f"Order routed to {primary.name} (strategy: {strategy.value}, "
                   f"confidence: {primary_score:.2f}, fallbacks: {len(fallbacks)})")

        return decision

    def _get_available_venues(
        self,
        order: Any,
        preferred: List[str] = None,
        excluded: List[str] = None
    ) -> List[Venue]:
        """Filter venues based on order requirements"""
        available = []

        for venue in self.venues.values():
            # Check exclusions
            if excluded and venue.name in excluded:
                continue

            # Check preferences
            if preferred and venue.name not in preferred:
                continue

            # Basic checks
            if not venue.enabled or not venue.healthy:
                continue

            # Order size limits
            if order.quantity < venue.min_order_size:
                continue
            if order.quantity > venue.max_order_size:
                continue

            # Order type support
            if order.order_type == 'MARKET' and not venue.supports_market:
                continue
            if order.order_type == 'LIMIT' and not venue.supports_limit:
                continue
            if order.order_type in ('SL', 'SLM') and not venue.supports_stop:
                continue

            # Daily volume check
            if self.daily_volume[venue.name] + order.quantity > venue.max_daily_volume:
                continue

            available.append(venue)

        return available

    def _generate_reasoning(self, venue: Venue, strategy: RoutingStrategy, scored: List) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        if strategy == RoutingStrategy.LATENCY:
            reasons.append(f"lowest latency ({venue.avg_latency_ms:.1f}ms)")
        elif strategy == RoutingStrategy.COST:
            reasons.append(f"lowest cost ({venue.get_cost_estimate(1000, 100, 'buy'):.1f}bps)")
        elif strategy == RoutingStrategy.FILL_RATE:
            reasons.append(f"highest fill rate ({venue.fill_rate*100:.1f}%)")
        elif strategy == RoutingStrategy.SMART:
            reasons.append(f"best overall score")

        reasons.append(f"fill rate: {venue.fill_rate*100:.1f}%")
        reasons.append(f"avg slippage: {venue.avg_slippage_bps:.1f}bps")

        return "; ".join(reasons)

    async def execute_with_failover(
        self,
        order: Any,
        decision: RouteDecision,
        place_order_fn: Callable
    ) -> Any:
        """
        Execute order with automatic failover.
        """
        venues_to_try = [decision.venue] + decision.fallback_venues
        last_error = None

        for i, venue in enumerate(venues_to_try):
            try:
                client = self.venue_clients.get(venue.name)
                if not client:
                    raise ValueError(f"No client for venue {venue.name}")

                # Update order with venue-specific params
                start = time.time()

                # Place order
                result = await place_order_fn(client, order)

                latency = (time.time() - start) * 1000

                # Update venue metrics
                filled = result.get('status') == 'filled'
                slippage = result.get('slippage_bps', 0)
                venue.update_health(latency, filled, slippage)

                # Update metrics
                self.metrics['orders_routed'] += 1
                if filled:
                    self.metrics['orders_filled'] += 1
                else:
                    self.metrics['orders_failed'] += 1

                # Track costs
                self.daily_costs[venue.name] += result.get('cost_bps', 0)
                self.daily_volume[venue.name] += order.quantity

                # Update averages
                self._update_averages(latency, result.get('cost_bps', 0))

                if i > 0:
                    self.metrics['fallback_used'] += 1
                    logger.warning(f"Order filled via fallback {i}: {venue.name}")

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Venue {venue.name} failed: {e}")

                # Update venue health
                venue.healthy = False
                await asyncio.sleep(self.retry_delay_ms / 1000)

                # Try to recover venue health
                await self._check_venue_recovery(venue)

                if i == len(venues_to_try) - 1:
                    # Last venue failed
                    self.metrics['orders_failed'] += 1
                    raise RuntimeError(f"All venues failed. Last error: {last_error}")

        raise RuntimeError(f"All venues exhausted: {last_error}")

    async def _check_venue_recovery(self, venue: Venue):
        """Check if venue has recovered"""
        try:
            # Try a simple health check
            client = self.venue_clients.get(venue.name)
            if client and hasattr(client, 'health_check'):
                await client.health_check()
                venue.healthy = True
                logger.info(f"Venue {venue.name} recovered")
        except Exception:
            pass  # Still unhealthy

    async def _health_monitor(self):
        """Background health monitoring"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)

                for venue in self.venues.values():
                    if not venue.enabled:
                        continue

                    # Check heartbeat
                    elapsed = (datetime.utcnow() - venue.last_heartbeat).total_seconds()
                    if elapsed > 60:  # 1 minute
                        venue.healthy = False
                        logger.warning(f"Venue {venue.name} heartbeat timeout")

                    # Check fill rate
                    if venue.orders_today > 10 and venue.fill_rate < 0.5:
                        venue.healthy = False
                        logger.warning(f"Venue {venue.name} low fill rate: {venue.fill_rate}")

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    def _update_averages(self, latency: float, cost_bps: float):
        n = self.metrics['orders_routed']
        if n == 1:
            self.metrics['avg_latency_ms'] = latency
            self.metrics['avg_cost_bps'] = cost_bps
        else:
            self.metrics['avg_latency_ms'] = (
                (self.metrics['avg_latency_ms'] * (n - 1) + latency) / n
            )
            self.metrics['avg_cost_bps'] = (
                (self.metrics['avg_cost_bps'] * (n - 1) + cost_bps) / n
            )

    def get_venue_stats(self) -> Dict:
        """Get venue performance statistics"""
        return {
            name: {
                'type': v.type.value,
                'enabled': v.enabled,
                'healthy': v.healthy,
                'fill_rate': v.fill_rate,
                'avg_latency_ms': v.avg_latency_ms,
                'avg_slippage_bps': v.avg_slippage_bps,
                'orders_today': v.orders_today,
                'daily_volume': self.daily_volume[v.name],
                'daily_cost_bps': self.daily_costs[v.name]
            }
            for name, v in self.venues.items()
        }

    def get_best_execution_report(self, order_id: str) -> Dict:
        """Generate best execution report for compliance"""
        # Would track full order lifecycle
        return {
            'order_id': order_id,
            'venue_analysis': self.get_venue_stats(),
            'routing_decision': 'Documented in order history',
            'cost_analysis': dict(self.daily_costs),
            'timestamp': datetime.utcnow().isoformat()
        }


# ============================================================
# Best Execution Compliance
# ============================================================

class BestExecutionMonitor:
    """
    Monitor and document best execution compliance.
    Required for regulatory reporting (MiFID II, SEC Rule 606).
    """

    def __init__(self, router: SmartOrderRouter):
        self.router = router
        self.execution_records: List[Dict] = []

    def record_execution(
        self,
        order: Any,
        decision: RouteDecision,
        result: Dict,
        market_state: Dict
    ):
        """Record execution for best execution analysis"""
        record = {
            'order_id': order.id,
            'timestamp': datetime.utcnow().isoformat(),
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': order.quantity,
            'order_type': order.order_type,
            'venue': decision.venue.name,
            'strategy': decision.strategy.value,
            'confidence': decision.confidence,
            'estimated_cost_bps': decision.estimated_cost_bps,
            'actual_cost_bps': result.get('cost_bps', 0),
            'latency_ms': result.get('latency_ms', 0),
            'fill_rate': decision.venue.fill_rate,
            'market_conditions': {
                'spread_bps': market_state.get('spread_bps', 0),
                'volatility': market_state.get('volatility', 0),
                'volume': market_state.get('volume', 0),
                'mid_price': market_state.get('mid_price', 0)
            },
            'alternatives': [
                {
                    'venue': v.name,
                    'score': v.get_score(decision.strategy, order.quantity, order.price),
                    'cost_bps': v.get_cost_estimate(order.quantity, order.price, order.side.value)
                }
                for v in decision.fallback_venues
            ]
        }

        self.execution_records.append(record)

    def generate_quarterly_report(self, quarter: str) -> Dict:
        """Generate quarterly best execution report (MiFID II RTS 28)"""
        # Filter records for quarter
        # Aggregate by venue, instrument class, client type
        return {
            'quarter': quarter,
            'total_orders': len(self.execution_records),
            'venues': self._aggregate_by_venue(),
            'instrument_classes': self._aggregate_by_instrument(),
            'execution_factors': self._analyze_execution_factors()
        }

    def _aggregate_by_venue(self) -> Dict:
        """Aggregate executions by venue"""
        venue_stats = defaultdict(lambda: {
            'orders': 0,
            'volume': 0,
            'avg_cost_bps': 0,
            'avg_latency': 0,
            'fill_rate': 0
        })

        for r in self.execution_records:
            v = r['venue']
            venue_stats[v]['orders'] += 1
            venue_stats[v]['volume'] += r.get('quantity', 0)

        return dict(venue_stats)

    def _aggregate_by_instrument(self) -> Dict:
        """Aggregate by instrument class"""
        # Would categorize by equity, derivative, etc.
        return {}

    def _analyze_execution_factors(self) -> Dict:
        """Analyze execution quality factors"""
        if not self.execution_records:
            return {}

        costs = [r['actual_cost_bps'] for r in self.execution_records if r.get('actual_cost_bps')]
        latencies = [r['latency_ms'] for r in self.execution_records if r.get('latency_ms')]

        return {
            'avg_cost_bps': np.mean(costs) if costs else 0,
            'median_cost_bps': np.median(costs) if costs else 0,
            'avg_latency_ms': np.mean(latencies) if latencies else 0,
            'cost_distribution': {
                'p25': np.percentile(costs, 25) if costs else 0,
                'p50': np.percentile(costs, 50) if costs else 0,
                'p75': np.percentile(costs, 75) if costs else 0,
                'p95': np.percentile(costs, 95) if costs else 0,
            }
        }


# ============================================================
# Factory
# ============================================================

def create_smart_router(config: Dict = None) -> SmartOrderRouter:
    """Create and configure smart order router"""
    return SmartOrderRouter(config)


def create_default_venues() -> List[Venue]:
    """Create default venue configurations for Indian market"""
    return [
        Venue(
            name="Zerodha",
            type=VenueType.BROKER,
            broker_id="zerodha",
            avg_latency_ms=15,
            fill_rate=0.98,
            avg_slippage_bps=3,
            commission_bps=3,
            spread_bps=2,
            max_order_size=100000,
            supports_market=True,
            supports_limit=True,
            supports_stop=True,
            supports_iceberg=True
        ),
        Venue(
            name="Dhan",
            type=VenueType.BROKER,
            broker_id="dhan",
            avg_latency_ms=10,
            fill_rate=0.97,
            avg_slippage_bps=4,
            commission_bps=2,
            spread_bps=2,
            max_order_size=50000,
            supports_market=True,
            supports_limit=True,
            supports_stop=True
        ),
        Venue(
            name="Upstox",
            type=VenueType.BROKER,
            broker_id="upstox",
            avg_latency_ms=20,
            fill_rate=0.96,
            avg_slippage_bps=5,
            commission_bps=3,
            spread_bps=3,
            max_order_size=100000,
            supports_market=True,
            supports_limit=True,
            supports_stop=True
        ),
    ]


__all__ = [
    'VenueType', 'RoutingStrategy', 'Venue', 'RouteDecision',
    'SmartOrderRouter', 'BestExecutionMonitor',
    'create_smart_router', 'create_default_venues'
]