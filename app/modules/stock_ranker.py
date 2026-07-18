"""Stock ranker — screen the NIFTY-50 universe and pick the best candidates.

One batched yfinance download (1 request, ~50 symbols, daily bars), then a
pure multi-factor score per stock:

    structure trend (HH/HL vs LH/LL)     ±2
    ADX >= 25 in trend direction         ±1
    EMA stack (price vs 20/50/200)       ±1
    MACD histogram sign                  ±1
    RSI zone (>55 bull / <45 bear)       ±1
    1-month return sign                  ±1
    3-month return sign                  ±1
    near 52w high (+) / low (−)          ±1
    volume surge with the move           ±1

Liquidity gate: stocks below MIN_TURNOVER average daily traded value are
excluded — a signal you cannot exit is not a signal.

'Best' here means STRONGEST ALIGNED EVIDENCE for screening, not a trade
signal: the pipeline is screen → strategy-hunt on the top names →
deploy only what validates out-of-sample.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("elco.ranker")

# NIFTY 50 constituents (equity symbols, .NS suffix added at download).
NIFTY50 = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "BHARTIARTL", "ITC",
    "SBIN", "LT", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "BAJFINANCE", "ASIANPAINT",
    "MARUTI", "M&M", "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "TATAMOTORS",
    "NTPC", "POWERGRID", "TATASTEEL", "NESTLEIND", "WIPRO", "JSWSTEEL", "ADANIENT",
    "ADANIPORTS", "TECHM", "ONGC", "COALINDIA", "BAJAJFINSV", "HINDALCO", "GRASIM",
    "DRREDDY", "CIPLA", "EICHERMOT", "BRITANNIA", "DIVISLAB", "HEROMOTOCO",
    "APOLLOHOSP", "BAJAJ-AUTO", "TATACONSUM", "INDUSINDBK", "SBILIFE", "HDFCLIFE",
    "LTIM", "SHRIRAMFIN", "BPCL",
]

MIN_TURNOVER_CR = 5.0   # min avg daily traded value (₹ crore) — liquidity gate


def score_stock(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Pure scorer for one stock's daily OHLCV frame (oldest first).
    Returns {score, direction, factors, liquidity_cr} or None if unusable."""
    if df is None or len(df) < 220:
        return None
    close = df["close"]
    price = float(close.iloc[-1])
    factors: List[str] = []
    score = 0

    # Liquidity gate (avg 20d turnover in ₹ crore).
    turnover_cr = float((df["close"] * df["volume"]).tail(20).mean() / 1e7)
    if turnover_cr < MIN_TURNOVER_CR:
        return {"score": 0, "direction": "ILLIQUID", "factors": ["below liquidity gate"],
                "liquidity_cr": round(turnover_cr, 1)}

    # Structure trend.
    from .smc_analysis import detect_structure, adx as calc_adx
    trend = detect_structure(df.iloc[-160:].reset_index(drop=True)).get("trend")
    if trend == "BULLISH":
        score += 2; factors.append("+2 bullish structure (HH/HL)")
    elif trend == "BEARISH":
        score -= 2; factors.append("-2 bearish structure (LH/LL)")

    # ADX in trend direction.
    a = calc_adx(df.iloc[-120:].reset_index(drop=True))
    if a["adx"] >= 25 and trend in ("BULLISH", "BEARISH"):
        d = 1 if trend == "BULLISH" else -1
        score += d; factors.append(f"{'+1' if d > 0 else '-1'} ADX {a['adx']} strong trend")

    # EMA stack.
    from .indicators import calculate_ema, calculate_rsi
    e20 = float(calculate_ema(close, 20).iloc[-1])
    e50 = float(calculate_ema(close, 50).iloc[-1])
    e200 = float(calculate_ema(close, 200).iloc[-1])
    if price > e20 > e50 > e200:
        score += 1; factors.append("+1 perfect bullish EMA stack")
    elif price < e20 < e50 < e200:
        score -= 1; factors.append("-1 perfect bearish EMA stack")

    # MACD histogram.
    macd = calculate_ema(close, 12) - calculate_ema(close, 26)
    hist = float((macd - calculate_ema(macd, 9)).iloc[-1])
    score += 1 if hist > 0 else -1
    factors.append(f"{'+1' if hist > 0 else '-1'} MACD histogram {'positive' if hist > 0 else 'negative'}")

    # RSI zone.
    rsi = float(calculate_rsi(close, 14).iloc[-1])
    if rsi > 55:
        score += 1; factors.append(f"+1 RSI {rsi:.0f} bullish zone")
    elif rsi < 45:
        score -= 1; factors.append(f"-1 RSI {rsi:.0f} bearish zone")

    # Momentum: 1-month and 3-month returns.
    for bars, label in ((21, "1-month"), (63, "3-month")):
        if len(close) > bars:
            ret = price / float(close.iloc[-bars - 1]) - 1.0
            if abs(ret) > 0.005:
                d = 1 if ret > 0 else -1
                score += d
                factors.append(f"{'+1' if d > 0 else '-1'} {label} return {ret * 100:+.1f}%")

    # 52-week position.
    hi52 = float(df["high"].tail(252).max())
    lo52 = float(df["low"].tail(252).min())
    if price >= hi52 * 0.95:
        score += 1; factors.append("+1 within 5% of 52w high")
    elif price <= lo52 * 1.05:
        score -= 1; factors.append("-1 within 5% of 52w low")

    # Volume surge aligned with the latest move.
    v20 = float(df["volume"].tail(20).mean())
    if v20 > 0 and float(df["volume"].iloc[-1]) / v20 > 1.3:
        d = 1 if float(close.iloc[-1]) >= float(df["open"].iloc[-1]) else -1
        score += d
        factors.append(f"{'+1' if d > 0 else '-1'} volume surge with {'up' if d > 0 else 'down'} move")

    direction = "LONG" if score > 0 else "SHORT" if score < 0 else "NEUTRAL"
    return {"score": score, "direction": direction, "factors": factors,
            "liquidity_cr": round(turnover_cr, 1),
            "price": round(price, 2), "rsi": round(rsi, 1), "adx": a["adx"]}


