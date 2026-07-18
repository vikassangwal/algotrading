"""Tests for the auto buy/sell loop + trade verification."""
from unittest.mock import patch

import pytest

from app.auto_trader import AutoTrader
from app.config import config, AutoTradeState
from app.data.mock_provider import MockProvider
from app.execution import ExecutionEngine
from app.risk_manager import risk_manager


@pytest.fixture(autouse=True)
def clean_state():
    from app import trading_rules as R
    R._state.day = ""
    R._state.trades_today = 0
    R._state.consecutive_losses = 0
    R._state.last_sl_exit.clear()
    config.auto_trade = AutoTradeState.OFF
    config.paper_mode = True
    risk_manager.portfolio_exposure = 0.0
    yield
    config.auto_trade = AutoTradeState.OFF
    config.paper_mode = True


def _deployed_row(signal="BUY", tradeable=True):
    return {
        "id": 1, "name": "Test RSI [1:1]", "symbol": "RELIANCE",
        "params": {"template": "rsi_reversion", "period": 14,
                   "oversold": 30, "overbought": 70,
                   "sl_atr": 1.5, "target_atr": 1.5},
        "active": True, "signal": signal, "regime_ok": True,
        "tradeable": tradeable,
    }


def test_scan_executes_and_verifies_paper_trade():
    config.auto_trade = AutoTradeState.ACTIVE
    ee = ExecutionEngine(MockProvider())
    at = AutoTrader()

    exec_result = {"executed": True, "signal": "BUY", "allocation": 50000,
                   "reason": "executed through gated chain"}

    def fake_execute(provider, execution_engine, rm, sid):
        # Simulate what execute_deployed does: route through the real engine.
        from app.engine import FusedSignal
        from app.config import TradingStyle
        sig = FusedSignal(symbol="RELIANCE", overall_score=1.0,
                          overall_confidence=0.75, style=TradingStyle.SWING)
        ok = execution_engine.execute_signal(sig, 50000)
        return dict(exec_result, executed=ok)

    with patch("app.strategy_runtime.evaluate_deployed", return_value=[_deployed_row()]), \
         patch("app.strategy_runtime.execute_deployed", side_effect=fake_execute):
        actions = at.scan_once(MockProvider(), ee, risk_manager)

    assert len(actions) == 1
    a = actions[0]
    assert a["executed"] is True
    v = a["verification"]
    assert v["status"] == "CONFIRMED_PAPER"
    assert v["checks"]["position_open"] and v["checks"]["has_mandatory_sl"]


def test_scan_skips_untradeable_signals():
    ee = ExecutionEngine(MockProvider())
    at = AutoTrader()
    rows = [_deployed_row(signal="BUY", tradeable=False),   # regime blocked
            _deployed_row(signal=None, tradeable=False)]    # no signal
    with patch("app.strategy_runtime.evaluate_deployed", return_value=rows):
        actions = at.scan_once(MockProvider(), ee, risk_manager)
    assert actions == []


def test_scan_never_doubles_an_open_position():
    config.auto_trade = AutoTradeState.ACTIVE
    ee = ExecutionEngine(MockProvider())
    at = AutoTrader()
    # Open a position first.
    from app.engine import FusedSignal
    from app.config import TradingStyle
    sig = FusedSignal(symbol="RELIANCE", overall_score=1.0,
                      overall_confidence=0.75, style=TradingStyle.SWING)
    assert ee.execute_signal(sig, 50000) is True

    with patch("app.strategy_runtime.evaluate_deployed", return_value=[_deployed_row()]):
        actions = at.scan_once(MockProvider(), ee, risk_manager)
    assert actions == []  # symbol already held -> no re-entry


def test_verify_detects_missing_position():
    ee = ExecutionEngine(MockProvider())
    at = AutoTrader()
    v = at.verify_trade("TCS", ee)  # never traded
    assert v["status"] == "FAILED"


def test_verify_live_without_order_id_is_unverified():
    config.auto_trade = AutoTradeState.ACTIVE
    ee = ExecutionEngine(MockProvider())
    from app.engine import FusedSignal
    from app.config import TradingStyle
    sig = FusedSignal(symbol="RELIANCE", overall_score=1.0,
                      overall_confidence=0.75, style=TradingStyle.SWING)
    assert ee.execute_signal(sig, 50000) is True

    config.paper_mode = False  # pretend live AFTER the fill (no order id stored)
    v = AutoTrader().verify_trade("RELIANCE", ee)
    assert v["status"] == "UNVERIFIED"
    assert "order id" in v["detail"].lower()


def test_verify_all_shape():
    ee = ExecutionEngine(MockProvider())
    at = AutoTrader()
    out = at.verify_all(ee)
    assert out["open_positions"] == 0
    assert "verified" in out


def test_rules_still_gate_auto_trades():
    """R1: HALTED system -> auto scan executes nothing even if signal fires."""
    config.auto_trade = AutoTradeState.HALTED
    ee = ExecutionEngine(MockProvider())
    at = AutoTrader()

    def fake_execute(provider, execution_engine, rm, sid):
        from app.engine import FusedSignal
        from app.config import TradingStyle
        sig = FusedSignal(symbol="RELIANCE", overall_score=1.0,
                          overall_confidence=0.75, style=TradingStyle.SWING)
        ok = execution_engine.execute_signal(sig, 50000)  # R1 blocks inside
        return {"executed": ok, "reason": "gated"}

    with patch("app.strategy_runtime.evaluate_deployed", return_value=[_deployed_row()]), \
         patch("app.strategy_runtime.execute_deployed", side_effect=fake_execute):
        actions = at.scan_once(MockProvider(), ee, risk_manager)

    assert len(actions) == 1
    assert actions[0]["executed"] is False
    assert "RELIANCE" not in ee.open_positions
