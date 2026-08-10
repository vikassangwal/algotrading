import logging
import os
import sys
import random
from datetime import datetime, timezone, timedelta
import pandas as pd
from dotenv import load_dotenv

# Add dhan_api to path so it can import its own dependencies correctly
sys.path.append(os.path.join(os.path.dirname(__file__), 'dhan_api'))

try:
    import yfinance as yf
except ImportError:
    yf = None

from typing import List
from .provider import DataProvider, Quote, Candle, OptionChain, OptionChainRow, NewsItem, Fundamentals
from .mock_provider import MockProvider

logger = logging.getLogger("elco.dhan")
load_dotenv()

import requests

# Indices don't take the .NS suffix on Yahoo — they have dedicated tickers.
# Bare equity symbols get ".NS" appended (NSE default).
_YF_INDEX_MAP = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTYBANK": "^NSEBANK",
    "SENSEX": "^BSESN",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "INDIAVIX": "^INDIAVIX",
}


def _yf_symbol(symbol: str) -> str:
    """Map an app symbol to its yfinance ticker (index-aware)."""
    s = symbol.upper().strip()
    if s in _YF_INDEX_MAP:
        return _YF_INDEX_MAP[s]
    if s.startswith("^") or "." in s or "=" in s:
        return s  # already a Yahoo ticker (index, commodity, forex, or decorated)
    return f"{s}.NS"

