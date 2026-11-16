"""
Execution Algorithms - Institutional Grade
==========================================
TWAP, VWAP, POV, and Implementation Shortfall executors
with real-time participation monitoring and adaptive logic.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class ExecutionConfig:
    """Configuration for execution algorithms"""
    # Common
    symbol: str
    side: OrderSide
    total_quantity: int
    max_participation_rate: float = 0.10  # Max % of volume
    min_order_size: int = 1
    max_order_size: int = 1000
    price_limit: Optional[float] = None  # Max price for buy, min for sell
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: str = "Asia/Kolkata"

    # TWAP specific
    twap_interval_seconds: int = 60  # Slice interval

    # VWAP specific
    vwap_schedule: Optional[List[float]] = None  # Volume profile % per interval

    # POV specific
    pov_target_rate: float = 0.05  # Target participation rate

    # IS specific
    is_risk_aversion: float = 1.0
    is_volatility: Optional[float] = None

    # Risk
    max_slippage_bps: float = 50
    cancel_on_limit_breach: bool = True


@dataclass
class ExecutionSlice:
    """Single execution slice"""
    slice_id: str
    quantity: int
    price_limit: Optional[float]
    timestamp: datetime
    status: str = "pending"
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    order_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ExecutionReport:
    """Execution performance report"""
    algorithm: str
    symbol: str
    side: str
    target_quantity: int
    filled_quantity: int
    avg_fill_price: float
    vwap_benchmark: float
    arrival_price: float
    slippage_bps: float
    implementation_shortfall_bps: float
    participation_rate: float
    duration_seconds: float
    slices_total: int
    slices_filled: int
    slices_failed: int
    start_time: datetime
    end_time: datetime
    slice_details: List[Dict] = field(default_factory=list)


class ExecutionAlgorithm(ABC):
    """Base class for execution algorithms"""

    def __init__(self, config: ExecutionConfig, order_callback: Callable):
        self.config = config
        self.order_callback = order_callback  # async function to place orders
        self.status = ExecutionStatus.PENDING
        self.slices: List[ExecutionSlice] = []
        self.filled_quantity = 0
        self.total_value = 0.0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._cancelled = False
        self._paused = False
        self._task: Optional[asyncio.Task] = None

    @abstractmethod
    async def execute(self) -> ExecutionReport:
        """Execute the algorithm"""
        pass

    async def pause(self):
        """Pause execution"""
        self._paused = True
        self.status = ExecutionStatus.PAUSED
        logger.info(f"{self.__class__.__name__} paused")

    async def resume(self):
        """Resume execution"""
        self._paused = False
        self.status = ExecutionStatus.RUNNING
        logger.info(f"{self.__class__.__name__} resumed")

    async def cancel(self):
        """Cancel execution"""
        self._cancelled = True
        self.status = ExecutionStatus.CANCELLED
        logger.info(f"{self.__class__.__name__} cancelled")

    def _create_slice(self, quantity: int, price_limit: Optional[float] = None) -> ExecutionSlice:
        """Create execution slice"""
        return ExecutionSlice(
            slice_id=str(uuid.uuid4())[:8],
            quantity=quantity,
            price_limit=price_limit or self.config.price_limit,
            timestamp=datetime.utcnow()
        )

    async def _place_slice_order(self, slice: ExecutionSlice) -> Dict:
        """Place order for slice via callback"""
        try:
            result = await self.order_callback({
                'symbol': self.config.symbol,
                'side': self.config.side.value,
                'quantity': slice.quantity,
                'price': slice.price_limit,
                'order_type': 'LIMIT' if slice.price_limit else 'MARKET',
                'metadata': {'slice_id': slice.slice_id, 'algo': self.__class__.__name__}
            })
            slice.status = "sent"
            slice.order_ids.append(result.get('order_id', ''))
            return result
        except Exception as e:
            slice.status = "error"
            logger.error(f"Slice order failed: {e}")
            raise

    async def _wait_for_fill(self, slice: ExecutionSlice, timeout: float = 30) -> bool:
        """Wait for slice to fill"""
        start = time.time()
        while time.time() - start < timeout:
            if slice.filled_quantity >= slice.quantity:
                slice.status = "filled"
                return True
            if slice.status in ("cancelled", "rejected", "error"):
                return False
            await asyncio.sleep(0.5)
        slice.status = "timeout"
        return False

    def _calculate_participation(self, slice_qty: int, interval_volume: int) -> float:
        """Calculate participation rate"""
        if interval_volume == 0:
            return 0.0
        return slice_qty / interval_volume

    def _check_slippage(self, fill_price: float, benchmark: float) -> bool:
        """Check if slippage within limits"""
        if self.config.side == OrderSide.BUY:
            slippage = (fill_price - benchmark) / benchmark * 10000
        else:
            slippage = (benchmark - fill_price) / benchmark * 10000
        return slippage <= self.config.max_slippage_bps

    def _generate_report(self) -> ExecutionReport:
        """Generate execution report"""
        vwap = self.total_value / self.filled_quantity if self.filled_quantity > 0 else 0
        arrival = self.slices[0].price_limit if self.slices else 0

        if self.config.side == OrderSide.BUY:
            slippage = (vwap - arrival) / arrival * 10000
        else:
            slippage = (arrival - vwap) / arrival * 10000

        return ExecutionReport(
            algorithm=self.__class__.__name__,
            symbol=self.config.symbol,
            side=self.config.side.value,
            target_quantity=self.config.total_quantity,
            filled_quantity=self.filled_quantity,
            avg_fill_price=vwap,
            vwap_benchmark=0,  # Would need market VWAP
            arrival_price=arrival,
            slippage_bps=slippage,
            implementation_shortfall_bps=slippage,  # Simplified
            participation_rate=0,  # Would need actual volume data
            duration_seconds=(self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0,
            slices_total=len(self.slices),
            slices_filled=sum(1 for s in self.slices if s.status == "filled"),
            slices_failed=sum(1 for s in self.slices if s.status in ("error", "timeout", "cancelled")),
            start_time=self.start_time,
            end_time=self.end_time,
            slice_details=[{
                'slice_id': s.slice_id,
                'quantity': s.quantity,
                'filled': s.filled_quantity,
                'avg_price': s.avg_fill_price,
                'status': s.status,
                'timestamp': s.timestamp.isoformat()
            } for s in self.slices]
        )


# ============================================================
# TWAP - Time Weighted Average Price
# ============================================================

class TWAPExecutor(ExecutionAlgorithm):
    """
    Time-Weighted Average Price execution.
    Slices order evenly across time intervals.
    """

    def __init__(self, config: ExecutionConfig, order_callback: Callable, volume_predictor: Callable = None):
        super().__init__(config, order_callback)
        self.volume_predictor = volume_predictor  # Optional: predict volume for sizing
        self.interval_seconds = config.twap_interval_seconds
        self.num_intervals = 0

    async def execute(self) -> ExecutionReport:
        """Execute TWAP strategy"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.utcnow()
        self._cancelled = False

        try:
            # Calculate intervals
            if self.config.end_time and self.config.start_time:
                total_seconds = (self.config.end_time - self.config.start_time).total_seconds()
            else:
                # Default: 1 hour
                total_seconds = 3600
                self.config.end_time = self.config.start_time + timedelta(seconds=total_seconds) if self.config.start_time else datetime.utcnow() + timedelta(seconds=total_seconds)

            self.num_intervals = max(1, int(total_seconds / self.interval_seconds))
            base_qty = self.config.total_quantity // self.num_intervals
            remainder = self.config.total_quantity % self.num_intervals

            logger.info(f"TWAP: {self.num_intervals} intervals, base_qty={base_qty}, remainder={remainder}")

            # Execute intervals
            for i in range(self.num_intervals):
                if self._cancelled:
                    break

                while self._paused:
                    await asyncio.sleep(1)

                # Calculate slice quantity
                slice_qty = base_qty + (1 if i < remainder else 0)
                if slice_qty < self.config.min_order_size:
                    continue

                # Create and execute slice
                slice = self._create_slice(slice_qty)
                self.slices.append(slice)

                await self._place_slice_order(slice)
                filled = await self._wait_for_fill(slice)

                if filled:
                    self.filled_quantity += slice.filled_quantity
                    self.total_value += slice.filled_quantity * slice.avg_fill_price
                else:
                    # Handle unfilled - could retry or continue
                    logger.warning(f"Slice {slice.slice_id} not fully filled")

                # Update progress
                progress = (i + 1) / self.num_intervals * 100
                logger.info(f"TWAP progress: {progress:.1f}% ({self.filled_quantity}/{self.config.total_quantity})")

                # Wait for next interval
                if i < self.num_intervals - 1 and not self._cancelled:
                    await asyncio.sleep(self.interval_seconds)

            self.end_time = datetime.utcnow()
            self.status = ExecutionStatus.COMPLETED if self.filled_quantity > 0 else ExecutionStatus.ERROR

            return self._generate_report()

        except Exception as e:
            self.status = ExecutionStatus.ERROR
            logger.error(f"TWAP execution error: {e}")
            raise


