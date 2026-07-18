"""Restart-survival tests: a server restart must never reset the rules."""
import pytest

from app import state_store as SS
from app import trading_rules as R
from app.config import config, AutoTradeState, TradingStyle
from app.data.mock_provider import MockProvider
from app.engine import FusedSignal
from app.execution import ExecutionEngine
from app.risk_manager import risk_manager


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    # Isolate the state file per test.
    monkeypatch.setattr(SS, "STATE_PATH", tmp_path / "runtime_state.json")
    R._state.day = ""
    R._state.trades_today = 0
    R._state.consecutive_losses = 0
    R._state.last_sl_exit.clear()
    config.auto_trade = AutoTradeState.ACTIVE
    config.paper_mode = True
    risk_manager.daily_pnl = 0.0
    risk_manager.portfolio_exposure = 0.0
    SS._execution_engine = None
    yield
    config.auto_trade = AutoTradeState.OFF
    SS._execution_engine = None


def _open_paper_position(ee, symbol="RELIANCE"):
    sig = FusedSignal(symbol=symbol, overall_score=1.0,
                      overall_confidence=0.75, style=TradingStyle.SWING)
    assert ee.execute_signal(sig, 50000) is True
    return ee.open_positions[symbol]


def test_full_restart_cycle_restores_rules_and_positions():
    ee = ExecutionEngine(MockProvider())
    SS.register(ee)
    trade = _open_paper_position(ee)
    assert R._state.trades_today == 1
    assert SS.STATE_PATH.exists()  # entry persisted automatically

    # --- simulate a crash: fresh engine + wiped in-memory state -------------
    R._state.trades_today = 0
    R._state.day = ""
    risk_manager.daily_pnl = -123.0  # will be overwritten by restore
    ee2 = ExecutionEngine(MockProvider())
    SS.register(ee2)
    out = SS.restore_all()

    assert out["restored"] and out["same_day"]
    assert out["positions"] == 1
    restored = ee2.open_positions["RELIANCE"]
    assert restored.stop_loss == trade.stop_loss      # SL survives
    assert restored.target == trade.target
    assert restored.initial_risk == trade.initial_risk
    assert R._state.trades_today == 1                  # R5 counter survives
    assert risk_manager.daily_pnl == 0.0


def test_halt_survives_restart():
    """R7's HALTED state must NOT be resettable by bouncing the server."""
    ee = ExecutionEngine(MockProvider())
    SS.register(ee)
    config.auto_trade = AutoTradeState.HALTED
    SS.persist_all()

    config.auto_trade = AutoTradeState.ACTIVE  # crash + naive default
    SS.restore_all()
    assert config.auto_trade == AutoTradeState.HALTED


def test_active_does_not_auto_resume():
    """ACTIVE must NOT auto-restore — a human re-arms auto-trading."""
    ee = ExecutionEngine(MockProvider())
    SS.register(ee)
    config.auto_trade = AutoTradeState.ACTIVE
    SS.persist_all()

    config.auto_trade = AutoTradeState.OFF
    SS.restore_all()
    assert config.auto_trade == AutoTradeState.OFF


def test_stale_day_state_not_restored_but_positions_are():
    ee = ExecutionEngine(MockProvider())
    SS.register(ee)
    _open_paper_position(ee, "TCS")
    # Tamper the file to look like yesterday's snapshot.
    import json
    data = json.loads(SS.STATE_PATH.read_text(encoding="utf-8"))
    data["day"] = "2000-01-01"
    data["rules"]["trades_today"] = 9
    SS.STATE_PATH.write_text(json.dumps(data), encoding="utf-8")

    R._state.trades_today = 0
    ee2 = ExecutionEngine(MockProvider())
    SS.register(ee2)
    out = SS.restore_all()
    assert out["positions"] == 1                       # swing position survives
    assert R._state.trades_today == 0                  # yesterday's counters don't
    assert not out["same_day"]


def test_cooldown_survives_restart():
    ee = ExecutionEngine(MockProvider())
    SS.register(ee)
    R.record_exit("TCS", pnl=-100.0, was_stop_loss=True)  # persists cooldown

    R._state.last_sl_exit.clear()
    SS.restore_all()
    assert "TCS" in R._state.last_sl_exit                 # R6 survives
    v = R.check_entry_rules("TCS", is_live=False)
    assert not v.allowed and "R6" in v.reason


def test_missing_file_is_graceful():
    out = SS.restore_all()
    assert out["restored"] is False
    assert "no prior state" in out["detail"]
