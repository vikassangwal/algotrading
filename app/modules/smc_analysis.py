"""Market Structure + Smart Money Concepts from real OHLCV data.

Implements the parts of the institutional-TA roadmap that daily/intraday
candles can honestly support:

  * Swing highs/lows (fractal pivots) -> HH / HL / LH / LL labeling
  * Structure trend + Break of Structure (BOS) + Change of Character (CHOCH)
  * Support/Resistance zones (clustered swing levels, touch-counted)
  * Fair Value Gaps (3-candle imbalance), unfilled ones tracked
  * Order Blocks (last opposite candle before an impulsive displacement)
  * Liquidity sweeps / stop hunts (wick beyond a prior swing, close back inside)
  * Premium/Discount zone of the current dealing range
  * Fibonacci retracement of the last major swing
  * Classic + Camarilla pivots, ADX trend strength

NOT implemented on purpose (needs tick/order-flow data we don't have):
footprint charts, DOM, time & sales, delta/cumulative delta, iceberg
detection. Pretending to derive those from OHLCV would be fake analysis.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger("elco.smc")

SWING_LOOKBACK = 3          # fractal: bar higher/lower than N on both sides
ZONE_TOLERANCE_PCT = 0.6    # cluster levels within 0.6% into one S/R zone
IMPULSE_ATR_MULT = 1.5      # displacement candle = body >= 1.5x ATR
FVG_MIN_PCT = 0.15          # ignore FVGs thinner than 0.15% of price


# --- Swings and structure ----------------------------------------------------

def find_swings(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> List[Dict]:
    """Fractal swing points: index, price, kind ('high'|'low'). Chronological."""
    highs, lows = df["high"].values, df["low"].values
    n = len(df)
    swings: List[Dict] = []
    for i in range(lookback, n - lookback):
        win_h = highs[i - lookback: i + lookback + 1]
        win_l = lows[i - lookback: i + lookback + 1]
        if highs[i] == win_h.max() and (win_h.argmax() == lookback):
            swings.append({"index": i, "price": float(highs[i]), "kind": "high"})
        elif lows[i] == win_l.min() and (win_l.argmin() == lookback):
            swings.append({"index": i, "price": float(lows[i]), "kind": "low"})
    return swings


def label_structure(swings: List[Dict]) -> List[Dict]:
    """Label each swing HH/LH (highs) or HL/LL (lows) vs the previous same-kind swing."""
    last_high = last_low = None
    labeled = []
    for s in swings:
        s = dict(s)
        if s["kind"] == "high":
            s["label"] = None if last_high is None else ("HH" if s["price"] > last_high else "LH")
            last_high = s["price"]
        else:
            s["label"] = None if last_low is None else ("HL" if s["price"] > last_low else "LL")
            last_low = s["price"]
        labeled.append(s)
    return labeled


def detect_structure(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> Dict[str, Any]:
    """Trend from recent swing labels + BOS/CHOCH off the latest close."""
    swings = label_structure(find_swings(df, lookback=lookback))
    if len(swings) < 4:
        return {"trend": "UNDEFINED", "swings": [], "bos": None, "choch": None,
                "note": "Not enough swings to define structure."}

    recent = [s["label"] for s in swings[-6:] if s["label"]]
    bulls = sum(1 for x in recent if x in ("HH", "HL"))
    bears = sum(1 for x in recent if x in ("LH", "LL"))
    trend = "BULLISH" if bulls > bears else "BEARISH" if bears > bulls else "SIDEWAYS"

    close = float(df["close"].iloc[-1])
    last_swing_high = next((s for s in reversed(swings) if s["kind"] == "high"), None)
    last_swing_low = next((s for s in reversed(swings) if s["kind"] == "low"), None)

    bos = choch = None
    if last_swing_high and close > last_swing_high["price"]:
        if trend == "BULLISH":
            bos = {"direction": "BULLISH", "broken_level": last_swing_high["price"],
                   "meaning": "Continuation: prior swing high broken with trend."}
        else:
            choch = {"direction": "BULLISH", "broken_level": last_swing_high["price"],
                     "meaning": "Change of Character: bearish structure violated upward."}
    elif last_swing_low and close < last_swing_low["price"]:
        if trend == "BEARISH":
            bos = {"direction": "BEARISH", "broken_level": last_swing_low["price"],
                   "meaning": "Continuation: prior swing low broken with trend."}
        else:
            choch = {"direction": "BEARISH", "broken_level": last_swing_low["price"],
                     "meaning": "Change of Character: bullish structure violated downward."}

    return {
        "trend": trend,
        "recent_labels": recent,
        "last_swing_high": last_swing_high["price"] if last_swing_high else None,
        "last_swing_low": last_swing_low["price"] if last_swing_low else None,
        "bos": bos,
        "choch": choch,
        "swings": swings[-10:],
    }


# --- Support / Resistance zones ---------------------------------------------

def support_resistance_zones(df: pd.DataFrame, max_zones: int = 6) -> List[Dict]:
    """Cluster swing levels within tolerance; rank by touches. Real levels only."""
    swings = find_swings(df)
    if not swings:
        return []
    price = float(df["close"].iloc[-1])
    levels = sorted(s["price"] for s in swings)
    zones: List[List[float]] = []
    for lv in levels:
        if zones and abs(lv - np.mean(zones[-1])) / price * 100 <= ZONE_TOLERANCE_PCT:
            zones[-1].append(lv)
        else:
            zones.append([lv])
    ranked = sorted(zones, key=len, reverse=True)[:max_zones]
    out = []
    for z in ranked:
        center = float(np.mean(z))
        out.append({
            "level": round(center, 2),
            "touches": len(z),
            "kind": "SUPPORT" if center < price else "RESISTANCE",
            "distance_pct": round(100.0 * (center - price) / price, 2),
        })
    return sorted(out, key=lambda x: abs(x["distance_pct"]))


# --- Fair Value Gaps ---------------------------------------------------------

def fair_value_gaps(df: pd.DataFrame, max_gaps: int = 5) -> List[Dict]:
    """3-candle imbalances still unfilled by later price. Bullish FVG:
    candle1.high < candle3.low. Bearish FVG: candle1.low > candle3.high."""
    price = float(df["close"].iloc[-1])
    gaps: List[Dict] = []
    highs, lows = df["high"].values, df["low"].values
    n = len(df)
    for i in range(2, n):
        lo1, hi1 = lows[i - 2], highs[i - 2]
        lo3, hi3 = lows[i], highs[i]
        if hi1 < lo3 and (lo3 - hi1) / price * 100 >= FVG_MIN_PCT:
            top, bottom, kind = lo3, hi1, "BULLISH"
        elif lo1 > hi3 and (lo1 - hi3) / price * 100 >= FVG_MIN_PCT:
            top, bottom, kind = lo1, hi3, "BEARISH"
        else:
            continue
        filled = bool((lows[i + 1:] <= bottom).any()) if kind == "BULLISH" and i + 1 < n else \
                 bool((highs[i + 1:] >= top).any()) if kind == "BEARISH" and i + 1 < n else False
        if not filled:
            gaps.append({
                "kind": kind, "top": round(float(top), 2), "bottom": round(float(bottom), 2),
                "bars_ago": n - 1 - i,
                "size_pct": round(abs(top - bottom) / price * 100, 2),
            })
    return gaps[-max_gaps:]


# --- Order Blocks ------------------------------------------------------------

def order_blocks(df: pd.DataFrame, max_blocks: int = 4) -> List[Dict]:
    """Last opposite-color candle before an impulsive displacement (body >=
    IMPULSE_ATR_MULT * ATR). The candle's range is the block zone."""
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    atr = pd.Series(tr).rolling(14).mean().values
    price = float(c[-1])
    blocks: List[Dict] = []
    n = len(df)
    for i in range(15, n - 1):
        body = abs(c[i] - o[i])
        a = atr[i - 1]
        if not np.isfinite(a) or a <= 0 or body < IMPULSE_ATR_MULT * a:
            continue
        j = i - 1
        if c[i] > o[i] and c[j] < o[j]:        # bullish impulse after down candle
            kind, top, bottom = "BULLISH", h[j], l[j]
        elif c[i] < o[i] and c[j] > o[j]:      # bearish impulse after up candle
            kind, top, bottom = "BEARISH", h[j], l[j]
        else:
            continue
        # Unmitigated = price hasn't traded back through the block since.
        later_lows, later_highs = l[i + 1:], h[i + 1:]
        mitigated = bool((later_lows <= bottom).any()) if kind == "BULLISH" else \
                    bool((later_highs >= top).any())
        if not mitigated:
            blocks.append({
                "kind": kind, "top": round(float(top), 2), "bottom": round(float(bottom), 2),
                "bars_ago": n - 1 - i,
                "distance_pct": round(100.0 * ((top + bottom) / 2 - price) / price, 2),
            })
    return blocks[-max_blocks:]