class DhanRestClient:
    # Class-level cache of the NSE-equity symbol -> security_id map (22MB CSV, load once).
    _symbol_map = None

    def __init__(self, client_id, token):
        self.client_id = client_id
        self.token = token
        self.base_url = "https://api.dhan.co/v2"
        self.headers = {
            "access-token": token,
            "client-id": client_id,
            "Content-Type": "application/json"
        }

    def get_fund_limit(self):
        resp = requests.get(f"{self.base_url}/fundlimit", headers=self.headers)
        if resp.status_code == 200:
            return resp.json()
        return None

    def get_ltp(self, exchange_segment, security_id):
        # We need security_id for Dhan. Since we don't have a symbol mapper in this prototype,
        # we will use yfinance for LTP as fallback, but this method is here for OMS.
        pass

    @classmethod
    def _load_symbol_map(cls):
        """Lazily build {TRADING_SYMBOL: security_id} for NSE equities from the
        bundled Dhan instrument master. Cached on the class after first load."""
        if cls._symbol_map is not None:
            return cls._symbol_map
        csv_path = os.path.join(
            os.path.dirname(__file__), "dhan_api", "Dependencies",
            "all_instrument 2025-05-19.csv",
        )
        mapping = {}
        try:
            df = pd.read_csv(csv_path, low_memory=False)
            nse_eq = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_SEGMENT"] == "E")]
            for sym, sid in zip(nse_eq["SEM_TRADING_SYMBOL"], nse_eq["SEM_SMST_SECURITY_ID"]):
                mapping[str(sym).upper()] = str(int(sid))
            logger.info(f"Loaded {len(mapping)} NSE-equity security IDs from instrument master.")
        except Exception as e:
            logger.error(f"Failed to load Dhan instrument master: {e}")
        cls._symbol_map = mapping
        return mapping

    def get_security_id(self, symbol):
        """Return the Dhan NSE-equity security_id for a trading symbol, or None."""
        return self._load_symbol_map().get(symbol.upper())

    def place_order(self, symbol, quantity, transaction_type):
        """
        Submit a REAL market order to Dhan (NSE equity, intraday).

        Defense in depth: even though callers are already gated by
        live_trading_enabled(), this refuses to hit the broker unless the
        LIVE_TRADING env flag is explicitly 'true'. Returns the broker order id
        on success, or None on any failure (so the caller does not record a fill).
        """
        if os.getenv("LIVE_TRADING", "false").strip().lower() != "true":
            logger.error(
                "DhanRestClient.place_order called without LIVE_TRADING=true — refusing. "
                "This is a safety backstop; no real order was sent."
            )
            return None

        security_id = self.get_security_id(symbol)
        if not security_id:
            logger.error(f"No NSE security_id found for symbol '{symbol}'. Cannot place real order.")
            return None

        side = transaction_type.upper()
        if side not in ("BUY", "SELL"):
            logger.error(f"Invalid transaction_type '{transaction_type}'. Must be BUY or SELL.")
            return None

        payload = {
            "dhanClientId": self.client_id,
            "transactionType": side,
            "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY",
            "orderType": "MARKET",
            "validity": "DAY",
            "securityId": security_id,
            "quantity": int(quantity),
            "price": 0,
            "triggerPrice": 0,
            "disclosedQuantity": 0,
            "afterMarketOrder": False,
        }
        try:
            resp = requests.post(
                f"{self.base_url}/orders", headers=self.headers, json=payload, timeout=10
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                order_id = data.get("orderId") or data.get("data", {}).get("orderId")
                if order_id:
                    logger.info(f"Dhan LIVE order accepted: {side} {quantity} {symbol} -> orderId {order_id}")
                    return str(order_id)
                logger.error(f"Dhan order response missing orderId: {data}")
                return None
            logger.error(f"Dhan order rejected (HTTP {resp.status_code}): {resp.text}")
            return None
        except Exception as e:
            logger.error(f"Dhan order placement failed: {e}")
            return None

    def get_order_status(self, order_id: str):
        """Fetch REAL order status from Dhan (GET /v2/orders/{order-id}).

        Returns {'order_id', 'status', 'filled_qty', 'avg_price', 'raw_status'}
        or None if the lookup fails. Status is normalized to one of
        CONFIRMED (traded), PENDING, REJECTED, CANCELLED, UNKNOWN.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/orders/{order_id}", headers=self.headers, timeout=10
            )
            if resp.status_code != 200:
                logger.warning(f"Dhan order status HTTP {resp.status_code} for {order_id}")
                return None
            data = resp.json()
            if isinstance(data, list):
                data = data[0] if data else {}
            raw = str(data.get("orderStatus", "")).upper()
            normalized = {
                "TRADED": "CONFIRMED",
                "PART_TRADED": "PENDING",
                "PENDING": "PENDING",
                "TRANSIT": "PENDING",
                "REJECTED": "REJECTED",
                "CANCELLED": "CANCELLED",
                "EXPIRED": "CANCELLED",
            }.get(raw, "UNKNOWN")
            return {
                "order_id": str(order_id),
                "status": normalized,
                "raw_status": raw,
                "filled_qty": data.get("filledQty") or data.get("filled_qty") or 0,
                "avg_price": data.get("averageTradedPrice") or data.get("avg_price") or 0,
            }
        except Exception as e:
            logger.warning(f"Dhan order status lookup failed for {order_id}: {e}")
            return None

class DhanProvider(DataProvider):
    def __init__(self):
        # We also keep a mock provider as fallback for things Dhan doesn't provide
        self.fallback = MockProvider(seed=999)
        self.rest_client = None
        self._initialize_dhan()

    def _initialize_dhan(self):
        client_code = os.getenv("DHAN_CLIENT_ID")
        token_id = os.getenv("DHAN_ACCESS_TOKEN")
        
        if not client_code or not token_id:
            logger.warning("Dhan Credentials not found in .env. Dhan API will not work.")
            return

        try:
            self.rest_client = DhanRestClient(client_code, token_id)
            # Test connection
            limits = self.rest_client.get_fund_limit()
            if limits is not None:
                logger.info("Successfully initialized Dhan REST wrapper!")
            else:
                logger.error("Dhan API returned error during init.")
                self.rest_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Dhan API: {e}")
            self.rest_client = None

    def get_quote(self, symbol: str) -> Quote:
        # Use yfinance for Quotes to avoid complex NSE symbol -> ID mapping for now.
        # This provides REAL market data to the UI without the mapping overhead.
        try:
            from ..yf_cache import get_safe_ltp
            ltp = get_safe_ltp(symbol)
            if ltp > 0:
                return Quote(
                    symbol=symbol.upper(),
                    ltp=float(ltp),
                    change_pct=0.0, 
                    volume=0,
                    ts=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.error(f"Error fetching LTP for {symbol}: {e}")
            
        return self.fallback.get_quote(symbol)

    def get_candles(self, symbol: str, timeframe: str, count: int) -> List[Candle]:
        # 1. Check Background Daemon Cache First
        if hasattr(self, 'live_cache') and self.live_cache:
            charts = self.live_cache.get("charts", {})
            sym_key = f"{symbol}.NS"
            if sym_key in charts:
                df = charts[sym_key]
                if not df.empty:
                    df = df.tail(count)
                    candles = []
                    for idx, row in df.iterrows():
                        candles.append(Candle(
                            ts=idx if isinstance(idx, datetime) else datetime.now(),
                            open=float(row['Open']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            close=float(row['Close']),
                            volume=int(row['Volume'])
                        ))
                    if candles:
                        return candles
                        
        # 2. Always try yfinance as the primary fallback if Dhan fails or is uninitialized
        try:
            if yf:
                # Map timeframe to yfinance format
                interval = "1d" if timeframe == "1d" else "15m"
                ticker = yf.Ticker(_yf_symbol(symbol))
                df = ticker.history(period="1y" if timeframe == "1d" else "5d", interval=interval)
                if not df.empty:
                    df = df.tail(count)
                    candles = []
                    for idx, row in df.iterrows():
                        candles.append(Candle(
                            ts=idx if isinstance(idx, datetime) else datetime.now(),
                            open=float(row['Open']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            close=float(row['Close']),
                            volume=int(row['Volume'])
                        ))
                    if candles:
                        return candles
        except Exception as e:
            logger.error(f"Error fetching yfinance candles for {symbol}: {e}")
            
        return self.fallback.get_candles(symbol, timeframe, count)

    def get_option_chain(self, symbol: str) -> OptionChain:
        # Check Background Daemon Cache First
        if hasattr(self, 'live_cache') and self.live_cache:
            chains = self.live_cache.get("option_chains", {})
            sym_key = f"{symbol}.NS"
            if sym_key in chains:
                cached_chain = chains[sym_key]
                expiry = cached_chain["expiry"]
                calls = cached_chain["calls"]
                puts = cached_chain["puts"]
                
                rows = []
                # Attempt a simple merge by strike
                for idx, call_row in calls.iterrows():
                    strike = float(call_row['strike'])
                    put_row = puts[puts['strike'] == strike]
                    if not put_row.empty:
                        rows.append(OptionChainRow(
                            strike=strike,
                            call_oi=int(call_row['openInterest']),
                            put_oi=int(put_row.iloc[0]['openInterest']),
                            call_oi_change=0,
                            put_oi_change=0,
                            call_iv=float(call_row.get('impliedVolatility', 0.0)),
                            put_iv=float(put_row.iloc[0].get('impliedVolatility', 0.0))
                        ))
                if rows:
                    return OptionChain(symbol=symbol, spot=0.0, expiry=expiry, rows=rows)

        # Fallback to mock for now until we specifically build Tradehull Option Chain parser.
        return self.fallback.get_option_chain(symbol)

    def get_news(self, limit: int = 5) -> List[NewsItem]:
        try:
            if yf:
                # Use NIFTY 50 ETF as a proxy for general market news
                ticker = yf.Ticker("^NSEI") 
                news_data = ticker.news
                if not news_data:
                    # Fallback to Reliance for news if NIFTY has none
                    ticker = yf.Ticker("RELIANCE.NS")
                    news_data = ticker.news
                    
                if news_data:
                    items = []
                    for item in news_data[:limit]:
                        # yfinance news items have 'title', 'publisher', 'providerPublishTime'
                        ts = datetime.fromtimestamp(item.get('providerPublishTime', 0), tz=timezone.utc)
                        items.append(NewsItem(
                            headline=item.get('title', 'Market Update'),
                            source=item.get('publisher', 'yfinance'),
                            ts=ts,
                            symbols=[]
                        ))
                    if items:
                        return items
        except Exception as e:
            logger.error(f"Error fetching yfinance news: {e}")
            
        return self.fallback.get_news(limit)

    def get_fundamentals(self, symbol: str) -> dict:
        """Fetch real fundamentals from yfinance."""
        if not yf:
            return self.fallback.get_fundamentals(symbol)
            
        try:
            ticker = yf.Ticker(_yf_symbol(symbol)) # NSE suffix
            info = ticker.info
            return {
                "pe_ratio": info.get("trailingPE", 15.0),
                "pb_ratio": info.get("priceToBook", 2.0),
                "roe": info.get("returnOnEquity", 0.15),
                "roce": 0.18,
                "current_ratio": info.get("currentRatio", 1.5),
                "total_debt": info.get("totalDebt", 0),
                "shareholder_equity": info.get("totalStockholderEquity", 100000),
                "revenue": info.get("totalRevenue", 500000),
                "net_income": info.get("netIncomeToCommon", 50000),
                "eps_growth_yoy": info.get("earningsQuarterlyGrowth", 0.10)
            }
        except Exception as e:
            logger.error(f"yfinance fundamental error: {e}")
            return self.fallback.get_fundamentals(symbol)

    def get_macro_data(self) -> dict:
        return self.fallback.get_macro_data()

    def get_intermarket_data(self) -> dict:
        return self.fallback.get_intermarket_data()

    def get_sector_data(self, sector_name: str) -> dict:
        return self.fallback.get_sector_data(sector_name)

    def get_derivatives_data(self, symbol: str) -> dict:
        return self.fallback.get_derivatives_data(symbol)

    def get_sentiment_data(self, symbol: str) -> dict:
        # Start from the mock baseline, then overlay REAL NSE institutional flow
        # (FII/DII net + block-deal lean) when the NSE endpoints are reachable.
        data = self.fallback.get_sentiment_data(symbol)
        try:
            from .nse_provider import nse_provider
            flows = nse_provider.get_fii_dii_activity()
            if flows:
                data["fii_net_buying"] = flows.get("fii_net")
                data["dii_net_buying"] = flows.get("dii_net")
                data["fii_dii_date"] = flows.get("date")
            block = nse_provider.get_block_deal_sentiment(symbol)
            if block:
                data["block_deals_sentiment"] = block
        except Exception as e:
            logger.warning(f"NSE institutional-flow overlay failed for {symbol}: {e}")
        return data

    def get_quant_data(self, symbol: str) -> dict:
        """HONESTY: no mock passthrough. The mock's hardcoded values
        (xgboost_win_probability=0.75, bid_ask_imbalance, pair z-scores)
        were inflating REAL analyses. Absent data must be absent — the
        quant branches already skip None fields; the ML engine still gets
        real candles via raw_data['df']."""
        return {}

    def get_portfolio_data(self) -> dict:
        return self.fallback.get_portfolio_data()
