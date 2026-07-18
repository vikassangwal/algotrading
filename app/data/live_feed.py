"""Dhan live market feed — REAL tick-by-tick data over Dhan's WebSocket v2.

Implements the documented Dhan binary feed protocol directly over the
`websockets` library (dhanhq's own client needs Python 3.10+; this file stays
3.8-compatible so it runs both locally and in the 3.11 Docker image).

Data flow:
    Dhan WS (wss://api-feed.dhan.co) → LiveTickCache (thread-safe, in-proc)
    → FastAPI /ws/live pushes ticks to the browser chart.

HONESTY CONTRACT: every tick carries `source`:
  * "dhan"     — real-time exchange tick (sub-second)
  * "yfinance" — delayed (~15 min) fallback quote, used ONLY when the Dhan
                 feed is not connected (bad/expired token, market closed, no creds)
The frontend must label delayed data as delayed. No fabricated ticks, ever.

Protocol notes (Dhan API v2 market feed):
  * URL: wss://api-feed.dhan.co?version=2&token=<jwt>&clientId=<id>&authType=2
  * Subscribe: JSON text frame {"RequestCode": 17, "InstrumentCount": n,
      "InstrumentList": [{"ExchangeSegment": "NSE_EQ", "SecurityId": "2885"}]}
    (RequestCode 15=ticker, 17=quote, 21=full; max 100 instruments per frame)
  * Responses are little-endian binary. 8-byte header:
      byte 0     : feed response code (2=ticker, 4=quote, 6=prev-close,
                   8=full, 50=server disconnect)
      bytes 1-2  : message length (uint16)
      byte 3     : exchange segment code
      bytes 4-7  : security id (uint32)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger("elco.livefeed")

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None

WS_URL = "wss://api-feed.dhan.co"

# Well-known index security IDs on the IDX_I segment (Dhan instrument master).
INDEX_IDS = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27,
    "SENSEX": 51,
}
_SEGMENT_IDX = "IDX_I"
_SEGMENT_EQ = "NSE_EQ"


class LiveTickCache:
    """Thread-safe {symbol: tick-dict} store shared between the feed thread
    and FastAPI request/websocket handlers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._ticks: Dict[str, dict] = {}

    def put(self, symbol: str, tick: dict):
        with self._lock:
            self._ticks[symbol.upper()] = tick

    def get(self, symbol: str) -> Optional[dict]:
        with self._lock:
            t = self._ticks.get(symbol.upper())
            return dict(t) if t else None

    def get_many(self, symbols: List[str]) -> Dict[str, dict]:
        with self._lock:
            out = {}
            for s in symbols:
                t = self._ticks.get(s.upper())
                if t:
                    out[s.upper()] = dict(t)
            return out

    def all_symbols(self) -> List[str]:
        with self._lock:
            return list(self._ticks.keys())