def rank_universe(symbols: Optional[List[str]] = None, top_n: int = 10) -> Dict[str, Any]:
    """Batch-download the universe and rank by |score|. Real data only —
    symbols that fail to download are listed in 'skipped', never guessed."""
    import yfinance as yf

    symbols = [s.upper() for s in (symbols or NIFTY50)]
    tickers = [f"{s}.NS" for s in symbols]
    try:
        raw = yf.download(tickers, period="1y", interval="1d", progress=False,
                          auto_adjust=True, group_by="ticker", threads=True)
    except Exception as e:
        return {"error": f"batch download failed: {e}", "ranked": [], "skipped": symbols}

    ranked, skipped = [], []
    for sym, tk in zip(symbols, tickers):
        try:
            df = raw[tk] if isinstance(raw.columns, pd.MultiIndex) else raw
            df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
            df = df.reset_index(drop=True)
            s = score_stock(df)
            if s is None:
                skipped.append({"symbol": sym, "reason": "insufficient data"})
            elif s["direction"] == "ILLIQUID":
                skipped.append({"symbol": sym, "reason": f"liquidity {s['liquidity_cr']}cr < {MIN_TURNOVER_CR}cr"})
            else:
                ranked.append({"symbol": sym, **s})
        except Exception as e:
            skipped.append({"symbol": sym, "reason": str(e)[:60]})

    ranked.sort(key=lambda x: abs(x["score"]), reverse=True)
    return {
        "universe_size": len(symbols),
        "scored": len(ranked),
        "skipped": skipped,
        "best_long": [r for r in ranked if r["direction"] == "LONG"][:top_n],
        "best_short": [r for r in ranked if r["direction"] == "SHORT"][:top_n],
        "note": (
            "Screening by aligned evidence, not a trade signal. Pipeline: "
            "screen -> strategy-hunt the top names -> deploy only what "
            "validates out-of-sample -> auto-trader trades the validated book."
        ),
    }
