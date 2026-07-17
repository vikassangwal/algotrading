"""Data provider abstraction.

All analysis modules consume this interface only — so Zerodha / Upstox /
Angel One / Fyers / TrueData can be dropped in later without touching the
analysis code. Today the MockProvider (see mock_provider.py) implements it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class Quote:
    symbol: str
    ltp: float
    change_pct: float
    volume: int
    ts: datetime


@dataclass
class OptionChainRow:
    strike: float
    call_oi: int
    put_oi: int
    call_oi_change: int
    put_oi_change: int
    call_iv: float
    put_iv: float


@dataclass
class OptionChain:
    symbol: str
    spot: float
    expiry: str
    rows: list[OptionChainRow] = field(default_factory=list)


@dataclass
class NewsItem:
    headline: str
    source: str
    ts: datetime
    symbols: list[str] = field(default_factory=list)


@dataclass
class Fundamentals:
    symbol: str
    pe: float
    pb: float
    roe: float
    roce: float
    debt_to_equity: float
    promoter_holding_pct: float
    promoter_pledge_pct: float
    earnings_growth_pct: float  # YoY


class DataProvider(ABC):
    """Interface every broker/data adapter must implement."""
    def __init__(self):
        self.live_cache = {}

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        """timeframe: '1m' | '5m' | '15m' | '1d'"""

    @abstractmethod
    def get_option_chain(self, symbol: str) -> OptionChain: ...

    @abstractmethod
    def get_news(self, limit: int = 20) -> list[NewsItem]: ...

    @abstractmethod
    def get_fundamentals(self, symbol: str) -> dict:
        """Returns a dict with fundamental metrics (e.g., pe_ratio, roe, net_income)."""

    @abstractmethod
    def get_macro_data(self) -> dict:
        """Returns a dict with macroeconomic indicators (e.g., gdp_growth, pmi)."""

    @abstractmethod
    def get_intermarket_data(self) -> dict:
        """Returns a dict with cross-asset data (e.g., us_10y_yield, dxy)."""

    @abstractmethod
    def get_sector_data(self, sector_name: str) -> dict:
        """Returns a dict with sector-specific data (e.g., sector_pe, momentum)."""

    @abstractmethod
    def get_derivatives_data(self, symbol: str) -> dict:
        """Returns a dict with F&O metrics (e.g., pcr, rollover_pct)."""

    @abstractmethod
    def get_sentiment_data(self, symbol: str) -> dict:
        """Returns a dict with sentiment and alt data (e.g., fear_greed_index, gex)."""

    @abstractmethod
    def get_quant_data(self, symbol: str) -> dict:
        """Returns a dict with quant metrics (e.g., var_95_pct, xgboost_prob)."""

    @abstractmethod
    def get_portfolio_data(self) -> dict:
        """Returns a dict with current portfolio exposures and correlations."""
