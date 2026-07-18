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


# --- Auto-hunt daemon + options piggyback ------------------------------------

def test_hunt_daemon_weekend_gate(monkeypatch, tmp_path):
    from app import hunt_daemon as HD
    from datetime import datetime

    monkeypatch.setattr(HD, "STATE_PATH", tmp_path / "hunt.json")
    d = HD.HuntDaemon()

    class Wednesday:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 7, 15, 12, 0, tzinfo=HD.IST)
    monkeypatch.setattr(HD, "datetime", Wednesday)
    assert d._should_run() is False  # weekday

    class SaturdayNoon:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 7, 18, 12, 0, tzinfo=HD.IST)
    monkeypatch.setattr(HD, "datetime", SaturdayNoon)
    assert d._should_run() is True
    (tmp_path / "hunt.json").write_text('{"weekend": "2026-07-18"}', encoding="utf-8")
    assert d._should_run() is False  # once per weekend


def test_hunt_daemon_deploys_validated(monkeypatch, tmp_path):
    from unittest.mock import patch
    from app import hunt_daemon as HD

    monkeypatch.setattr(HD, "STATE_PATH", tmp_path / "hunt.json")
    d = HD.HuntDaemon()
    fake_hunt = {
        "book": [{"symbol": "TITAN", "name": "EMA X",
                  "params": {"template": "ema_cross", "fast": 10, "slow": 20,
                             "sl_atr": 1.5, "target_atr": 1.5},
                  "test": {"win_rate_pct": 70.0, "profit_factor": 2.0, "trades": 8}}],
        "no_edge": [{"symbol": "NTPC", "reason": "nothing validated"}],
    }
    with patch("app.modules.strategy_generator.hunt_validated", return_value=fake_hunt), \
         patch("app.strategy_runtime.deploy", return_value={"id": 99}) as dep:
        out = d.run_hunt(["TITAN", "NTPC"])
    assert dep.called
    assert out["result"]["deployed"][0]["symbol"] == "TITAN"
    assert out["result"]["no_edge"][0]["symbol"] == "NTPC"


def test_options_piggyback_buy_becomes_atm_ce():
    from unittest.mock import patch
    from app.auto_trader import AutoTrader

    fake_chain = {"available": True, "underlyingPrice": 24334.0,
                  "strikes": [24300.0, 24350.0, 24400.0],
                  "expirationDate": "21-Jul-2026",
                  "calls": [{"strike": 24350.0, "ltp": 115.0}],
                  "puts": [{"strike": 24350.0, "ltp": 110.0}]}
    with patch("app.options_trader._chain", return_value=fake_chain), \
         patch("app.options_trader.open_trade",
               return_value={"ok": True, "id": 7, "entry_ltp": 115.0}) as ot:
        r = AutoTrader._options_piggyback("NIFTY", "BUY")
    assert r["attempted"] and r["ok"]
    args = ot.call_args[0]
    assert args[1] == 24350.0 and args[2] == "CE"   # ATM call for a BUY


def test_options_piggyback_no_chain_fails_soft():
    from unittest.mock import patch
    from app.auto_trader import AutoTrader
    with patch("app.options_trader._chain", return_value={"available": False}):
        r = AutoTrader._options_piggyback("SOMESMALLCAP", "BUY")
    assert r["attempted"] is False
    assert "option chain" in r["reason"]
