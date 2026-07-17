"""Tests for UniversalScanner — vectorized multi-symbol scanning.

Verifies the rolling/groupby math is correct and does NOT bleed across symbols.
"""
import pandas as pd

from app.modules.multi_scanner import UniversalScanner


def _frame():
    # Two symbols interleaved; AAA has a clear volume spike + gap on its last row.
    rows = []
    # AAA: flat volume 100 for 20 bars, then a 5x spike; gap up on last bar.
    for i in range(20):
        rows.append({"symbol": "AAA", "Open": 100, "High": 101, "Low": 99, "Close": 100, "Volume": 100})
    rows.append({"symbol": "AAA", "Open": 110, "High": 112, "Low": 109, "Close": 111, "Volume": 500})
    # BBB: flat, no breakout, no gap.
    for i in range(21):
        rows.append({"symbol": "BBB", "Open": 50, "High": 51, "Low": 49, "Close": 50, "Volume": 200})
    return pd.DataFrame(rows)


def test_volume_breakout_detects_spike_only():
    scanner = UniversalScanner(_frame())
    out = scanner.scan_volume_breakouts(volume_multiplier=2.0, window=20)
    # Only AAA's spike row (volume 500 vs avg 100) should be flagged.
    assert list(out["symbol"].unique()) == ["AAA"]
    assert (out["Volume"] == 500).all()


def test_gap_up_detected_without_symbol_bleed():
    scanner = UniversalScanner(_frame())
    out = scanner.scan_gap_ups_downs(threshold_pct=0.5)
    # AAA gapped up (open 110 > prev high 101); BBB never gaps.
    aaa = out[out["symbol"] == "AAA"]
    assert aaa["Gap_Up"].any()
    assert "BBB" not in out["symbol"].values


def test_missing_column_raises():
    df = pd.DataFrame({"Close": [1, 2, 3]})
    try:
        UniversalScanner(df).scan_volume_breakouts()
        assert False, "expected ValueError for missing Volume column"
    except ValueError:
        pass


def test_momentum_shift_flags_crossover():
    # Build a single symbol whose ROC crosses from negative to positive.
    closes = [100, 98, 96, 94, 92, 90, 92, 96, 102, 110]
    df = pd.DataFrame({"Close": closes})
    out = UniversalScanner(df).scan_momentum_shifts(window=3)
    # At least one bullish shift should be detected as price reverses up.
    assert out["Bullish_Shift"].any()
