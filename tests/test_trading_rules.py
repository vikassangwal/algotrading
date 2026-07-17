"""Tests for the MANDATORY trading rules (R1–R7) and their enforcement
inside ExecutionEngine.execute_signal — the no-bypass property is the point.
"""
from datetime import datetime, timedelta

import pytest

from app import trading_rules as R
from app.config import config, AutoTradeState, TradingStyle
from app.engine import FusedSignal


@pytest.fixture(autouse=True)
def clean_state():
    """Reset rule state and config before every test."""
    R._state.day = ""
    R._state.trades_today = 0
    R._state.consecutive_losses = 0
    R._state.last_sl_exit.clear()
    config.auto_trade = AutoTradeState.OFF
    config.paper_mode = True
    yield
    config.auto_trade = AutoTradeState.OFF
    config.paper_mode = True


def test_r1_halted_system_blocks_everything():
    config.auto_trade = AutoTradeState.HALTED
    v = R.check_entry_rules("RELIANCE", is_live=False)
    assert not v.allowed
    assert "R1" in v.reason


def test_r5_max_trades_per_day():
    for _ in range(R.MAX_TRADES_PER_DAY):
        R.record_entry()
    v = R.check_entry_rules("TCS", is_live=False)
    assert not v.allowed
    assert "R5" in v.reason


def test_r6_cooldown_after_stop_loss():
    R.record_exit("INFY", pnl=-500.0, was_stop_loss=True)
    v = R.check_entry_rules("INFY", is_live=False)
    assert not v.allowed
    assert "R6" in v.reason
    # Different symbol is NOT blocked by INFY's cooldown.
    v2 = R.check_entry_rules("TCS", is_live=False)
    assert v2.allowed


def test_r6_cooldown_expires():
    R.record_exit("INFY", pnl=-500.0, was_stop_loss=True)
    # Backdate the SL exit beyond the cooldown window.
    R._state.last_sl_exit["INFY"] = (
        R._now_ist() - timedelta(minutes=R.SL_COOLDOWN_MINUTES + 1)
    )
    assert R.check_entry_rules("INFY", is_live=False).allowed


def test_r7_consecutive_losses_halts_the_day():
    for _ in range(R.MAX_CONSECUTIVE_LOSSES):
        R.record_exit("RELIANCE", pnl=-100.0, was_stop_loss=False)
    v = R.check_entry_rules("RELIANCE", is_live=False)
    assert not v.allowed
    # R1 fires because record_exit triggered the system halt, or R7 directly.
    assert ("R7" in v.reason) or ("R1" in v.reason)
    # A win resets the streak only if it comes before the breaker trips.


def test_win_resets_consecutive_losses():
    R.record_exit("A", pnl=-100.0, was_stop_loss=False)
    R.record_exit("B", pnl=-100.0, was_stop_loss=False)
    R.record_exit("C", pnl=+300.0, was_stop_loss=False)
    assert R._state.consecutive_losses == 0
    assert R.check_entry_rules("D", is_live=False).allowed


def test_r3_r4_mandatory_stops_shape():
    stops = R.compute_mandatory_stops("BUY", entry_price=100.0, atr=2.0)
    assert stops["stop_loss"] < 100.0 < stops["target"]
    # R4: reward distance >= risk distance.
    assert (stops["target"] - 100.0) >= (100.0 - stops["stop_loss"]) - 1e-9

    stops_s = R.compute_mandatory_stops("SELL", entry_price=100.0, atr=2.0)
    assert stops_s["target"] < 100.0 < stops_s["stop_loss"]


def test_r3_fallback_when_atr_unusable():
    stops = R.compute_mandatory_stops("BUY", entry_price=100.0, atr=0.0)
    assert stops["stop_loss"] < 100.0 < stops["target"]  # never naked


def test_execute_signal_enforces_rules_no_bypass():
    """The engine itself must refuse a trade when rules say no — regardless of
    caller. We halt the system and verify execute_signal returns False."""
    from app.data.mock_provider import MockProvider
    from app.execution import ExecutionEngine

    ee = ExecutionEngine(MockProvider())
    config.auto_trade = AutoTradeState.HALTED
    sig = FusedSignal(symbol="RELIANCE", overall_score=0.9,
                      overall_confidence=0.9, style=TradingStyle.INTRADAY)
    assert ee.execute_signal(sig, requested_allocation=50000) is False
    assert "RELIANCE" not in ee.open_positions


def test_execute_signal_attaches_mandatory_sl_target():
    """Every executed trade must carry a stop-loss and target (R3)."""
    from app.data.mock_provider import MockProvider
    from app.execution import ExecutionEngine

    ee = ExecutionEngine(MockProvider())
    config.auto_trade = AutoTradeState.ACTIVE
    sig = FusedSignal(symbol="RELIANCE", overall_score=0.9,
                      overall_confidence=0.9, style=TradingStyle.INTRADAY)
    ok = ee.execute_signal(sig, requested_allocation=100000)
    assert ok is True
    trade = ee.open_positions["RELIANCE"]
    assert trade.stop_loss > 0
    assert trade.target > trade.entry_price  # BUY side
    assert trade.stop_loss < trade.entry_price


def test_rules_status_shape():
    s = R.rules_status()
    for key in ("trades_today", "consecutive_losses", "market_open_now",
                "system_halted", "symbols_in_cooldown"):
        assert key in s


# --- Regime gate on deployed strategies -------------------------------------

def test_regime_gate_blocks_incompatible_regime():
    from app import strategy_runtime as SR

    class FakeProvider:
        pass

    # Monkeypatch regime detection: strongly trending market.
    orig = SR._regime_ok
    try:
        # reversion template in TRENDING -> blocked
        import app.modules.ai_regime as ai
        class FakeEngine:
            def __init__(self, p): pass
            def detect_regime(self, s): return {"regime": "TRENDING"}
        real_engine = ai.MarketRegimeEngine
        ai.MarketRegimeEngine = FakeEngine
        ok, regime = SR._regime_ok("rsi_reversion", FakeProvider(), "TCS")
        assert ok is False and regime == "TRENDING"
        # trend template in TRENDING -> allowed
        ok2, _ = SR._regime_ok("macd", FakeProvider(), "TCS")
        assert ok2 is True
        # reversion in RANGE_BOUND -> allowed
        class FakeEngine2(FakeEngine):
            def detect_regime(self, s): return {"regime": "RANGE_BOUND"}
        ai.MarketRegimeEngine = FakeEngine2
        ok3, _ = SR._regime_ok("rsi_reversion", FakeProvider(), "TCS")
        assert ok3 is True
    finally:
        ai.MarketRegimeEngine = real_engine
        assert SR._regime_ok is orig


def test_regime_gate_fails_open_on_detection_error():
    """Infrastructure failure must never block trades silently."""
    from app import strategy_runtime as SR
    import app.modules.ai_regime as ai

    class Boom:
        def __init__(self, p): raise RuntimeError("regime engine down")
    real_engine = ai.MarketRegimeEngine
    try:
        ai.MarketRegimeEngine = Boom
        ok, regime = SR._regime_ok("rsi_reversion", object(), "TCS")
        assert ok is True and regime == "DETECTION_FAILED"
    finally:
        ai.MarketRegimeEngine = real_engine
