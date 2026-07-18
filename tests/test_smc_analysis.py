"""Tests for market-structure / SMC analysis on synthetic OHLCV."""
import numpy as np
import pandas as pd

from app.modules import smc_analysis as S


def _ohlc_from_closes(closes, wick=0.3):
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    high = np.maximum(opens, closes) + wick
    low = np.minimum(opens, closes) - wick
    vol = np.full(len(closes), 1_000_000)
    return pd.DataFrame({"open": opens, "high": high, "low": low,
                         "close": closes, "volume": vol})


def _uptrend(n=120):
    # Amplitude must beat the slope so real pullbacks (swing points) form.
    x = np.arange(n, dtype=float)
    return _ohlc_from_closes(100 + x * 0.8 + 10 * np.sin(x / 5))


def _downtrend(n=120):
    x = np.arange(n, dtype=float)
    return _ohlc_from_closes(200 - x * 0.8 + 10 * np.sin(x / 5))


def test_swings_found_and_labeled():
    swings = S.label_structure(S.find_swings(_uptrend()))
    assert len(swings) >= 4
    labels = [s["label"] for s in swings if s["label"]]
    # An uptrend should be dominated by HH/HL labels.
    assert labels.count("HH") + labels.count("HL") > labels.count("LH") + labels.count("LL")


def test_structure_trend_detection():
    assert S.detect_structure(_uptrend())["trend"] == "BULLISH"
    assert S.detect_structure(_downtrend())["trend"] == "BEARISH"


def test_bos_fires_on_breakout():
    df = _uptrend()
    # Force the last close far above every prior swing high -> bullish BOS.
    df.loc[df.index[-1], "close"] = float(df["high"].max()) + 10
    df.loc[df.index[-1], "high"] = float(df["high"].max()) + 11
    s = S.detect_structure(df)
    assert s["bos"] is not None and s["bos"]["direction"] == "BULLISH"


def test_support_resistance_zones_sorted_by_distance():
    zones = S.support_resistance_zones(_uptrend(200))
    assert zones, "expected at least one zone"
    dists = [abs(z["distance_pct"]) for z in zones]
    assert dists == sorted(dists)
    for z in zones:
        assert z["kind"] in ("SUPPORT", "RESISTANCE")


def test_fvg_detection_on_constructed_gap():
    closes = [100.0] * 30
    df = _ohlc_from_closes(closes, wick=0.1)
    # Construct a clean bullish FVG at the end: candle1 high < candle3 low.
    df.loc[df.index[-3], ["open", "close", "high", "low"]] = [100, 100, 100.2, 99.8]
    df.loc[df.index[-2], ["open", "close", "high", "low"]] = [100, 104, 104.5, 100]
    df.loc[df.index[-1], ["open", "close", "high", "low"]] = [104, 105, 105.5, 103.5]
    gaps = S.fair_value_gaps(df)
    assert any(g["kind"] == "BULLISH" for g in gaps)


def test_liquidity_sweep_detection():
    closes = list(100 + 5 * np.sin(np.arange(60) / 4.0))
    df = _ohlc_from_closes(closes, wick=0.2)
    # Sweep: wick far below the range low, but close back inside.
    lo = float(df["low"].min())
    df.loc[df.index[-1], "low"] = lo - 3
    df.loc[df.index[-1], "close"] = 101
    df.loc[df.index[-1], "open"] = 100
    sweeps = S.liquidity_sweeps(df)
    assert any(s["kind"] == "SELL_SIDE_SWEEP" for s in sweeps)


def test_premium_discount_zones():
    pd_zone = S.premium_discount(_uptrend())
    assert pd_zone.get("zone") != "UNDEFINED"
    assert 0 <= pd_zone["position"] <= 1.5  # position may exceed 1 slightly on breakout


def test_adx_strong_in_trend_weak_in_chop():
    strong = S.adx(_ohlc_from_closes(100 + np.arange(100) * 1.5))["adx"]
    rng = np.random.default_rng(4)
    chop = S.adx(_ohlc_from_closes(100 + rng.normal(0, 0.3, 100).cumsum() * 0.1))["adx"]
    assert strong > chop


def test_camarilla_ordering():
    cam = S.camarilla_pivots(_uptrend())
    assert cam["r4"] > cam["r1"] > cam["s1"] > cam["s4"]


def test_smc_report_shape_and_honesty():
    r = S.smc_report(_uptrend(150))
    for key in ("market_structure", "support_resistance", "fair_value_gaps",
                "order_blocks", "liquidity_sweeps", "premium_discount",
                "fibonacci", "camarilla_pivots", "adx", "not_available"):
        assert key in r
    assert "tick" in r["not_available"]  # honest about order-flow limits
