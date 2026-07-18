"""Offline tests for the stock ranker's pure scoring function."""
import numpy as np
import pandas as pd

from app.modules.stock_ranker import score_stock, MIN_TURNOVER_CR, NIFTY50


def _frame(closes, volume=2_000_000):
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    return pd.DataFrame({
        "open": opens,
        "high": np.maximum(opens, closes) * 1.004,
        "low": np.minimum(opens, closes) * 0.996,
        "close": closes,
        "volume": np.full(len(closes), volume),
    })


def _uptrend(n=300):
    x = np.arange(n, dtype=float)
    return _frame(100 + x * 0.5 + 8 * np.sin(x / 6))


def _downtrend(n=300):
    x = np.arange(n, dtype=float)
    return _frame(300 - x * 0.5 + 8 * np.sin(x / 6))


def test_uptrend_scores_long():
    s = score_stock(_uptrend())
    assert s["direction"] == "LONG"
    assert s["score"] >= 4
    assert any("structure" in f for f in s["factors"])


def test_downtrend_scores_short():
    s = score_stock(_downtrend())
    assert s["direction"] == "SHORT"
    assert s["score"] <= -4


def test_illiquid_stock_is_gated():
    # Tiny volume -> turnover below the gate -> excluded, score irrelevant.
    s = score_stock(_frame(100 + np.arange(300) * 0.5, volume=100))
    assert s["direction"] == "ILLIQUID"


def test_insufficient_data_returns_none():
    assert score_stock(_uptrend(100)) is None


def test_universe_list_sane():
    assert len(NIFTY50) == 50
    assert len(set(NIFTY50)) == 50  # no duplicates
    assert MIN_TURNOVER_CR > 0
