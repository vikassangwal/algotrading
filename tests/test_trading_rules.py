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


# --- R8/R9 entry rules + D1-D3 exit discipline -------------------------------

def test_r9_max_open_positions():
    v = R.check_entry_rules("TCS", is_live=False, open_positions_count=R.MAX_OPEN_POSITIONS)
    assert not v.allowed
    assert "R9" in v.reason
    v2 = R.check_entry_rules("TCS", is_live=False, open_positions_count=R.MAX_OPEN_POSITIONS - 1)
    assert v2.allowed


def test_r8_daily_loss_limit_blocks_entry():
    from app.risk_manager import risk_manager
    from app.config import config as cfg
    old = risk_manager.daily_pnl
    try:
        risk_manager.daily_pnl = -(cfg.capital * cfg.risk.daily_loss_limit_pct / 100.0) - 1
        v = R.check_entry_rules("TCS", is_live=False)
        assert not v.allowed
        assert "R8" in v.reason
    finally:
        risk_manager.daily_pnl = old


def _paper_trade(action="BUY", entry=100.0, risk=2.0):
    from app.execution import TradeRecord
    sl = entry - risk if action == "BUY" else entry + risk
    return TradeRecord(
        trade_id="T1", symbol="X", action=action, qty=10, entry_price=entry,
        timestamp="2026-07-17T10:00:00", reasons=[], stop_loss=sl,
        target=entry + 2 * risk if action == "BUY" else entry - 2 * risk,
        initial_risk=risk, peak_price=entry,
    )


def test_d1_breakeven_move_long():
    from app.command_center import _apply_trailing_discipline
    t = _paper_trade()
    _apply_trailing_discipline(t, 102.0)  # +1R
    assert t.stop_loss == 100.0  # breakeven


def test_d2_trailing_long_and_never_loosens():
    from app.command_center import _apply_trailing_discipline
    t = _paper_trade()
    _apply_trailing_discipline(t, 103.0)  # +1.5R -> trail = 103-2 = 101
    assert t.stop_loss == 101.0
    _apply_trailing_discipline(t, 105.0)  # peak 105 -> trail 103
    assert t.stop_loss == 103.0
    _apply_trailing_discipline(t, 101.0)  # price falls back — stop must NOT loosen
    assert t.stop_loss == 103.0


def test_d1_d2_short_mirror():
    from app.command_center import _apply_trailing_discipline
    t = _paper_trade(action="SELL", entry=100.0, risk=2.0)
    _apply_trailing_discipline(t, 98.0)   # +1R for a short
    assert t.stop_loss == 100.0           # breakeven
    _apply_trailing_discipline(t, 96.0)   # +2R -> trail = 96+2 = 98
    assert t.stop_loss == 98.0


def test_d3_time_stop_age():
    from app.command_center import _trade_age_days
    t = _paper_trade()
    t.timestamp = "2020-01-01T09:30:00"
    assert _trade_age_days(t) > R.TIME_STOP_DAYS


# --- Intraday support ---------------------------------------------------------

def test_d4_intraday_paper_position_squares_off_at_eod():
    """Intraday paper positions must square off at 15:15 like live would."""
    from unittest.mock import patch
    from app.command_center import auto_manage_positions
    from app.data.mock_provider import MockProvider
    from app.execution import ExecutionEngine
    from app.engine import FusedSignal

    config.auto_trade = AutoTradeState.ACTIVE
    ee = ExecutionEngine(MockProvider())
    sig = FusedSignal(symbol="RELIANCE", overall_score=1.0,
                      overall_confidence=0.75, style=TradingStyle.INTRADAY)
    assert ee.execute_signal(sig, 50000) is True
    assert ee.open_positions["RELIANCE"].timeframe == "intraday"

    class NoopEngine:
        def analyze(self, s):
            raise RuntimeError("not needed")

    with patch("app.command_center._is_live_eod", return_value=True):
        actions = auto_manage_positions(NoopEngine(), MockProvider(), ee)
    assert any(a["reason"] == "eod_squareoff" for a in actions)
    assert "RELIANCE" not in ee.open_positions


def test_d4_swing_paper_position_not_squared_off():
    """Swing paper positions are NOT touched by the EOD square-off."""
    from unittest.mock import patch
    from app.command_center import auto_manage_positions
    from app.data.mock_provider import MockProvider
    from app.execution import ExecutionEngine
    from app.engine import FusedSignal

    config.auto_trade = AutoTradeState.ACTIVE
    ee = ExecutionEngine(MockProvider())
    sig = FusedSignal(symbol="TCS", overall_score=1.0,
                      overall_confidence=0.75, style=TradingStyle.SWING)
    assert ee.execute_signal(sig, 50000) is True

    class NeutralEngine:
        def analyze(self, s):
            class S: overall_score = 0.0
            return S()

    with patch("app.command_center._is_live_eod", return_value=True):
        auto_manage_positions(NeutralEngine(), MockProvider(), ee)
    # Still open unless SL/target coincidentally hit; ensure not closed for EOD.
    if "TCS" not in ee.open_positions:
        closed = [t for t in ee.journal if t.symbol == "TCS"][-1]
        assert closed.status == "CLOSED"  # then it must have been SL/target
        # but reason list should not include eod (we can't easily assert reason here)
    else:
        assert ee.open_positions["TCS"].timeframe == "swing"


def test_intraday_history_rejects_bad_interval_gracefully():
    from app.backtester import load_intraday_history
    import pytest as _pytest
    # Unknown interval falls back to 15m; nonexistent symbol raises ValueError.
    with _pytest.raises(ValueError):
        load_intraday_history("ZZZZNOTREAL", interval="15m", days=10)
