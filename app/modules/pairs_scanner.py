"""Pairs / statistical-arbitrage scanner — retail-feasible arbitrage, honestly.

Finds highly-correlated NSE pairs and flags spread dislocations:
  spread_t = A_t − β·B_t   (β = rolling hedge ratio, cov/var)
  z = (spread − mean_60d) / std_60d
|z| ≥ Z_ENTRY means the pair is stretched: classic stat-arb would LONG the
cheap leg and SHORT the rich leg, betting the spread mean-reverts.

HONESTY: signals only, no auto-execution — shorting cash equity overnight
isn't possible in India (needs futures/intraday), and pair convergence can
take days. Use as study signals / intraday context, not a money machine.
"""
from __future__ import annotations

import logging
from itertools import combinations
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("elco.pairs")

MIN_CORR = 0.60   # daily-return corr; same-sector pairs rarely exceed ~0.75
Z_WINDOW = 60
Z_ENTRY = 2.0

# Sector buckets — economically-related pairs only (random correlation is
# how stat-arb blows up).
PAIR_UNIVERSE = {
    "banks": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN", "INDUSINDBK"],
    "it": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
    "energy": ["RELIANCE", "ONGC", "BPCL"],
    "pharma": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB"],
    "auto": ["MARUTI", "M&M", "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO"],
    "metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO"],
}


def _closes(symbols: List[str], period: str = "1y") -> Optional[pd.DataFrame]:
    import yfinance as yf
    try:
        raw = yf.download([f"{s}.NS" for s in symbols], period=period, interval="1d",
                          progress=False, auto_adjust=True, group_by="ticker", threads=True)
    except Exception as e:
        logger.warning(f"Pairs download failed: {e}")
        return None
    closes = {}
    for s in symbols:
        try:
            df = raw[f"{s}.NS"] if isinstance(raw.columns, pd.MultiIndex) else raw
            c = df["Close"].dropna()
            if len(c) > Z_WINDOW + 30:
                closes[s] = c
        except Exception:
            continue
    if len(closes) < 2:
        return None
    return pd.DataFrame(closes).dropna()


def analyze_pair(a: pd.Series, b: pd.Series) -> Dict[str, Any]:
    """Correlation, hedge beta, and current spread z-score for one pair."""
    ra, rb = a.pct_change().dropna(), b.pct_change().dropna()
    corr = float(ra.corr(rb))
    beta = float(ra.cov(rb) / rb.var()) if rb.var() > 0 else 1.0
    spread = a - beta * b
    win = spread.tail(Z_WINDOW)
    std = float(win.std())
    z = float((spread.iloc[-1] - win.mean()) / std) if std > 0 else 0.0
    return {"correlation": round(corr, 3), "hedge_beta": round(beta, 3),
            "z_score": round(z, 2)}


def scan_pairs(sectors: Optional[List[str]] = None) -> Dict[str, Any]:
    """Scan sector buckets for correlated pairs and current dislocations."""
    buckets = {k: v for k, v in PAIR_UNIVERSE.items()
               if not sectors or k in sectors}
    signals, watched, failed = [], [], []

    for sector, syms in buckets.items():
        prices = _closes(syms)
        if prices is None:
            failed.append(sector)
            continue
        for a, b in combinations(prices.columns, 2):
            st = analyze_pair(prices[a], prices[b])
            if st["correlation"] < MIN_CORR:
                continue
            row = {"sector": sector, "pair": f"{a}/{b}", **st}
            if abs(st["z_score"]) >= Z_ENTRY:
                rich, cheap = (a, b) if st["z_score"] > 0 else (b, a)
                row["signal"] = f"spread stretched: {rich} rich vs {cheap} — "
                row["signal"] += f"classic stat-arb: LONG {cheap} / SHORT {rich}"
                signals.append(row)
            else:
                watched.append(row)

    watched.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return {
        "signals": signals,
        "watched_pairs": watched[:15],
        "sectors_failed": failed,
        "params": {"min_correlation": MIN_CORR, "z_window_days": Z_WINDOW,
                   "z_entry": Z_ENTRY},
        "note": (
            "SIGNALS ONLY — not auto-traded. Overnight shorting of cash equity "
            "isn't possible in India (futures needed), and convergence can take "
            "days. Real daily closes, rolling hedge beta, 60d z-score."
        ),
    }