# ============================================================
# VWAP - Volume Weighted Average Price
# ============================================================

class VWAPExecutor(ExecutionAlgorithm):
    """
    Volume-Weighted Average Price execution.
    Slices order according to historical volume profile.
    """

    def __init__(self, config: ExecutionConfig, order_callback: Callable, volume_profile_provider: Callable = None):
        super().__init__(config, order_callback)
        self.volume_profile_provider = volume_profile_provider
        self.profile: List[float] = []

    async def execute(self) -> ExecutionReport:
        """Execute VWAP strategy"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.utcnow()
        self._cancelled = False

        try:
            # Get volume profile
            self.profile = await self._get_volume_profile()

            if not self.profile:
                logger.warning("No volume profile, falling back to TWAP")
                # Fallback to uniform
                self.profile = [1.0 / 12] * 12  # 12 intervals of 5 min

            # Normalize profile
            total = sum(self.profile)
            self.profile = [p / total for p in self.profile]

            logger.info(f"VWAP: {len(self.profile)} intervals with profile")

            # Execute per profile interval
            for i, weight in enumerate(self.profile):
                if self._cancelled:
                    break

                while self._paused:
                    await asyncio.sleep(1)

                # Calculate slice quantity
                slice_qty = int(self.config.total_quantity * weight)
                slice_qty = max(self.config.min_order_size, min(slice_qty, self.config.max_order_size))

                # Adjust for remaining
                remaining_qty = self.config.total_quantity - self.filled_quantity
                if i == len(self.profile) - 1:
                    slice_qty = remaining_qty

                if slice_qty <= 0:
                    continue

                # Create and execute slice
                slice = self._create_slice(slice_qty)
                self.slices.append(slice)

                await self._place_slice_order(slice)
                filled = await self._wait_for_fill(slice, timeout=60)

                if filled:
                    self.filled_quantity += slice.filled_quantity
                    self.total_value += slice.filled_quantity * slice.avg_fill_price

                logger.info(f"VWAP progress: {self.filled_quantity}/{self.config.total_quantity} (interval {i+1}/{len(self.profile)})")

                # Wait for next interval (5 min default)
                if i < len(self.profile) - 1 and not self._cancelled:
                    await asyncio.sleep(300)  # 5 minutes

            self.end_time = datetime.utcnow()
            self.status = ExecutionStatus.COMPLETED if self.filled_quantity > 0 else ExecutionStatus.ERROR

            return self._generate_report()

        except Exception as e:
            self.status = ExecutionStatus.ERROR
            logger.error(f"VWAP execution error: {e}")
            raise

    async def _get_volume_profile(self) -> List[float]:
        """Get volume profile for the day"""
        if self.volume_profile_provider:
            try:
                return await self.volume_profile_provider(self.config.symbol)
            except Exception as e:
                logger.warning(f"Volume profile provider failed: {e}")

        # Default: typical NSE volume profile (intraday)
        # Higher at open/close, lower at midday
        return [
            0.15,  # 9:15-9:30
            0.12,  # 9:30-9:45
            0.10,  # 9:45-10:00
            0.08,  # 10:00-10:15
            0.07,  # 10:15-10:30
            0.06,  # 10:30-10:45
            0.05,  # 10:45-11:00
            0.05,  # 11:00-11:15
            0.05,  # 11:15-11:30
            0.05,  # 11:30-11:45
            0.05,  # 11:45-12:00
            0.04,  # 12:00-12:15
            0.04,  # 12:15-12:30
            0.04,  # 12:30-12:45
            0.04,  # 12:45-13:00
            0.04,  # 13:00-13:15
            0.04,  # 13:15-13:30
            0.04,  # 13:30-13:45
            0.04,  # 13:45-14:00
            0.04,  # 14:00-14:15
            0.04,  # 14:15-14:30
            0.04,  # 14:30-14:45
            0.04,  # 14:45-15:00
            0.06,  # 15:00-15:15
            0.08,  # 15:15-15:30
        ]


# ============================================================
# POV - Percentage of Volume
# ============================================================

class POVExecutor(ExecutionAlgorithm):
    """
    Percentage of Volume execution.
    Dynamically adjusts order size based on real-time volume.
    """

    def __init__(
        self,
        config: ExecutionConfig,
        order_callback: Callable,
        market_data_provider: Callable = None
    ):
        super().__init__(config, order_callback)
        self.market_data_provider = market_data_provider
        self.target_rate = config.pov_target_rate
        self.check_interval = 30  # seconds
        self._volume_buffer = deque(maxlen=100)

    async def execute(self) -> ExecutionReport:
        """Execute POV strategy"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.utcnow()
        self._cancelled = False

        try:
            logger.info(f"POV: target rate={self.target_rate*100:.1f}%")

            while self.filled_quantity < self.config.total_quantity and not self._cancelled:
                while self._paused:
                    await asyncio.sleep(1)

                # Get current market volume
                interval_volume = await self._get_interval_volume()

                if interval_volume > 0:
                    # Calculate target quantity for this interval
                    target_qty = int(interval_volume * self.target_rate)
                    target_qty = max(self.config.min_order_size, min(target_qty, self.config.max_order_size))

                    # Adjust for remaining
                    remaining = self.config.total_quantity - self.filled_quantity
                    slice_qty = min(target_qty, remaining)

                    if slice_qty > 0:
                        slice = self._create_slice(slice_qty)
                        self.slices.append(slice)

                        await self._place_slice_order(slice)
                        filled = await self._wait_for_fill(slice, timeout=60)

                        if filled:
                            self.filled_quantity += slice.filled_quantity
                            self.total_value += slice.filled_quantity * slice.avg_fill_price

                            # Track participation
                            participation = slice.filled_quantity / interval_volume if interval_volume > 0 else 0
                            logger.info(f"POV: filled={slice.filled_quantity}, interval_vol={interval_volume}, "
                                      f"participation={participation*100:.2f}%, total={self.filled_quantity}/{self.config.total_quantity}")

                # Wait for next check interval
                if not self._cancelled:
                    await asyncio.sleep(self.check_interval)

            self.end_time = datetime.utcnow()
            self.status = ExecutionStatus.COMPLETED if self.filled_quantity > 0 else ExecutionStatus.ERROR

            return self._generate_report()

        except Exception as e:
            self.status = ExecutionStatus.ERROR
            logger.error(f"POV execution error: {e}")
            raise

    async def _get_interval_volume(self) -> int:
        """Get volume for current interval"""
        if self.market_data_provider:
            try:
                return await self.market_data_provider(self.config.symbol)
            except Exception as e:
                logger.warning(f"Market data provider failed: {e}")

        # Fallback: estimate from recent ticks
        if self._volume_buffer:
            return int(np.mean(self._volume_buffer))
        return 10000  # Default estimate

    def record_volume_tick(self, volume: int):
        """Record volume tick for estimation"""
        self._volume_buffer.append(volume)


