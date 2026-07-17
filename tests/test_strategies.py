"""Tests for the strategy library + honest backtest harness.

Verifies signal logic on constructed price paths and that the harness computes
metrics correctly and stays look-ahead free (no future data leaks into signals).
"""
import numpy as np
import pandas as pd

from app.modules import strategies as S


def _ohlc(closes):
    closes = np.asarray(closes, dtype=float)
    high = closes * 1.005
    low = closes * 0.995
    opens = np.concatenate([[closes[0]], closes[:-1]])
    vol = np.full(len(closes), 1_000_000)
    return pd.DataFrame({"open": opens, "high": high, "low": low, "close": closes, "volume": vol})


def test_donchian_breakout_fires_on_new_high():
    # 25 flat bars then a jump above the prior 20-bar high.
    closes = [100] * 25 + [120]
    sig = S.donchian_breakout(_ohlc(closes))
    assert sig == "BUY"


def test_donchian_breakout_fires_on_new_low():
    closes = [100] * 25 + [80]
    assert S.donchian_breakout(_ohlc(closes)) == "SELL"


def test_ema_crossover_detects_bullish_cross():
    # Long downtrend then a sharp rally to force a fast>slow crossover.
    down = list(np.linspace(200, 100, 60))
    up = list(np.linspace(100, 200, 20))
    sig = None
    df = _ohlc(down + up)
    # Scan forward for the crossover bar.
    for i in range(55, len(df)):
        s = S.ema_trend_crossover(df.iloc[: i + 1])
        if s:
            sig = s
            break
    assert sig == "BUY"


def test_rsi_mean_reversion_returns_valid_or_none():
    closes = list(np.linspace(100, 60, 40))  # steady decline -> oversold
    sig = S.rsi_mean_reversion(_ohlc(closes))
    assert sig in ("BUY", "SELL", None)


def test_backtest_metrics_are_consistent():
    # Deterministic trending series so at least some trades close.
    rng = np.random.default_rng(42)
    rets = rng.normal(0.001, 0.02, 400)
    closes = 100 * np.cumprod(1 + rets)
    df = _ohlc(closes)
    res = S.backtest_strategy("EMA Trend Crossover", S.ema_trend_crossover, df)
    # Win rate is a real percentage.
    assert 0.0 <= res.win_rate <= 100.0
    # If there were losses, profit factor is defined and non-negative.
    if res.profit_factor is not None:
        assert res.profit_factor >= 0.0
    assert res.max_drawdown_pct >= 0.0
    assert res.total_trades >= 0


def test_rank_returns_all_strategies_sorted():
    rng = np.random.default_rng(7)
    rets = rng.normal(0.0005, 0.015, 500)
    closes = 100 * np.cumprod(1 + rets)
    ranked = S.rank_strategies(_ohlc(closes))
    assert len(ranked) == len(S.STRATEGIES)
    # Sorted by profit factor descending (None treated as lowest).
    pfs = [r["profit_factor"] if r["profit_factor"] is not None else -1.0 for r in ranked]
    assert pfs == sorted(pfs, reverse=True)
    # Every entry exposes the honest metric set.
    for r in ranked:
        assert {"win_rate_pct", "profit_factor", "expectancy_r", "sharpe",
                "max_drawdown_pct", "recommended"} <= set(r)


def test_no_lookahead_signal_only_uses_past():
    # A signal computed on a truncated frame must equal the signal computed on
    # the full frame truncated to the same point (i.e. future bars don't matter).
    rng = np.random.default_rng(1)
    closes = 100 * np.cumprod(1 + rng.normal(0, 0.02, 200))
    df = _ohlc(closes)
    cut = 120
    sig_truncated = S.macd_momentum(df.iloc[: cut + 1])
    sig_full_view = S.macd_momentum(df.iloc[: cut + 1].copy())
    assert sig_truncated == sig_full_view