class DhanLiveFeed:
    """Background thread running an asyncio loop that keeps a Dhan WS
    connection alive, subscribes to symbols, parses binary ticks into the
    LiveTickCache, and reconnects with backoff on any failure."""

    def __init__(self, cache: LiveTickCache):
        self.cache = cache
        self.client_id = ""
        self.token = ""
        self._wanted: Dict[str, tuple] = {}   # symbol -> (segment, security_id)
        self._id_to_symbol: Dict[tuple, str] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._resubscribe = threading.Event()
        self.connected = False
        self.last_error: Optional[str] = None
        self.last_tick_ts: float = 0.0

    def _load_creds(self):
        """(Re)read creds lazily — .env may be loaded after this module imports."""
        if not (self.client_id and self.token):
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            self.client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
            self.token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()

    # -- public API ----------------------------------------------------------

    def has_credentials(self) -> bool:
        self._load_creds()
        return bool(self.client_id and self.token and websockets is not None)

    def ensure_running(self):
        """Start the feed thread once (idempotent)."""
        if not self.has_credentials():
            self.last_error = "Dhan credentials missing or websockets lib unavailable."
            return
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run_thread, daemon=True, name="DhanLiveFeed"
            )
            self._thread.start()
            logger.info("Dhan live feed thread started.")

    def subscribe(self, symbols: List[str]):
        """Add symbols (equities by name, indices by NIFTY/BANKNIFTY/...)."""
        added = False
        with self._lock:
            for s in symbols:
                s = s.upper().strip()
                if not s or s in self._wanted:
                    continue
                seg_id = self._resolve(s)
                if seg_id:
                    self._wanted[s] = seg_id
                    self._id_to_symbol[(seg_id[0], int(seg_id[1]))] = s
                    added = True
        if added:
            self._resubscribe.set()

    def status(self) -> dict:
        return {
            "credentials_present": self.has_credentials(),
            "connected": self.connected,
            "subscribed": sorted(self._wanted.keys()),
            "last_tick_age_sec": round(time.time() - self.last_tick_ts, 1) if self.last_tick_ts else None,
            "last_error": self.last_error,
        }

    # -- internals -----------------------------------------------------------

    def _resolve(self, symbol: str) -> Optional[tuple]:
        """Map an app symbol to (exchange_segment, security_id)."""
        if symbol in INDEX_IDS:
            return (_SEGMENT_IDX, str(INDEX_IDS[symbol]))
        try:
            from .dhan_provider import DhanRestClient
            sid = DhanRestClient._load_symbol_map().get(symbol)
            if sid:
                return (_SEGMENT_EQ, str(sid))
        except Exception as e:
            logger.warning(f"Security-id lookup failed for {symbol}: {e}")
        logger.warning(f"No security id for '{symbol}' — cannot subscribe on Dhan feed.")
        return None

    def _run_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        except Exception as e:  # pragma: no cover
            self.last_error = f"feed loop crashed: {e}"
            logger.error(self.last_error)
        finally:
            loop.close()
            self.connected = False

    @staticmethod
    def _market_open() -> bool:
        """NSE cash-market hours: 09:15–15:30 IST, Mon–Fri. Used only to pick a
        reconnect cadence — Dhan's feed drops idle connections after hours, so
        hammering it overnight is pointless."""
        from datetime import datetime, timezone, timedelta
        ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
        if ist.weekday() >= 5:
            return False
        minutes = ist.hour * 60 + ist.minute
        return (9 * 60 + 15) <= minutes <= (15 * 60 + 30)

    async def _run(self):
        backoff = 2
        url = f"{WS_URL}?version=2&token={self.token}&clientId={self.client_id}&authType=2"
        while not self._stop.is_set():
            try:
                async with websockets.connect(url, ping_interval=20, close_timeout=5) as ws:
                    self.connected = True
                    self.last_error = None
                    backoff = 2
                    logger.info("Dhan WS connected.")
                    await self._send_subscriptions(ws)
                    while not self._stop.is_set():
                        if self._resubscribe.is_set():
                            self._resubscribe.clear()
                            await self._send_subscriptions(ws)
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=5)
                        except asyncio.TimeoutError:
                            continue
                        if isinstance(msg, (bytes, bytearray)):
                            self._parse_binary(bytes(msg))
            except Exception as e:
                self.connected = False
                if self._market_open():
                    self.last_error = str(e)
                    wait = backoff
                    backoff = min(backoff * 2, 60)
                else:
                    # After hours the feed server drops connections — expected.
                    self.last_error = f"market closed; feed idle ({e})"
                    wait = 300  # retry every 5 min so we're live right at open
                logger.warning(f"Dhan WS disconnected ({e}); retrying in {wait}s.")
                await asyncio.sleep(wait)
        self.connected = False

    async def _send_subscriptions(self, ws):
        with self._lock:
            instruments = [
                {"ExchangeSegment": seg, "SecurityId": sid}
                for (seg, sid) in self._wanted.values()
            ]
        # Dhan caps 100 instruments per subscribe frame.
        for i in range(0, len(instruments), 100):
            chunk = instruments[i:i + 100]
            frame = {
                "RequestCode": 17,  # Quote mode: LTP + OHLC + volume
                "InstrumentCount": len(chunk),
                "InstrumentList": chunk,
            }
            await ws.send(json.dumps(frame))
        if instruments:
            logger.info(f"Subscribed {len(instruments)} instruments on Dhan feed.")

    # Binary parsing — struct formats are little-endian per Dhan docs.

    _SEG_CODES = {0: _SEGMENT_IDX, 1: _SEGMENT_EQ}

    def _parse_binary(self, buf: bytes):
        # A frame may contain several packets back-to-back.
        off = 0
        n = len(buf)
        while off + 8 <= n:
            code = buf[off]
            (mlen,) = struct.unpack_from("<H", buf, off + 1)
            seg_code = buf[off + 3]
            (sec_id,) = struct.unpack_from("<I", buf, off + 4)
            if mlen <= 0 or off + mlen > n:
                break  # malformed / partial — drop the rest
            body = buf[off + 8: off + mlen]
            self._handle_packet(code, seg_code, sec_id, body)
            off += mlen

    def _handle_packet(self, code: int, seg_code: int, sec_id: int, body: bytes):
        seg = self._SEG_CODES.get(seg_code)
        symbol = self._id_to_symbol.get((seg, sec_id)) if seg else None
        if not symbol:
            return
        now = time.time()
        try:
            if code == 2 and len(body) >= 8:        # Ticker: LTP + LTT
                ltp, ltt = struct.unpack_from("<fI", body, 0)
                tick = {"ltp": round(ltp, 2), "exch_ts": int(ltt)}
            elif code == 4 and len(body) >= 42:      # Quote packet
                (ltp, ltq, ltt, avg, vol, tsq, tbq,
                 o, c, h, l) = struct.unpack_from("<fhIfIIIffff", body, 0)
                tick = {
                    "ltp": round(ltp, 2), "exch_ts": int(ltt), "volume": int(vol),
                    "open": round(o, 2), "high": round(h, 2),
                    "low": round(l, 2), "prev_close": round(c, 2),
                }
            elif code == 6 and len(body) >= 8:       # Prev close
                pc, _oi = struct.unpack_from("<fI", body, 0)
                prev = self.cache.get(symbol) or {}
                prev.update({"prev_close": round(pc, 2)})
                self.cache.put(symbol, prev)
                return
            elif code == 50:
                logger.warning("Dhan server sent disconnect (code 50) — likely invalid/expired token.")
                self.last_error = "Server disconnect (code 50): token invalid/expired?"
                return
            else:
                return
        except struct.error:
            return

        merged = self.cache.get(symbol) or {}
        merged.update(tick)
        merged["symbol"] = symbol
        merged["ts"] = now
        merged["source"] = "dhan"
        merged["delayed"] = False
        if merged.get("prev_close"):
            try:
                merged["change_pct"] = round(
                    (merged["ltp"] - merged["prev_close"]) / merged["prev_close"] * 100, 2
                )
            except (ZeroDivisionError, TypeError):
                pass
        self.cache.put(symbol, merged)
        self.last_tick_ts = now