# ============================================================
# Implementation Shortfall (IS) - Almgren-Chriss
# ============================================================

class ImplementationShortfallExecutor(ExecutionAlgorithm):
    """
    Implementation Shortfall (Almgren-Chriss) optimal execution.
    Minimizes: expected cost + risk_aversion * variance
    """

    def __init__(
        self,
        config: ExecutionConfig,
        order_callback: Callable,
        volatility: float = None,
        eta: float = 0.0001,  # Temporary impact
        sigma: float = 0.02   # Daily volatility
    ):
        super().__init__(config, order_callback)
        self.eta = eta  # Temporary market impact
        self.sigma = config.is_volatility or sigma  # Volatility
        self.risk_aversion = config.is_risk_aversion
        self.tau = 0  # Time horizon in fractions of day

    def _calculate_optimal_trajectory(self, n_intervals: int) -> List[float]:
        """
        Calculate optimal trading trajectory per Almgren-Chriss.
        x(t) = X * (sinh(k*(T-t)) / sinh(k*T))
        where k = sqrt(gamma/eta) and gamma = risk_aversion * sigma^2
        """
        gamma = self.risk_aversion * self.sigma ** 2
        k = np.sqrt(gamma / self.eta) if self.eta > 0 else 1.0
        T = 1.0  # 1 day horizon

        trajectory = []
        for i in range(n_intervals + 1):
            t = i / n_intervals
            if t == 1.0:
                x = 0
            else:
                x = np.sinh(k * (T - t)) / np.sinh(k * T)
            trajectory.append(x)

        # Convert to trade sizes (differences)
        trades = []
        for i in range(n_intervals):
            trade_frac = trajectory[i] - trajectory[i + 1]
            trades.append(max(0, trade_frac))

        # Normalize
        total = sum(trades)
        if total > 0:
            trades = [t / total for t in trades]

        return trades

    async def execute(self) -> ExecutionReport:
        """Execute Implementation Shortfall strategy"""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.utcnow()
        self._cancelled = False

        try:
            # Calculate optimal trajectory
            n_intervals = 20  # 20 intervals over the day
            trade_fractions = self._calculate_optimal_trajectory(n_intervals)

            logger.info(f"IS: {n_intervals} intervals, risk_aversion={self.risk_aversion}")

            for i, fraction in enumerate(trade_fractions):
                if self._cancelled:
                    break

                while self._paused:
                    await asyncio.sleep(1)

                slice_qty = int(self.config.total_quantity * fraction)
                slice_qty = max(self.config.min_order_size, min(slice_qty, self.config.max_order_size))

                remaining = self.config.total_quantity - self.filled_quantity
                if i == n_intervals - 1:
                    slice_qty = remaining

                if slice_qty <= 0:
                    continue

                slice = self._create_slice(slice_qty)
                self.slices.append(slice)

                await self._place_slice_order(slice)
                filled = await self._wait_for_fill(slice, timeout=60)

                if filled:
                    self.filled_quantity += slice.filled_quantity
                    self.total_value += slice.filled_quantity * slice.avg_fill_price

                logger.info(f"IS progress: {self.filled_quantity}/{self.config.total_quantity} "
                          f"(interval {i+1}/{n_intervals}, fraction={fraction:.3f})")

                # Wait for next interval
                if i < n_intervals - 1 and not self._cancelled:
                    await asyncio.sleep(1800)  # 30 minutes

            self.end_time = datetime.utcnow()
            self.status = ExecutionStatus.COMPLETED if self.filled_quantity > 0 else ExecutionStatus.ERROR

            return self._generate_report()

        except Exception as e:
            self.status = ExecutionStatus.ERROR
            logger.error(f"IS execution error: {e}")
            raise


