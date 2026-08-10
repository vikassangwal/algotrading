"""Real NSE India public-data adapter.

Fetches institutional-flow data that no other provider supplies:
  - FII/DII daily net buy/sell (cash market)
  - Security-wise delivery quantity / delivery %  (from the bhavcopy)
  - Bulk & block deals

NSE's public JSON endpoints require a primed session (a real browser-like
User-Agent plus the cookies NSE hands out on the home page) or they return 401
/ time out. This adapter primes a session, retries once, caches every result
for the trading day (the underlying data only updates end-of-day), and returns
None on any failure so callers degrade gracefully instead of crashing.

All methods are best-effort. Nothing here places orders or mutates state.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("elco.nse")

_BASE = "https://www.nseindia.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": _BASE,
}


class NSEProvider:
    """Thin, cached client over NSE India's public data endpoints."""

    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self._session_ts: float = 0.0
        # {key: (ist_day, value)} — one entry per IST trading day.
        self._cache: Dict[str, Any] = {}
        # {key: monotonic-expiry} — short negative cache so a blocked/failing
        # NSE endpoint doesn't get re-hit (with its 10s×2 retries) on every
        # analyze request.
        self._failed_until: Dict[str, float] = {}

    NEGATIVE_CACHE_TTL = 600  # seconds to back off after a failed fetch

    @staticmethod
    def _ist_day() -> int:
        """Day number in IST (UTC+5:30). NSE data rolls on IST days, so keying
        the cache on UTC days would hold evening-published data stale until
        05:30 IST the next morning."""
        return int((time.time() + 5.5 * 3600) // 86400)

    # -- session management -------------------------------------------------

    def _get_session(self) -> requests.Session:
        """Return a cookie-primed session, refreshing it every ~5 minutes.

        NSE requires you to hit the home page first so it can set the cookies
        its JSON endpoints validate against.
        """
        now = time.time()
        if self._session is not None and (now - self._session_ts) < 300:
            return self._session

        s = requests.Session()
        s.headers.update(_HEADERS)
        try:
            r = s.get(_BASE, timeout=self.timeout)
            if r.status_code == 200:
                s.get(f"{_BASE}/market-data/live-equity-market", timeout=self.timeout)
        except Exception as e:
            logger.warning(f"NSE session priming failed: {e}")
        self._session = s
        self._session_ts = now
        return s

    def _get_json(self, path: str) -> Optional[Any]:
        """GET a JSON endpoint with one automatic session-refresh retry."""
        url = f"{_BASE}{path}"
        for attempt in (1, 2):
            try:
                s = self._get_session()
                resp = s.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"NSE {path} → HTTP {resp.status_code} (attempt {attempt})")
            except Exception as e:
                logger.warning(f"NSE {path} failed (attempt {attempt}): {e}")
            # Force a fresh session before the second try.
            self._session = None
        return None

    def _cached(self, key: str, producer) -> Any:
        """IST-day-scoped cache with a short negative cache on failures.

        Success: cached until the IST day rolls over (NSE data is end-of-day).
        Failure: remembered for NEGATIVE_CACHE_TTL so callers don't pay the
        full timeout+retry cost on every request while NSE is blocking us.
        """
        day = self._ist_day()
        hit = self._cache.get(key)
        if hit is not None and hit[0] == day:
            return hit[1]
        # Recent failure? Don't re-hit NSE yet.
        if self._failed_until.get(key, 0.0) > time.monotonic():
            return None
        value = producer()
        if value is not None:
            self._cache[key] = (day, value)
            self._failed_until.pop(key, None)
        else:
            self._failed_until[key] = time.monotonic() + self.NEGATIVE_CACHE_TTL
        return value

    # -- public data --------------------------------------------------------

    def get_fii_dii_activity(self) -> Optional[Dict[str, float]]:
        """FII & DII net cash-market flow (INR crore) for the latest session.

        Returns {'fii_net': float, 'dii_net': float, 'date': str} or None.
        Positive = net buying.
        """
        def _fetch():
            data = self._get_json("/api/fiidiiTradeReact")
            if not isinstance(data, list) or not data:
                return None
            fii_net = dii_net = None
            date = None
            for row in data:
                cat = str(row.get("category", "")).upper()
                try:
                    net = float(row.get("netValue", row.get("net", 0)))
                except (TypeError, ValueError):
                    continue
                date = row.get("date", date)
                if "FII" in cat or "FPI" in cat:
                    fii_net = net
                elif "DII" in cat:
                    dii_net = net
            if fii_net is None and dii_net is None:
                return None
            return {"fii_net": fii_net or 0.0, "dii_net": dii_net or 0.0, "date": date}

        return self._cached("fii_dii", _fetch)

    def get_delivery_data(self, symbol: str) -> Optional[Dict[str, float]]:
        """Delivery quantity and delivery % for a symbol (latest session).

        Primary: NSE quote-equity API (often 403s). Fallback: the daily
        sec_bhavdata_full CSV from NSE archives (real end-of-day data,
        publicly served without cookie games).
        Returns {'delivery_percentage': float, 'delivery_volume': float,
        'traded_volume': float, 'source': str} or None.
        """
        sym = symbol.upper()

        def _fetch():
            data = self._get_json(f"/api/quote-equity?symbol={sym}&section=trade_info")
            if isinstance(data, dict):
                sec = data.get("securityWiseDP") or {}
                deliv_pct = sec.get("deliveryToTradedQuantity")
                deliv_qty = sec.get("deliveryQuantity")
                traded = sec.get("quantityTraded")
                if deliv_pct is not None or deliv_qty is not None:
                    try:
                        return {
                            "delivery_percentage": float(deliv_pct) if deliv_pct is not None else None,
                            "delivery_volume": float(deliv_qty) if deliv_qty is not None else None,
                            "traded_volume": float(traded) if traded is not None else None,
                            "source": "nse_quote_api",
                        }
                    except (TypeError, ValueError):
                        pass
            # Fallback: end-of-day bhavcopy from NSE archives.
            row = self._bhavcopy_row(sym)
            if row is not None:
                return row
            return None

        return self._cached(f"deliv:{sym}", _fetch)

    def _bhavcopy_row(self, sym: str) -> Optional[Dict[str, float]]:
        """Look up a symbol in the latest sec_bhavdata_full CSV (tries today
        back through the last 6 calendar days to skip weekends/holidays)."""
        table = self._cached("bhavcopy", self._fetch_bhavcopy)
        if not table:
            return None
        row = table.get(sym)
        if row is None:
            return None
        return dict(row, source="nse_bhavcopy_eod")

    def _fetch_bhavcopy(self) -> Optional[Dict[str, Dict[str, float]]]:
        import csv
        import io
        from datetime import datetime, timedelta, timezone as _tz

        ist_now = datetime.now(_tz(timedelta(hours=5, minutes=30)))
        s = self._get_session()
        for back in range(0, 7):
            day = ist_now - timedelta(days=back)
            if day.weekday() >= 5:
                continue
            # NSE serves archives from two hosts; either can 503 at times.
            fname = f"sec_bhavdata_full_{day.strftime('%d%m%Y')}.csv"
            resp = None
            for host in ("nsearchives.nseindia.com", "archives.nseindia.com"):
                try:
                    r = s.get(f"https://{host}/products/content/{fname}", timeout=self.timeout)
                    if r.status_code == 200 and len(r.content) > 1000:
                        resp = r
                        break
                except Exception:
                    continue
            try:
                if resp is None:
                    continue
                out: Dict[str, Dict[str, float]] = {}
                reader = csv.DictReader(io.StringIO(resp.text))
                for r in reader:
                    r = {k.strip(): (v.strip() if isinstance(v, str) else v)
                         for k, v in r.items() if k}
                    if r.get("SERIES") not in ("EQ", "BE"):
                        continue
                    try:
                        row = {
                            "delivery_percentage": float(r["DELIV_PER"]),
                            "delivery_volume": float(r["DELIV_QTY"]),
                            "traded_volume": float(r["TTL_TRD_QNTY"]),
                            "date": r.get("DATE1", ""),
                        }
                        # Close + turnover let the market scanner rank the
                        # ENTIRE exchange's liquidity from this one file.
                        try:
                            row["close"] = float(r.get("CLOSE_PRICE") or 0)
                            row["turnover"] = float(r.get("TURNOVER_LACS") or 0) * 1e5
                        except (TypeError, ValueError):
                            pass
                        out[r["SYMBOL"]] = row
                    except (KeyError, ValueError):
                        continue
                if out:
                    logger.info(f"Bhavcopy loaded: {day.strftime('%d-%b')} ({len(out)} symbols).")
                    return out
            except Exception as e:
                logger.warning(f"Bhavcopy fetch failed for {day.date()}: {e}")
        return None

    def get_bulk_deals(self) -> Optional[List[Dict[str, Any]]]:
        """Latest bulk deals. Returns a list of deal dicts or None."""
        return self._cached("bulk", lambda: self._deals("/api/historical/bulk-deals"))

    def get_block_deals(self) -> Optional[List[Dict[str, Any]]]:
        """Latest block deals. Returns a list of deal dicts or None."""
        return self._cached("block", lambda: self._deals("/api/block-deal"))

    def _deals(self, path: str) -> Optional[List[Dict[str, Any]]]:
        data = self._get_json(path)
        if isinstance(data, dict):
            data = data.get("data") or data.get("BULK_DEALS_DATA") or []
        if not isinstance(data, list):
            return None
        return data

    def get_block_deal_sentiment(self, symbol: str) -> Optional[str]:
        """Coarse buy/sell lean for a symbol's block deals, or None if none."""
        deals = self.get_block_deals()
        if not deals:
            return None
        sym = symbol.upper()
        buys = sells = 0
        for d in deals:
            name = str(d.get("symbol", d.get("BD_SYMBOL", ""))).upper()
            if name != sym:
                continue
            btype = str(d.get("buySell", d.get("BD_BUY_SELL", ""))).upper()
            if "BUY" in btype:
                buys += 1
            elif "SELL" in btype:
                sells += 1
        if buys == 0 and sells == 0:
            return None
        if buys > sells:
            return "Bullish"
        if sells > buys:
            return "Bearish"
        return "Neutral"


# Process-wide singleton — cookie priming is expensive, so share one session.
nse_provider = NSEProvider()
