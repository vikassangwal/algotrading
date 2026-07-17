"""Tests for the auto strategy generator — split correctness + honest labeling."""
import numpy as np
import pandas as pd
import pytest

from app.modules import strategy_generator as G


def _ohlc(closes):
    closes = np.asarray(closes, dtype=float)
    high = closes * 1.005
    low = closes * 0.995
    opens = np.concatenate([[closes[0]], closes[:-1]])
    vol = np.full(len(closes), 1_000_000)
    return pd.DataFrame({"open": opens, "high": high, "low": low, "close": closes, "volume": vol})


def _random_walk(n=800, seed=3):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0004, 0.015, n)
    return _ohlc(100 * np.cumprod(1 + rets))


def test_build_variants_all_have_name_fn_params():
    variants = G.build_variants()
    assert len(variants) >= 20
    for name, fn, params in variants:
        assert isinstance(name, str) and name
        assert callable(fn)
        assert "template" in params


def test_variant_cap_respected():
    assert len(G.build_variants(max_variants=5)) == 5


def test_generate_requires_enough_bars():
    with pytest.raises(ValueError):
        G.generate_strategies(_random_walk(n=200))


def test_split_fractions():
    df = _random_walk(n=1000)
    r = G.generate_strategies(df, top_n=3)
    assert r["bars_train"] == 700
    assert r["bars_test"] == 300
    assert r["bars_total"] == 1000


def test_validated_entries_meet_test_gate():
    df = _random_walk(n=1000, seed=7)
    r = G.generate_strategies(df, top_n=5)
    for v in r["validated"]:
        assert v["status"] == "VALIDATED"
        assert v["test"]["trades"] >= G.MIN_TRADES_TEST
        assert v["test"]["expectancy_r"] > 0
        pf = v["test"]["profit_factor"]
        assert pf == "inf" or float(pf) >= 1.2
    for v in r["overfit"]:
        assert v["status"] == "OVERFIT"
        assert "why" in v


def test_signal_functions_return_valid_values():
    df = _random_walk(n=300)
    for name, fn, _ in G.build_variants(max_variants=10):
        assert fn(df) in ("BUY", "SELL", None)


def test_pf_ok_handles_all_forms():
    assert G._pf_ok("inf", 1.3) is True
    assert G._pf_ok(None, 1.3) is False
    assert G._pf_ok(1.5, 1.3) is True
    assert G._pf_ok(1.1, 1.3) is False


def test_min_win_rate_gate_enforced_on_both_splits():
    df = _random_walk(n=900, seed=11)
    r = G.generate_strategies(df, top_n=5, min_win_rate=60.0)
    assert r["min_win_rate_filter"] == 60.0
    for v in r["validated"]:
        assert v["train"]["win_rate_pct"] >= 60.0
        assert v["test"]["win_rate_pct"] >= 60.0
        # Win rate alone is never enough — profitability gates still apply.
        assert v["test"]["expectancy_r"] > 0


def test_exit_profiles_are_gridded():
    df = _random_walk(n=900, seed=5)
    r = G.generate_strategies(df, top_n=3)
    # variants_tried now counts entry-variants × exit-profiles.
    assert r["variants_tried"] == 28 * len(G.EXIT_PROFILES)
    # Every result carries its exit params.
    for v in r["validated"] + r["overfit"]:
        assert "sl_atr" in v["params"] and "target_atr" in v["params"]
