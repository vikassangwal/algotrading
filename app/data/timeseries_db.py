"""
TimescaleDB Integration for High-Frequency Tick Data
=====================================================
Production-ready tick data storage with:
- Automatic hypertable creation with compression
- Continuous aggregates for OHLCV, VWAP, volume
- Real-time data ingestion with batching
- Retention policies and data tiering
- Microsecond precision timestamps
- Partitioned by time + symbol for query performance
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from contextlib import asynccontextmanager

import asyncpg
import asyncpg.pool

logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """Single tick data point"""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    exchange: str = "NSE"
    trade_type: str = "regular"  # regular, auction, odd_lot
    metadata: Dict = None


@dataclass
class OHLCVBar:
    """OHLCV bar data"""
    symbol: str
    timestamp: datetime
    interval: str  # 1s, 1m, 5m, 15m, 1h, 1d
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float
    trade_count: int
    metadata: Dict = None


class TimescaleDBManager:
    """
    High-performance TimescaleDB manager for tick data.
    Optimized for:
    - High-throughput ingestion (100k+ ticks/sec)
    - Low-latency queries
    - Automatic compression
    - Continuous aggregates
    """

    def __init__(self, dsn: str, pool_size: int = 20):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        self.pool_size = pool_size
        self._write_batch: List[TickData] = []
        self._batch_size = 1000
        self._batch_timeout = 0.1  # seconds
        self._write_task: Optional[asyncio.Task] = None
        self._running = False

    async def initialize(self):
        """Initialize connection pool and schema"""
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=5,
            max_size=self.pool_size,
            command_timeout=60
        )

        await self._create_schema()
        await self._create_continuous_aggregates()
        await self._create_compression_policies()
        await self._create_retention_policies()

        self._running = True
        self._write_task = asyncio.create_task(self._batch_writer())

        logger.info("TimescaleDB initialized")

    async def _create_schema(self):
        """Create tables and indexes"""
        async with self.pool.acquire() as conn:
            # Enable TimescaleDB
            await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

            # Main ticks hypertable
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ticks (
                    time        TIMESTAMPTZ       NOT NULL,
                    symbol      TEXT              NOT NULL,
                    exchange    TEXT              NOT NULL DEFAULT 'NSE',
                    price       DOUBLE PRECISION  NOT NULL,
                    volume      BIGINT            NOT NULL,
                    bid         DOUBLE PRECISION,
                    ask         DOUBLE PRECISION,
                    bid_size    BIGINT,
                    ask_size    BIGINT,
                    trade_type  TEXT              NOT NULL DEFAULT 'regular',
                    metadata    JSONB
                );
            """)

            # Create hypertable
            await conn.execute("""
                SELECT create_hypertable(
                    'ticks', 'time',
                    chunk_time_interval => INTERVAL '1 day',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
            """)

            # Indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time
                ON ticks (symbol, time DESC);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticks_exchange_time
                ON ticks (exchange, time DESC);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticks_price
                ON ticks (price) WHERE price IS NOT NULL;
            """)

            # OHLCV continuous aggregates will be created separately
            # But we need base tables for custom intervals
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_1s (
                    time        TIMESTAMPTZ       NOT NULL,
                    symbol      TEXT              NOT NULL,
                    open        DOUBLE PRECISION  NOT NULL,
                    high        DOUBLE PRECISION  NOT NULL,
                    low         DOUBLE PRECISION  NOT NULL,
                    close       DOUBLE PRECISION  NOT NULL,
                    volume      BIGINT            NOT NULL,
                    vwap        DOUBLE PRECISION,
                    trade_count INTEGER           DEFAULT 0
                );
            """)
            await conn.execute("""
                SELECT create_hypertable(
                    'ohlcv_1s', 'time',
                    chunk_time_interval => INTERVAL '1 hour',
                    if_not_exists => TRUE
                );
            """)
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ohlcv_1s_symbol_time
                ON ohlcv_1s (symbol, time);
            """)

            # VWAP table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS vwap_data (
                    time        TIMESTAMPTZ       NOT NULL,
                    symbol      TEXT              NOT NULL,
                    vwap        DOUBLE PRECISION  NOT NULL,
                    volume      BIGINT            NOT NULL,
                    interval    TEXT              NOT NULL
                );
            """)
            await conn.execute("""
                SELECT create_hypertable(
                    'vwap_data', 'time',
                    chunk_time_interval => INTERVAL '1 day',
                    if_not_exists => TRUE
                );
            """)
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_vwap_symbol_time_interval
                ON vwap_data (symbol, time, interval);
            """)

            # Trade summary table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_summary (
                    time        TIMESTAMPTZ       NOT NULL,
                    symbol      TEXT              NOT NULL,
                    total_volume BIGINT           NOT NULL,
                    trade_count  INTEGER          NOT NULL,
                    buy_volume   BIGINT           DEFAULT 0,
                    sell_volume  BIGINT           DEFAULT 0,
                    vwap         DOUBLE PRECISION,
                    interval    TEXT              NOT NULL
                );
            """)
            await conn.execute("""
                SELECT create_hypertable(
                    'trade_summary', 'time',
                    chunk_time_interval => INTERVAL '1 day',
                    if_not_exists => TRUE
                );
            """)
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_summary_symbol_time_interval
                ON trade_summary (symbol, time, interval);
            """)

            logger.info("TimescaleDB schema created")

    async def _create_continuous_aggregates(self):
        """Create continuous aggregates for common queries"""
        async with self.pool.acquire() as conn:
            # 1-second OHLCV
            await conn.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1s_cagg
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('1 second', time) AS bucket,
                    symbol,
                    FIRST(price, time) AS open,
                    MAX(price) AS high,
                    MIN(price) AS low,
                    LAST(price, time) AS close,
                    SUM(volume) AS volume,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap,
                    COUNT(*) AS trade_count
                FROM ticks
                GROUP BY bucket, symbol
                WITH NO DATA;
            """)

            # 1-minute OHLCV
            await conn.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1m_cagg
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('1 minute', time) AS bucket,
                    symbol,
                    FIRST(price, time) AS open,
                    MAX(price) AS high,
                    MIN(price) AS low,
                    LAST(price, time) AS close,
                    SUM(volume) AS volume,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap,
                    COUNT(*) AS trade_count
                FROM ticks
                GROUP BY bucket, symbol
                WITH NO DATA;
            """)

            # 5-minute OHLCV
            await conn.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_5m_cagg
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('5 minute', time) AS bucket,
                    symbol,
                    FIRST(price, time) AS open,
                    MAX(price) AS high,
                    MIN(price) AS low,
                    LAST(price, time) AS close,
                    SUM(volume) AS volume,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap,
                    COUNT(*) AS trade_count
                FROM ticks
                GROUP BY bucket, symbol
                WITH NO DATA;
            """)

            # 15-minute OHLCV
            await conn.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_15m_cagg
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('15 minute', time) AS bucket,
                    symbol,
                    FIRST(price, time) AS open,
                    MAX(price) AS high,
                    MIN(price) AS low,
                    LAST(price, time) AS close,
                    SUM(volume) AS volume,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap,
                    COUNT(*) AS trade_count
                FROM ticks
                GROUP BY bucket, symbol
                WITH NO DATA;
            """)

            # 1-hour OHLCV
            await conn.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1h_cagg
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('1 hour', time) AS bucket,
                    symbol,
                    FIRST(price, time) AS open,
                    MAX(price) AS high,
                    MIN(price) AS low,
                    LAST(price, time) AS close,
                    SUM(volume) AS volume,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap,
                    COUNT(*) AS trade_count
                FROM ticks
                GROUP BY bucket, symbol
                WITH NO DATA;
            """)

            # 1-day OHLCV
            await conn.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1d_cagg
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('1 day', time) AS bucket,
                    symbol,
                    FIRST(price, time) AS open,
                    MAX(price) AS high,
                    MIN(price) AS low,
                    LAST(price, time) AS close,
                    SUM(volume) AS volume,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap,
                    COUNT(*) AS trade_count
                FROM ticks
                GROUP BY bucket, symbol
                WITH NO DATA;
            """)

            # Trade summary aggregate
            await conn.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS trade_summary_1m_cagg
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('1 minute', time) AS bucket,
                    symbol,
                    SUM(volume) AS total_volume,
                    COUNT(*) AS trade_count,
                    SUM(CASE WHEN price >= bid THEN volume ELSE 0 END) AS buy_volume,
                    SUM(CASE WHEN price <= ask THEN volume ELSE 0 END) AS sell_volume,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap
                FROM ticks
                GROUP BY bucket, symbol
                WITH NO DATA;
            """)

            # Add refresh policies
            await conn.execute("""
                SELECT add_continuous_aggregate_policy('ohlcv_1s_cagg',
                    start_offset => INTERVAL '3 seconds',
                    end_offset => INTERVAL '1 second',
                    schedule_interval => INTERVAL '1 second');
            """)
            await conn.execute("""
                SELECT add_continuous_aggregate_policy('ohlcv_1m_cagg',
                    start_offset => INTERVAL '2 minutes',
                    end_offset => INTERVAL '1 minute',
                    schedule_interval => INTERVAL '1 minute');
            """)
            await conn.execute("""
                SELECT add_continuous_aggregate_policy('ohlcv_5m_cagg',
                    start_offset => INTERVAL '10 minutes',
                    end_offset => INTERVAL '5 minute',
                    schedule_interval => INTERVAL '5 minute');
            """)
            await conn.execute("""
                SELECT add_continuous_aggregate_policy('ohlcv_15m_cagg',
                    start_offset => INTERVAL '30 minutes',
                    end_offset => INTERVAL '15 minute',
                    schedule_interval => INTERVAL '15 minute');
            """)
            await conn.execute("""
                SELECT add_continuous_aggregate_policy('ohlcv_1h_cagg',
                    start_offset => INTERVAL '2 hours',
                    end_offset => INTERVAL '1 hour',
                    schedule_interval => INTERVAL '1 hour');
            """)
            await conn.execute("""
                SELECT add_continuous_aggregate_policy('ohlcv_1d_cagg',
                    start_offset => INTERVAL '2 days',
                    end_offset => INTERVAL '1 day',
                    schedule_interval => INTERVAL '1 day');
            """)

            # Indexes on continuous aggregates
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_1s_cagg_symbol_time
                ON ohlcv_1s_cagg (symbol, bucket DESC);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_1m_cagg_symbol_time
                ON ohlcv_1m_cagg (symbol, bucket DESC);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_5m_cagg_symbol_time
                ON ohlcv_5m_cagg (symbol, bucket DESC);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_15m_cagg_symbol_time
                ON ohlcv_15m_cagg (symbol, bucket DESC);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_1h_cagg_symbol_time
                ON ohlcv_1h_cagg (symbol, bucket DESC);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_1d_cagg_symbol_time
                ON ohlcv_1d_cagg (symbol, bucket DESC);
            """)

            logger.info("Continuous aggregates created")

    async def _create_compression_policies(self):
        """Create compression policies for older data"""
        async with self.pool.acquire() as conn:
            # Enable compression on main ticks table
            await conn.execute("""
                ALTER TABLE ticks SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'symbol, exchange'
                );
            """)

            # Compress chunks older than 7 days
            await conn.execute("""
                SELECT add_compression_policy('ticks', INTERVAL '7 days');
            """)

            # Compression for OHLCV tables
            for table in ['ohlcv_1s', 'ohlcv_1m_cagg', 'ohlcv_5m_cagg', 'ohlcv_15m_cagg', 'ohlcv_1h_cagg', 'ohlcv_1d_cagg']:
                try:
                    await conn.execute(f"""
                        ALTER TABLE {table} SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'symbol'
                        );
                    """)
                    await conn.execute(f"""
                        SELECT add_compression_policy('{table}', INTERVAL '30 days');
                    """)
                except Exception as e:
                    logger.debug(f"Compression for {table}: {e}")

            logger.info("Compression policies created")

    async def _create_retention_policies(self):
        """Create data retention policies"""
        async with self.pool.acquire() as conn:
            # Raw ticks: keep 30 days
            await conn.execute("""
                SELECT add_retention_policy('ticks', INTERVAL '30 days');
            """)

            # 1-second aggregates: keep 7 days
            await conn.execute("""
                SELECT add_retention_policy('ohlcv_1s_cagg', INTERVAL '7 days');
            """)
            await conn.execute("""
                SELECT add_retention_policy('ohlcv_1s', INTERVAL '7 days');
            """)

            # 1-minute aggregates: keep 90 days
            await conn.execute("""
                SELECT add_retention_policy('ohlcv_1m_cagg', INTERVAL '90 days');
            """)

            # 5-minute aggregates: keep 1 year
            await conn.execute("""
                SELECT add_retention_policy('ohlcv_5m_cagg', INTERVAL '1 year');
            """)

            # 15-minute aggregates: keep 2 years
            await conn.execute("""
                SELECT add_retention_policy('ohlcv_15m_cagg', INTERVAL '2 years');
            """)

            # 1-hour aggregates: keep 5 years
            await conn.execute("""
                SELECT add_retention_policy('ohlcv_1h_cagg', INTERVAL '5 years');
            """)

            # 1-day aggregates: keep forever (no policy)

            logger.info("Retention policies created")

    # ============================================================
    # Batch Writer for High-Throughput Ingestion
    # ============================================================

    async def _batch_writer(self):
        """Background task to flush write batches"""
        while self._running:
            try:
                if self._write_batch:
                    await self._flush_batch()
                await asyncio.sleep(self._batch_timeout)
            except Exception as e:
                logger.error(f"Batch writer error: {e}")
                await asyncio.sleep(1)

    async def _flush_batch(self):
        """Flush write batch to database"""
        if not self._write_batch:
            return

        batch = self._write_batch
        self._write_batch = []

        async with self.pool.acquire() as conn:
            try:
                # Use COPY for bulk insert (fastest)
                records = [
                    (
                        tick.timestamp,
                        tick.symbol,
                        tick.exchange,
                        tick.price,
                        tick.volume,
                        tick.bid,
                        tick.ask,
                        tick.bid_size,
                        tick.ask_size,
                        tick.trade_type,
                        tick.metadata
                    )
                    for tick in batch
                ]

                await conn.copy_records_to_table(
                    'ticks',
                    records=records,
                    columns=[
                        'time', 'symbol', 'exchange', 'price', 'volume',
                        'bid', 'ask', 'bid_size', 'ask_size', 'trade_type', 'metadata'
                    ]
                )

            except Exception as e:
                logger.error(f"Batch write failed: {e}")
                # Re-queue failed batch
                self._write_batch = batch + self._write_batch

    async def write_tick(self, tick: TickData):
        """Write single tick (batched)"""
        self._write_batch.append(tick)

        # Force flush if batch is large
        if len(self._write_batch) >= self._batch_size:
            await self._flush_batch()

    async def write_ticks(self, ticks: List[TickData]):
        """Write multiple ticks"""
        self._write_batch.extend(ticks)
        if len(self._write_batch) >= self._batch_size:
            await self._flush_batch()

    @asynccontextmanager
    async def batch_writer(self):
        """Context manager for explicit batch writing"""
        try:
            yield self
        finally:
            await self._flush_batch()

    # ============================================================
    # Query Methods
    # ============================================================

    async def get_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        limit: int = 10000
    ) -> List[Dict]:
        """Get raw ticks for symbol in time range"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, symbol, exchange, price, volume, bid, ask, bid_size, ask_size, trade_type, metadata
                FROM ticks
                WHERE symbol = $1 AND time >= $2 AND time <= $3
                ORDER BY time ASC
                LIMIT $4
            """, symbol, start, end, limit)

            return [dict(row) for row in rows]

    async def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        limit: int = 10000
    ) -> List[Dict]:
        """Get OHLCV from continuous aggregate"""
        interval_map = {
            '1s': 'ohlcv_1s_cagg',
            '1m': 'ohlcv_1m_cagg',
            '5m': 'ohlcv_5m_cagg',
            '15m': 'ohlcv_15m_cagg',
            '1h': 'ohlcv_1h_cagg',
            '1d': 'ohlcv_1d_cagg'
        }

        table = interval_map.get(interval, 'ohlcv_1m_cagg')

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT bucket as time, symbol, open, high, low, close, volume, vwap, trade_count
                FROM {table}
                WHERE symbol = $1 AND bucket >= $2 AND bucket <= $3
                ORDER BY bucket ASC
                LIMIT $4
            """, symbol, start, end, limit)

            return [dict(row) for row in rows]

    async def get_vwap(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = '1m'
    ) -> List[Dict]:
        """Get VWAP data"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, symbol, vwap, volume, interval
                FROM vwap_data
                WHERE symbol = $1 AND time >= $2 AND time <= $3 AND interval = $4
                ORDER BY time ASC
            """, symbol, start, end, interval)

            return [dict(row) for row in rows]

    async def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """Get latest tick for symbol"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT time, price, volume, bid, ask
                FROM ticks
                WHERE symbol = $1
                ORDER BY time DESC
                LIMIT 1
            """, symbol)

            return dict(row) if row else None

    async def get_symbol_stats(self, symbol: str, start: datetime) -> Dict:
        """Get symbol statistics since start"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*) as trade_count,
                    SUM(volume) as total_volume,
                    MIN(price) as low_price,
                    MAX(price) as high_price,
                    AVG(price) as avg_price,
                    SUM(price * volume) / NULLIF(SUM(volume), 0) as vwap
                FROM ticks
                WHERE symbol = $1 AND time >= $2
            """, symbol, start)

            return dict(row) if row else {}

    async def stream_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        batch_size: int = 1000
    ) -> AsyncGenerator[List[Dict], None]:
        """Stream ticks in batches for large datasets"""
        offset = 0
        while True:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT time, symbol, exchange, price, volume, bid, ask, bid_size, ask_size, trade_type, metadata
                    FROM ticks
                    WHERE symbol = $1 AND time >= $2 AND time <= $3
                    ORDER BY time ASC
                    LIMIT $4 OFFSET $5
                """, symbol, start, end, batch_size, offset)

                if not rows:
                    break

                yield [dict(row) for row in rows]
                offset += batch_size

                if len(rows) < batch_size:
                    break

    async def get_market_profile(self, symbol: str, date: datetime) -> Dict:
        """Get market profile (TPO) for a symbol on a date"""
        start = date.replace(hour=9, minute=15, second=0, microsecond=0)
        end = start + timedelta(days=1)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    time_bucket('30 minute', time) AS bucket,
                    MIN(price) AS low,
                    MAX(price) AS high,
                    SUM(volume) AS volume,
                    COUNT(*) AS tpo_count
                FROM ticks
                WHERE symbol = $1 AND time >= $2 AND time < $3
                GROUP BY bucket
                ORDER BY bucket
            """, symbol, start, end)

            return {
                'symbol': symbol,
                'date': date.date().isoformat(),
                'profile': [dict(row) for row in rows]
            }

    # ============================================================
    # Maintenance
    # ============================================================

    async def refresh_continuous_aggregates(self):
        """Manually refresh continuous aggregates"""
        async with self.pool.acquire() as conn:
            for view in ['ohlcv_1s_cagg', 'ohlcv_1m_cagg', 'ohlcv_5m_cagg', 'ohlcv_15m_cagg', 'ohlcv_1h_cagg', 'ohlcv_1d_cagg']:
                await conn.execute(f"CALL refresh_continuous_aggregate('{view}', NULL, NULL);")
        logger.info("Continuous aggregates refreshed")

    async def get_db_stats(self) -> Dict:
        """Get database statistics"""
        async with self.pool.acquire() as conn:
            # Table sizes
            sizes = await conn.fetch("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC
            """)

            # Chunk stats
            chunks = await conn.fetch("""
                SELECT
                    hypertable_name,
                    COUNT(*) as chunk_count,
                    pg_size_pretty(SUM(pg_total_relation_size(chunk))) as total_size
                FROM timescaledb_information.chunks
                GROUP BY hypertable_name
            """)

            # Compression stats
            compression = await conn.fetch("""
                SELECT
                    hypertable_name,
                    COUNT(*) as compressed_chunks,
                    pg_size_pretty(SUM(pg_total_relation_size(chunk))) as compressed_size,
                    pg_size_pretty(SUM(pg_total_relation_size(chunk_uncompressed))) as uncompressed_size
                FROM timescaledb_information.compressed_chunks
                GROUP BY hypertable_name
            """)

            return {
                'table_sizes': [dict(r) for r in sizes],
                'chunks': [dict(r) for r in chunks],
                'compression': [dict(r) for r in compression]
            }

    async def shutdown(self):
        """Graceful shutdown"""
        self._running = False
        if self._write_task:
            self._write_task.cancel()
            try:
                await self._write_task
            except asyncio.CancelledError:
                pass
        await self._flush_batch()
        if self.pool:
            await self.pool.close()
        logger.info("TimescaleDB shutdown complete")


# ============================================================
# High-Level Tick Store Interface
# ============================================================

class TickStore:
    """
    High-level interface for tick data operations.
    Used by market data pipeline and strategies.
    """

    def __init__(self, db_manager: TimescaleDBManager):
        self.db = db_manager
        self._symbol_cache: Dict[str, datetime] = {}

    async def on_tick(self, tick: TickData):
        """Process incoming tick"""
        await self.db.write_tick(tick)

    async def on_ticks(self, ticks: List[TickData]):
        """Process batch of ticks"""
        await self.db.write_ticks(ticks)

    async def get_historical_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """Get historical ticks"""
        rows = await self.db.get_ticks(symbol, start, end)
        return [TickData(**row) for row in rows]

    async def get_ohlcv_bars(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> List[OHLCVBar]:
        """Get OHLCV bars"""
        rows = await self.db.get_ohlcv(symbol, interval, start, end)
        return [OHLCVBar(**row) for row in rows]

    async def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """Get latest tick for symbol"""
        row = await self.db.get_latest_price(symbol)
        if row:
            return TickData(
                symbol=row['symbol'],
                timestamp=row['time'],
                price=row['price'],
                volume=row['volume'],
                bid=row['bid'],
                ask=row['ask']
            )
        return None

    async def get_vwap(self, symbol: str, start: datetime, end: datetime) -> List[Dict]:
        """Get VWAP data"""
        return await self.db.get_vwap(symbol, start, end)

    async def get_market_stats(self, symbol: str, since: datetime) -> Dict:
        """Get market statistics"""
        return await self.db.get_symbol_stats(symbol, since)


# ============================================================
# Factory
# ============================================================

async def create_tick_store(dsn: str, pool_size: int = 20) -> TickStore:
    """Create and initialize tick store"""
    db = TimescaleDBManager(dsn, pool_size)
    await db.initialize()
    return TickStore(db)


__all__ = [
    'TimescaleDBManager',
    'TickStore',
    'TickData',
    'OHLCVBar',
    'create_tick_store'
]