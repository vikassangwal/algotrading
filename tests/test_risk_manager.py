"""Tests for RiskManager — the financial-safety-critical sizing and limits."""
import pytest

from app.risk_manager import RiskManager
from app.config import config, AutoTradeState
from app.engine import FusedSignal, TradingStyle


def make_signal(score=0.8, confidence=0.8):
    return FusedSignal(
        symbol="TEST",
        overall_score=score,
        overall_confidence=confidence,
        style=TradingStyle.SWING,
    )


@pytest.fixture(autouse=True)
def reset_state():
    """Isolate global config/risk state between tests."""
    old_auto = config.auto_trade
    old_cap = config.capital
    config.auto_trade = AutoTradeState.ACTIVE
    config.capital = 1_000_000.0
    yield
    config.auto_trade = old_auto
    config.capital = old_cap


def test_rejects_when_autotrade_off():
    config.auto_trade = AutoTradeState.OFF
    rm = RiskManager()
    assert rm.calculate_position_size(make_signal()) == 0.0


def test_rejects_neutral_signal():
    rm = RiskManager()
    assert rm.calculate_position_size(make_signal(score=0.0, confidence=0.0)) == 0.0


def test_daily_loss_hard_stop_triggers_halt():
    rm = RiskManager()
    # Push daily PnL below the hard limit
    rm.daily_pnl = -(config.capital * (config.risk.daily_loss_limit_pct / 100.0)) - 1
    assert rm.calculate_position_size(make_signal()) == 0.0
    assert config.auto_trade == AutoTradeState.HALTED


def test_negative_kelly_rejected():
    rm = RiskManager()
    # Very low confidence -> negative Kelly edge -> reject
    assert rm.calculate_position_size(make_signal(confidence=0.2)) == 0.0


def test_position_size_capped_at_max_position_pct():
    rm = RiskManager()
    alloc = rm.calculate_position_size(make_signal(confidence=0.95))
    max_allowed = config.capital * (config.risk.max_position_pct / 100.0)
    assert 0 < alloc <= max_allowed + 1e-6


def test_exposure_cap_blocks_when_full():
    rm = RiskManager()
    # Already fully exposed
    rm.portfolio_exposure = config.capital * (config.risk.max_portfolio_exposure_pct / 100.0)
    assert rm.calculate_position_size(make_signal(confidence=0.95)) == 0.0