# --- Liquidity sweeps --------------------------------------------------------

def liquidity_sweeps(df: pd.DataFrame, recent_bars: int = 10) -> List[Dict]:
    """Stop hunt: wick pierces a prior swing level but the bar CLOSES back
    inside. Classic liquidity grab before reversal."""
    swings = find_swings(df.iloc[:-1])  # levels known before the sweep bar
    n = len(df)
    out: List[Dict] = []
    for i in range(max(SWING_LOOKBACK * 2, n - recent_bars), n):
        bar_h, bar_l, bar_c = (float(df[k].iloc[i]) for k in ("high", "low", "close"))
        for s in swings:
            if s["index"] >= i - 1:
                continue
            if s["kind"] == "high" and bar_h > s["price"] and bar_c < s["price"]:
                out.append({"kind": "BUY_SIDE_SWEEP", "swept_level": round(s["price"], 2),
                            "bars_ago": n - 1 - i,
                            "meaning": "Wick above prior high, closed back below — possible stop hunt."})
                break
            if s["kind"] == "low" and bar_l < s["price"] and bar_c > s["price"]:
                out.append({"kind": "SELL_SIDE_SWEEP", "swept_level": round(s["price"], 2),
                            "bars_ago": n - 1 - i,
                            "meaning": "Wick below prior low, closed back above — possible stop hunt."})
                break
    return out[-5:]


