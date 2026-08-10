import time
import logging
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logger = logging.getLogger("elco.yf_cache")

_INFO_CACHE = {}
_CACHE_TTL = 900  # 15 minutes TTL

def get_cached_yf_info(symbol: str) -> dict:
    """Safely fetch and cache yfinance ticker.info to prevent 429 Too Many Requests."""
    clean_sym = symbol.upper().strip()
    if not clean_sym.endswith(".NS") and not clean_sym.endswith(".BO") and not clean_sym.startswith("^") and "=" not in clean_sym:
        clean_sym = f"{clean_sym}.NS"
        
    now = time.time()
    if clean_sym in _INFO_CACHE:
        data, ts = _INFO_CACHE[clean_sym]
        if now - ts < _CACHE_TTL:
            return data

    try:
        tk = yf.Ticker(clean_sym)
        info = tk.info
        if isinstance(info, dict) and len(info) > 0:
            _INFO_CACHE[clean_sym] = (info, now)
            return info
    except Exception as e:
        logger.warning(f"yfinance info fetch failed for {clean_sym}: {e}")

    # Return cached data if available even if expired, else empty dict
    if clean_sym in _INFO_CACHE:
        return _INFO_CACHE[clean_sym][0]
        
    return {}

_LTP_CACHE = {}
_LTP_CACHE_TTL = 3  # 3 seconds TTL for live price

def get_safe_ltp(symbol: str) -> float:
    """Safely retrieve last traded price without crashing on FastInfo object structure."""
    clean_sym = symbol.upper().strip()
    if not clean_sym.endswith(".NS") and not clean_sym.endswith(".BO") and not clean_sym.startswith("^") and "=" not in clean_sym:
        clean_sym = f"{clean_sym}.NS"

    now = time.time()
    if clean_sym in _LTP_CACHE:
        val, ts = _LTP_CACHE[clean_sym]
        if now - ts < _LTP_CACHE_TTL:
            return val

    try:
        tk = yf.Ticker(clean_sym)
        fi = tk.fast_info
        
        # Try attribute access first (FastInfo object in yfinance 0.2+)
        if hasattr(fi, "last_price") and getattr(fi, "last_price", None) is not None:
            val = float(fi.last_price)
            _LTP_CACHE[clean_sym] = (val, now)
            return val
        if hasattr(fi, "lastPrice") and getattr(fi, "lastPrice", None) is not None:
            val = float(fi.lastPrice)
            _LTP_CACHE[clean_sym] = (val, now)
            return val
            
        # Try dict-like get
        if hasattr(fi, "get"):
            val = fi.get("last_price") or fi.get("lastPrice")
            if val is not None:
                val = float(val)
                _LTP_CACHE[clean_sym] = (val, now)
                return val
                
        # Try subscript access
        if hasattr(fi, "__getitem__"):
            try:
                val = float(fi["last_price"])
                _LTP_CACHE[clean_sym] = (val, now)
                return val
            except Exception:
                val = float(fi["lastPrice"])
                _LTP_CACHE[clean_sym] = (val, now)
                return val
    except Exception:
        pass

    # Fallback to history 1d 1m bar
    try:
        tk = yf.Ticker(clean_sym)
        hist = tk.history(period="1d", interval="1m")
        if hist is not None and not hist.empty:
            val = float(hist["Close"].iloc[-1])
            _LTP_CACHE[clean_sym] = (val, now)
            return val
    except Exception:
        pass

    return 0.0


# --- Full quote cache (LTP + prev close + change% + volume) ----------------
_QUOTE_CACHE = {}
_QUOTE_CACHE_TTL = 5  # 5 seconds — slightly longer than LTP since we fetch more data

def get_safe_quote(symbol: str) -> dict:
    """Return {ltp, prev_close, change_pct, volume} from yfinance.
    Uses fast_info for LTP and previous_close, falls back to history."""
    clean_sym = symbol.upper().strip()
    if not clean_sym.endswith(".NS") and not clean_sym.endswith(".BO") and not clean_sym.startswith("^") and "=" not in clean_sym:
        clean_sym = f"{clean_sym}.NS"

    now = time.time()
    if clean_sym in _QUOTE_CACHE:
        cached, ts = _QUOTE_CACHE[clean_sym]
        if now - ts < _QUOTE_CACHE_TTL:
            return cached

    result = {"ltp": 0.0, "prev_close": 0.0, "change_pct": 0.0, "volume": 0}

    try:
        tk = yf.Ticker(clean_sym)
        fi = tk.fast_info

        # Extract LTP
        ltp = 0.0
        for attr in ("last_price", "lastPrice"):
            v = getattr(fi, attr, None)
            if v is not None and v > 0:
                ltp = float(v)
                break
        if ltp <= 0:
            # dict-style fallback
            if hasattr(fi, "get"):
                v = fi.get("last_price") or fi.get("lastPrice")
                if v:
                    ltp = float(v)

        # Extract previous close
        prev = 0.0
        for attr in ("previous_close", "previousClose", "regularMarketPreviousClose"):
            v = getattr(fi, attr, None)
            if v is not None and v > 0:
                prev = float(v)
                break
        if prev <= 0 and hasattr(fi, "get"):
            v = fi.get("previous_close") or fi.get("previousClose") or fi.get("regularMarketPreviousClose")
            if v:
                prev = float(v)

        # Extract volume
        vol = 0
        for attr in ("last_volume", "lastVolume", "regularMarketVolume"):
            v = getattr(fi, attr, None)
            if v is not None and v > 0:
                vol = int(v)
                break

        if ltp > 0:
            result["ltp"] = ltp
            result["prev_close"] = prev
            result["volume"] = vol
            if prev > 0:
                result["change_pct"] = round(100.0 * (ltp - prev) / prev, 2)
            _QUOTE_CACHE[clean_sym] = (result, now)
            # Also update LTP cache
            _LTP_CACHE[clean_sym] = (ltp, now)
            return result
    except Exception as e:
        logger.warning(f"get_safe_quote fast_info failed for {clean_sym}: {e}")

    # Fallback: 2-day history
    try:
        tk = yf.Ticker(clean_sym)
        hist = tk.history(period="5d", interval="1d")
        if hist is not None and len(hist) >= 2:
            ltp = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            vol = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
            result["ltp"] = ltp
            result["prev_close"] = prev
            result["volume"] = vol
            if prev > 0:
                result["change_pct"] = round(100.0 * (ltp - prev) / prev, 2)
            _QUOTE_CACHE[clean_sym] = (result, now)
            _LTP_CACHE[clean_sym] = (ltp, now)
            return result
    except Exception:
        pass

    # Last resort: use LTP cache
    ltp = get_safe_ltp(symbol)
    if ltp > 0:
        result["ltp"] = ltp
    return result
