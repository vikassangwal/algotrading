import time
import logging
import yfinance as yf

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

def get_safe_ltp(symbol: str) -> float:
    """Safely retrieve last traded price without crashing on FastInfo object structure."""
    clean_sym = symbol.upper().strip()
    if not clean_sym.endswith(".NS") and not clean_sym.endswith(".BO") and not clean_sym.startswith("^") and "=" not in clean_sym:
        clean_sym = f"{clean_sym}.NS"

    try:
        tk = yf.Ticker(clean_sym)
        fi = tk.fast_info
        
        # Try attribute access first (FastInfo object in yfinance 0.2+)
        if hasattr(fi, "last_price") and getattr(fi, "last_price", None) is not None:
            return float(fi.last_price)
        if hasattr(fi, "lastPrice") and getattr(fi, "lastPrice", None) is not None:
            return float(fi.lastPrice)
            
        # Try dict-like get
        if hasattr(fi, "get"):
            val = fi.get("last_price") or fi.get("lastPrice")
            if val is not None:
                return float(val)
                
        # Try subscript access
        if hasattr(fi, "__getitem__"):
            try:
                return float(fi["last_price"])
            except Exception:
                return float(fi["lastPrice"])
    except Exception:
        pass

    # Fallback to history 1d 1m bar
    try:
        tk = yf.Ticker(clean_sym)
        hist = tk.history(period="1d", interval="1m")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass

    return 0.0
