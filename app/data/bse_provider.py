"""BSE web-API quotes — the no-credentials second option for live prices.

When the Dhan WebSocket is unavailable (no/expired token, connection down),
this provider gives near-real-time quotes (few-second delay) from BSE's public
website API — no account, no token, no cookie games. Third tier below this is
yfinance (~15 min delayed).

Honesty labels: source='bse_web', delayed=False but latency_note explains the
few-second website delay. Symbols not listed on BSE return None — never a
made-up price.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional

import requests

logger = logging.getLogger("elco.bse")

BASE = "https://api.bseindia.com/BseIndiaAPI/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json",
}
SCRIP_TTL = 20 * 3600          # refresh symbol->scripcode map daily
QUOTE_CACHE_SEC = 3            # don't hammer BSE more than ~1 req/3s/symbol
_INDEX_ALIASES = {"SENSEX": "1", "BSE SENSEX": "1"}  # BSE index codes


class BSEProvider:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._lock = threading.Lock()
        self._scrip_map: Dict[str, str] = {}
        self._scrip_fetched_at = 0.0
        self._quote_cache: Dict[str, tuple] = {}  # sym -> (monotonic_ts, quote)

    # -- scrip master --------------------------------------------------------

    def _ensure_scrips(self) -> bool:
        with self._lock:
            if self._scrip_map and time.monotonic() - self._scrip_fetched_at < SCRIP_TTL:
                return True
        try:
            r = requests.get(
                f"{BASE}/ListofScripData/w",
                params={"Group": "", "Scripcode": "", "industry": "",
                        "segment": "Equity", "status": "Active"},
                headers=HEADERS, timeout=30,
            )
            r.raise_for_status()
            rows = r.json()
            mapping = {str(x["scrip_id"]).upper(): str(x["SCRIP_CD"])
                       for x in rows if x.get("scrip_id") and x.get("SCRIP_CD")}
            if not mapping:
                return False
            with self._lock:
                self._scrip_map = mapping
                self._scrip_fetched_at = time.monotonic()
            logger.info(f"BSE scrip master loaded: {len(mapping)} symbols.")
            return True
        except Exception as e:
            logger.warning(f"BSE scrip master fetch failed: {e}")
            return bool(self._scrip_map)

    def scripcode(self, symbol: str) -> Optional[str]:
        if not self._ensure_scrips():
            return None
        return self._scrip_map.get(symbol.upper().strip())

    # -- quotes --------------------------------------------------------------

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Near-real-time quote from BSE's website API. None if unlisted/down."""
        sym = symbol.upper().strip()
        now = time.monotonic()
        cached = self._quote_cache.get(sym)
        if cached and now - cached[0] < QUOTE_CACHE_SEC:
            return cached[1]

        code = self.scripcode(sym)
        if code is None:
            return None
        try:
            r = requests.get(
                f"{BASE}/getScripHeaderData/w",
                params={"Debtflag": "", "scripcode": code, "seriesid": ""},
                headers=HEADERS, timeout=self.timeout,
            )
            if r.status_code != 200:
                return None
            d = r.json()
            cur = d.get("CurrRate") or {}
            head = d.get("Header") or {}
            ltp = float(cur.get("LTP") or 0)
            if ltp <= 0:
                return None
            chg_raw = str(cur.get("PcChg") or "0").replace("+", "")
            quote = {
                "symbol": sym,
                "ltp": ltp,
                "change_pct": float(chg_raw) if chg_raw not in ("", "-") else 0.0,
                "prev_close": float(head.get("PrevClose") or 0) or None,
                "source": "bse_web",
                "delayed": False,
                "latency_note": "BSE website feed (~few seconds behind exchange)",
                "time": time.time(),
            }
            self._quote_cache[sym] = (now, quote)
            return quote
        except Exception as e:
            logger.warning(f"BSE quote failed for {sym}: {e}")
            return None

    def get_many(self, symbols) -> Dict[str, Dict]:
        out = {}
        for s in symbols:
            q = self.get_quote(s)
            if q:
                out[s.upper()] = q
        return out


bse_provider = BSEProvider()
