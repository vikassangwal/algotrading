"""Tests for execution: safe live-gating and position close accounting."""
import os

from app.execution import ExecutionEngine, TradeRecord, live_trading_enabled
from app.risk_manager import risk_manager
from app.config import config
from app.data.mock_provider import MockProvider
from datetime import datetime


def test_live_trading_disabled_by_default(monkeypatch):
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    config.paper_mode = True
    assert live_trading_enabled() is False


def test_live_requires_both_paper_off_and_flag(monkeypatch):
    # paper_mode off but flag not set -> still disabled
    config.paper_mode = False
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    assert live_trading_enabled() is False
    # both conditions -> enabled
    monkeypatch.setenv("LIVE_TRADING", "true")
    assert live_trading_enabled() is True
    config.paper_mode = True  # restore safe default


def test_close_position_books_pnl_and_releases_exposure():
    eng = ExecutionEngine(MockProvider(seed=1))
    trade = TradeRecord(
        trade_id="T1", symbol="TEST", action="BUY", qty=10,
        entry_price=100.0, timestamp=datetime.now().isoformat(), reasons=[],
    )
    eng.open_positions["TEST"] = trade
    risk_manager.portfolio_exposure = 1000.0
    before = risk_manager.daily_pnl

    ok = eng.close_position("TEST", exit_price=110.0)
    assert ok
    assert trade.pnl == 100.0            # (110-100)*10
    assert trade.status == "CLOSED"
    assert risk_manager.portfolio_exposure == 0.0
    assert risk_manager.daily_pnl - before == 100.0
    assert "TEST" not in eng.open_positions


def test_close_unknown_position_returns_false():
    eng = ExecutionEngine(MockProvider(seed=1))
    assert eng.close_position("NOPE", exit_price=100.0) is False
