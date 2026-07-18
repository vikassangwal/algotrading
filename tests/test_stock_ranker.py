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


def test_full_market_universe_uses_bhavcopy(monkeypatch):
    from app.modules import stock_ranker as SR
    from app.data import nse_provider as NP

    fake_table = {
        "BIGCO": {"close": 500.0, "turnover": 50e7, "delivery_percentage": 50.0},
        "MIDCO": {"close": 100.0, "turnover": 6e7, "delivery_percentage": 40.0},
        "TINYCO": {"close": 10.0, "turnover": 0.2e7, "delivery_percentage": 30.0},
        "NOTURN": {"close": 10.0, "delivery_percentage": 30.0},  # no turnover key
    }
    monkeypatch.setattr(NP.nse_provider, "_cached", lambda key, fn: fake_table)

    u = SR.full_market_universe(min_turnover_cr=5.0, max_symbols=10)
    assert u["nse_total_symbols"] == 4
    assert u["liquid_universe"] == ["BIGCO", "MIDCO"]  # sorted by turnover
    assert u["liquid_count"] == 2  # TINYCO/NOTURN gated out


def test_market_scan_reports_error_without_universe(monkeypatch):
    from app.modules import stock_ranker as SR
    from app.data import nse_provider as NP
    monkeypatch.setattr(NP.nse_provider, "_cached", lambda key, fn: None)
    r = SR.market_scan()
    assert "error" in r