# --- Premium / Discount, Fibonacci, pivots, ADX ------------------------------

def premium_discount(df: pd.DataFrame) -> Dict[str, Any]:
    """Position within the current dealing range (last major swing pair)."""
    structure = detect_structure(df)
    hi, lo = structure.get("last_swing_high"), structure.get("last_swing_low")
    if not hi or not lo or hi <= lo:
        return {"zone": "UNDEFINED"}
    price = float(df["close"].iloc[-1])
    pos = (price - lo) / (hi - lo)
    return {
        "range_high": round(hi, 2), "range_low": round(lo, 2),
        "equilibrium": round((hi + lo) / 2, 2),
        "position": round(pos, 2),
        "zone": "PREMIUM (sell-favored)" if pos > 0.62 else
                "DISCOUNT (buy-favored)" if pos < 0.38 else "EQUILIBRIUM",
    }


def fibonacci_levels(df: pd.DataFrame) -> Dict[str, Any]:
    """Retracement of the last major swing (structure-derived, not arbitrary)."""
    structure = detect_structure(df)
    hi, lo = structure.get("last_swing_high"), structure.get("last_swing_low")
    if not hi or not lo or hi <= lo:
        return {}
    diff = hi - lo
    return {
        "swing_high": round(hi, 2), "swing_low": round(lo, 2),
        "levels": {
            "0.236": round(hi - 0.236 * diff, 2),
            "0.382": round(hi - 0.382 * diff, 2),
            "0.5": round(hi - 0.5 * diff, 2),
            "0.618": round(hi - 0.618 * diff, 2),
            "0.786": round(hi - 0.786 * diff, 2),
        },
        "extension_1.272": round(hi + 0.272 * diff, 2),
        "extension_1.618": round(hi + 0.618 * diff, 2),
    }


def camarilla_pivots(df: pd.DataFrame) -> Dict[str, float]:
    h, l, c = (float(df[k].iloc[-1]) for k in ("high", "low", "close"))
    rng = h - l
    return {
        "r4": round(c + rng * 1.1 / 2, 2), "r3": round(c + rng * 1.1 / 4, 2),
        "r2": round(c + rng * 1.1 / 6, 2), "r1": round(c + rng * 1.1 / 12, 2),
        "s1": round(c - rng * 1.1 / 12, 2), "s2": round(c - rng * 1.1 / 6, 2),
        "s3": round(c - rng * 1.1 / 4, 2), "s4": round(c - rng * 1.1 / 2, 2),
    }


def adx(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
    """Wilder's ADX — trend strength (>25 trending, <20 choppy)."""
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    val = float(dx.ewm(alpha=1 / period, adjust=False).mean().iloc[-1])
    return {
        "adx": round(val, 1),
        "plus_di": round(float(plus_di.iloc[-1]), 1),
        "minus_di": round(float(minus_di.iloc[-1]), 1),
        "reading": "STRONG TREND" if val >= 25 else "WEAK/NO TREND" if val < 20 else "DEVELOPING",
    }


# --- Aggregate ---------------------------------------------------------------

def smc_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Everything above in one dict + an honest note about what's NOT here."""
    return {
        "market_structure": detect_structure(df),
        "support_resistance": support_resistance_zones(df),
        "fair_value_gaps": fair_value_gaps(df),
        "order_blocks": order_blocks(df),
        "liquidity_sweeps": liquidity_sweeps(df),
        "premium_discount": premium_discount(df),
        "fibonacci": fibonacci_levels(df),
        "camarilla_pivots": camarilla_pivots(df),
        "adx": adx(df),
        "not_available": (
            "Footprint/DOM/time-and-sales/delta/iceberg detection need "
            "tick-by-tick order-flow data (not derivable from OHLCV) — "
            "shown as unavailable instead of fabricated."
        ),
    }