# ============================================================
# Smart Execution Router
# ============================================================

class SmartExecutionRouter:
    """
    Routes orders to best execution algorithm based on:
    - Order size relative to ADV
    - Urgency
    - Market conditions
    - Cost optimization
    """

    def __init__(self, order_callback: Callable, market_data_provider: Callable = None):
        self.order_callback = order_callback
        self.market_data_provider = market_data_provider
        self.active_executions: Dict[str, ExecutionAlgorithm] = {}

    async def execute_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        urgency: str = "normal",  # low, normal, high
        price_limit: float = None,
        **kwargs
    ) -> ExecutionReport:
        """
        Route order to optimal algorithm.
        """

        # Get market data
        adv = 100000  # Default
        volatility = 0.02
        spread = 0.001

        if self.market_data_provider:
            try:
                data = await self.market_data_provider(symbol)
                adv = data.get('adv', adv)
                volatility = data.get('volatility', volatility)
                spread = data.get('spread', spread)
            except Exception as e:
                logger.warning(f"Market data failed: {e}")

        # Calculate participation rate
        participation = quantity / adv if adv > 0 else 0

        # Select algorithm
        algo = self._select_algorithm(
            quantity=quantity,
            participation=participation,
            urgency=urgency,
            volatility=volatility,
            spread=spread
        )

        logger.info(f"Selected {algo.__class__.__name__} for {symbol} {quantity} shares")

        # Execute
        config = ExecutionConfig(
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            price_limit=price_limit,
            **kwargs
        )

        execution = algo(config, self.order_callback, self.market_data_provider)
        execution_id = str(uuid.uuid4())[:8]
        self.active_executions[execution_id] = execution

        try:
            report = await execution.execute()
            del self.active_executions[execution_id]
            return report
        except Exception as e:
            del self.active_executions[execution_id]
            raise

    def _select_algorithm(
        self,
        quantity: int,
        participation: float,
        urgency: str,
        volatility: float,
        spread: float
    ) -> type:
        """
        Algorithm selection logic:
        - Small orders, low urgency -> TWAP
        - Large orders, known profile -> VWAP
        - Dynamic volume -> POV
        - Very large, risk-sensitive -> IS
        """

        # High urgency -> faster execution
        if urgency == "high":
            if participation < 0.01:
                return lambda c, cb, mdp: TWAPExecutor(c, cb, mdp, interval_seconds=30)
            return lambda c, cb, mdp: POVExecutor(c, cb, mdp, target_rate=0.20)

        # Low urgency, small -> TWAP
        if participation < 0.005 and quantity < 10000:
            return lambda c, cb, mdp: TWAPExecutor(c, cb, mdp, interval_seconds=120)

        # Medium participation -> VWAP if profile available
        if participation < 0.05:
            return lambda c, cb, mdp: VWAPExecutor(c, cb, mdp)

        # High participation -> POV
        if participation < 0.15:
            return lambda c, cb, mdp: POVExecutor(c, cb, mdp, target_rate=0.10)

        # Very large -> IS for risk management
        return lambda c, cb, mdp: ImplementationShortfallExecutor(
            c, cb, mdp,
            volatility=volatility,
            sigma=volatility
        )

    async def cancel_all(self):
        """Cancel all active executions"""
        for execution in self.active_executions.values():
            await execution.cancel()
        self.active_executions.clear()

    def get_active_count(self) -> int:
        return len(self.active_executions)


# ============================================================
# Factory
# ============================================================

class ExecutionAlgorithmFactory:
    """Factory for creating execution algorithms"""

    @staticmethod
    def create(algo_name: str, config: ExecutionConfig, order_callback: Callable, **kwargs) -> ExecutionAlgorithm:
        algorithms = {
            'twap': TWAPExecutor,
            'vwap': VWAPExecutor,
            'pov': POVExecutor,
            'is': ImplementationShortfallExecutor,
        }

        if algo_name not in algorithms:
            raise ValueError(f"Unknown algorithm: {algo_name}. Available: {list(algorithms.keys())}")

        return algorithms[algo_name](config, order_callback, **kwargs)

    @staticmethod
    def get_available() -> List[str]:
        return ['twap', 'vwap', 'pov', 'is']


__all__ = [
    'ExecutionStatus', 'OrderSide', 'ExecutionConfig', 'ExecutionSlice',
    'ExecutionReport', 'ExecutionAlgorithm',
    'TWAPExecutor', 'VWAPExecutor', 'POVExecutor', 'ImplementationShortfallExecutor',
    'SmartExecutionRouter', 'ExecutionAlgorithmFactory'
]