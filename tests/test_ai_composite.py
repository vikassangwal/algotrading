"""Tests for the AI composite engine — signals must be real & deterministic."""
import numpy as np
import pandas as pd

from app.modules.ai_composite_engine import AICompositeEngine


def _series(start, end, n=250, vol_start=1000, vol_end=3000):
    close = pd.Series(np.linspace(start, end, n))
    return pd.DataFrame({
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.linspace(vol_start, vol_end, n),
    })


def test_uptrend_is_bullish():
    r = AICompositeEngine(_series(100, 200)).calculate_scores()
    assert r["action"] in ("Buy", "Strong Buy")
    assert r["probability_pct"] > 50


def test_downtrend_is_bearish():
    r = AICompositeEngine(_series(200, 100, vol_start=3000, vol_end=1000)).calculate_scores()
    assert r["action"] in ("Sell", "Strong Sell")
    assert r["probability_pct"] < 50


def test_deterministic():
    df = _series(100, 200)
    a = AICompositeEngine(df.copy()).calculate_scores()
    b = AICompositeEngine(df.copy()).calculate_scores()
    assert a == b  # NO randomness — same input, same output


def test_insufficient_data_defaults_to_hold():
    tiny = _series(100, 110, n=5)
    r = AICompositeEngine(tiny).calculate_scores()
    assert r["action"] == "Hold"


def test_trade_setup_has_valid_levels():
    r = AICompositeEngine(_series(100, 200)).calculate_scores()
    s = r["trade_setup"]
    # For a long, stop-loss below entry, target above
    assert s["stop_loss"] < s["entry"] < s["target_1"]
