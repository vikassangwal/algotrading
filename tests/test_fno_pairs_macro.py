"""Tests: paper options discipline, pairs math, macro shape."""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from app.config import config, AutoTradeState


@pytest.fixture(autouse=True)
def reset_state():
    config.auto_trade = AutoTradeState.OFF
    yield
    config.auto_trade = AutoTradeState.OFF


FAKE_CHAIN = {
    "available": True, "expirationDate": "21-Jul-2026", "underlyingPrice": 24334.3,
    "calls": [{"strike": 24350.0, "ltp": 115.3, "oi": 1, "volume": 1, "iv": 0.107}],
    "puts": [{"strike": 24350.0, "ltp": 110.7, "oi": 1, "volume": 1, "iv": 0.11}],
}


def test_option_paper_trade_uses_real_ltp(tmp_path):
    from app import options_trader as OT
    with patch.object(OT, "_chain", return_value=FAKE_CHAIN):
        r = OT.open_trade("NIFTY", 24350, "CE", qty=10)
        assert r["ok"] and r["entry_ltp"] == 115.3
        c = OT.close_trade(r["id"])
        assert c["ok"] and c["pnl"] == 0.0


def test_option_selling_refused():
    from app import options_trader as OT
    r = OT.open_trade("NIFTY", 24350, "XX", qty=10)
    assert not r["ok"]


def test_option_halt_blocks_entry():
    from app import options_trader as OT
    config.auto_trade = AutoTradeState.HALTED
    r = OT.open_trade("NIFTY", 24350, "CE", qty=10)
    assert not r["ok"] and "R1" in r["reason"]


def test_option_premium_cap():
    from app import options_trader as OT
    big_chain = dict(FAKE_CHAIN, calls=[{"strike": 24350.0, "ltp": 500.0,
                                         "oi": 1, "volume": 1, "iv": 0.1}])
    with patch.object(OT, "_chain", return_value=big_chain):
        r = OT.open_trade("NIFTY", 24350, "CE", qty=100)  # 50k premium
    assert not r["ok"] and "capital" in r["reason"].lower()


def test_option_no_chain_no_trade():
    from app import options_trader as OT
    with patch.object(OT, "_chain", return_value={"available": False, "error": "down"}):
        r = OT.open_trade("NIFTY", 24350, "CE", qty=10)
    assert not r["ok"]  # never trades on missing data


# --- pairs math ---------------------------------------------------------------

def test_pair_zscore_detects_dislocation():
    from app.modules.pairs_scanner import analyze_pair
    rng = np.random.default_rng(7)
    # Strong common factor, small idiosyncratic noise -> correlated returns.
    base = 100 + rng.normal(0, 1.0, 300).cumsum()
    a = pd.Series(base + rng.normal(0, 0.3, 300))
    b = pd.Series(base * 0.9 + rng.normal(0, 0.3, 300))
    st = analyze_pair(a, b)
    assert st["correlation"] > 0.5
    baseline_z = abs(st["z_score"])

    a2 = a.copy()
    a2.iloc[-1] += 12  # violent dislocation on the last bar
    st2 = analyze_pair(a2, b)
    assert abs(st2["z_score"]) > baseline_z + 1.0


def test_scan_pairs_reports_failures():
    from app.modules import pairs_scanner as PS
    with patch.object(PS, "_closes", return_value=None):
        r = PS.scan_pairs(["banks"])
    assert r["sectors_failed"] == ["banks"]
    assert r["signals"] == []


# --- macro shape --------------------------------------------------------------

def test_macro_watch_handles_download_failure():
    from app.modules import macro_assets as MA
    import yfinance
    with patch.object(yfinance, "download", side_effect=RuntimeError("net down")):
        r = MA.macro_watch()
    assert "error" in r
    assert r["assets"] == {}  # nothing invented