class FallbackPoller:
    """SECOND OPTION when the Dhan feed can't deliver: near-real-time quotes
    from public exchange websites, honestly labeled.

      Tier 2a  equities → BSE website API  (source='bse_web', ~few sec delay)
      Tier 2b  indices  → NSE allIndices   (source='nse_web', ~few sec delay)

    The poller only writes a symbol into the cache when the Dhan feed hasn't
    ticked it recently — real ticks always win. Tier 3 (yfinance, ~15 min)
    stays in the frontend/quote endpoint as the last resort.
    """

    POLL_SEC = 5
    IDLE_SEC = 120           # off-market cadence
    DHAN_FRESH_SEC = 10      # if Dhan ticked within this, it owns the symbol

    _NSE_INDEX_NAMES = {
        "NIFTY": "NIFTY 50",
        "BANKNIFTY": "NIFTY BANK",
        "FINNIFTY": "NIFTY FINANCIAL SERVICES",
    }

    def __init__(self, cache: LiveTickCache, dhan_feed: DhanLiveFeed):
        self.cache = cache
        self.dhan = dhan_feed
        self._wanted: set = set()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.last_poll_ts: Optional[float] = None
        self.last_error: Optional[str] = None

    def subscribe(self, symbols: List[str]):
        with self._lock:
            for s in symbols:
                s = s.upper().strip()
                if s:
                    self._wanted.add(s)

    def ensure_running(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="FallbackPoller"
            )
            self._thread.start()
            logger.info("Fallback quote poller started (BSE equities + NSE indices).")

    def status(self) -> dict:
        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "subscribed": sorted(self._wanted),
            "last_poll_age_sec": round(time.time() - self.last_poll_ts, 1) if self.last_poll_ts else None,
            "last_error": self.last_error,
        }

    # -- internals -----------------------------------------------------------

    def _dhan_owns(self, symbol: str) -> bool:
        t = self.cache.get(symbol)
        return bool(
            t and t.get("source") == "dhan"
            and time.time() - t.get("time", 0) < self.DHAN_FRESH_SEC
        )

    def _loop(self):
        while not self._stop.is_set():
            try:
                in_hours = DhanLiveFeed._market_open()
                with self._lock:
                    wanted = list(self._wanted)
                if wanted and in_hours:
                    self._poll(wanted)
                self.last_poll_ts = time.time()
                wait = self.POLL_SEC if in_hours else self.IDLE_SEC
            except Exception as e:
                self.last_error = str(e)
                logger.warning(f"Fallback poll failed: {e}")
                wait = self.POLL_SEC * 3
            self._stop.wait(wait)

    def _poll(self, symbols: List[str]):
        indices = [s for s in symbols if s in INDEX_IDS or s in self._NSE_INDEX_NAMES]
        equities = [s for s in symbols if s not in indices and not self._dhan_owns(s)]

        # Equities via BSE website API.
        if equities:
            try:
                from .bse_provider import bse_provider
                for sym, q in bse_provider.get_many(equities).items():
                    if not self._dhan_owns(sym):
                        self.cache.put(sym, q)
            except Exception as e:
                logger.warning(f"BSE fallback failed: {e}")

        # Indices via NSE allIndices (one request covers all).
        need_idx = [s for s in indices if not self._dhan_owns(s)]
        if need_idx:
            try:
                from .nse_provider import nse_provider
                data = nse_provider._get_json("/api/allIndices")
                rows = (data or {}).get("data") or []
                by_name = {r.get("index"): r for r in rows}
                for sym in need_idx:
                    row = by_name.get(self._NSE_INDEX_NAMES.get(sym, sym))
                    if row and row.get("last"):
                        self.cache.put(sym, {
                            "symbol": sym,
                            "ltp": float(row["last"]),
                            "change_pct": float(row.get("percentChange") or 0),
                            "prev_close": float(row.get("previousClose") or 0) or None,
                            "source": "nse_web",
                            "delayed": False,
                            "latency_note": "NSE website feed (~few seconds behind exchange)",
                            "time": time.time(),
                        })
            except Exception as e:
                logger.warning(f"NSE index fallback failed: {e}")


# Process-wide singletons.
live_cache = LiveTickCache()
live_feed = DhanLiveFeed(live_cache)
fallback_poller = FallbackPoller(live_cache, live_feed)
