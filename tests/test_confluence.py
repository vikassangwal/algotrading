"""Offline tests for the confluence trade-setup engine."""
from unittest.mock import patch

from app.data.mock_provider import MockProvider
from app.engine import SignalFusionEngine
from app.modules import confluence as C


def _setup(symbol="RELIANCE"):
    provider = MockProvider()
    engine = SignalFusionEngine(provider)
    return C.build_trade_setup(symbol, provider, engine)


def test_setup_structure():
    s = _setup()
    for key in ("symbol", "verdict", "reason", "confluence", "disclaimer"):
        assert key in s
    assert s["verdict"] in ("BUY", "SELL", "NO_TRADE")
    conf = s["confluence"]
    assert conf["bull_points"] >= 0 and conf["bear_points"] >= 0
    for f in conf["factors"]:
        assert f["direction"] in ("BULL", "BEAR", "NEUTRAL")
        assert f["weight"] >= 1


def test_no_trade_when_evidence_thin():
    fake_fa = {
        "symbol": "X", "quote": {"price": 100.0, "change_pct": 0.0},
        "indicators": {}, "indicator_consensus": {"lean": "NEUTRAL"},
        "smc": {}, "regime": {"regime": "UNKNOWN"},
        "base_strategy_signals": {}, "deployed_strategies": [],
        "institutional": {}, "fused_signal": {"action": "NEUTRAL"},
        "trade_plan": {"atr_14": 2.0, "if_buy": {}, "if_sell": {}},
    }
    with patch("app.modules.full_analysis.full_analysis", return_value=fake_fa):
        s = C.build_trade_setup("X", None, None)
    assert s["verdict"] == "NO_TRADE"
    assert "evidence" in s["reason"].lower() or "conflict" in s["reason"].lower()


def test_buy_verdict_on_aligned_bullish_evidence():
    fake_fa = {
        "symbol": "X", "quote": {"price": 100.0, "change_pct": 1.5},
        "indicator_consensus": {"lean": "BULLISH", "bullish": 6, "bearish": 1},
        "smc": {
            "market_structure": {"trend": "BULLISH", "recent_labels": ["HH", "HL"],
                                  "bos": {"direction": "BULLISH", "meaning": "bos"},
                                  "choch": None},
            "premium_discount": {"zone": "DISCOUNT (buy-favored)", "position": 0.2},
            "liquidity_sweeps": [], "support_resistance": [],
            "adx": {"adx": 30.0},
        },
        "regime": {"regime": "TRENDING"},
        "deployed_strategies": [], "institutional": {},
        "fused_signal": {"action": "BUY", "score": 0.5, "confidence": 0.7},
        "trade_plan": {"atr_14": 2.0,
                       "if_buy": {"stop_loss": 97.0, "target": 104.5},
                       "if_sell": {"stop_loss": 103.0, "target": 95.5}},
    }
    with patch("app.modules.full_analysis.full_analysis", return_value=fake_fa):
        s = C.build_trade_setup("X", None, None)
    assert s["verdict"] == "BUY"
    assert s["trade_plan"]["stop_loss"] == 97.0
    assert s["confluence"]["bull_points"] >= C.MIN_TOTAL_POINTS


def test_conflicting_evidence_is_no_trade():
    fake_fa = {
        "symbol": "X", "quote": {"price": 100.0, "change_pct": 0.2},
        "indicator_consensus": {"lean": "BULLISH", "bullish": 5, "bearish": 2},
        "smc": {
            "market_structure": {"trend": "BEARISH", "recent_labels": ["LL", "LH"],
                                  "bos": {"direction": "BEARISH", "meaning": "bos"},
                                  "choch": None},
            "premium_discount": {"zone": "DISCOUNT (buy-favored)", "position": 0.2},
            "liquidity_sweeps": [], "support_resistance": [], "adx": {"adx": 15.0},
        },
        "regime": {"regime": "RANGE_BOUND"},
        "deployed_strategies": [], "institutional": {},
        "fused_signal": {"action": "BUY", "score": 0.3, "confidence": 0.6},
        "trade_plan": {"atr_14": 2.0, "if_buy": {}, "if_sell": {}},
    }
    with patch("app.modules.full_analysis.full_analysis", return_value=fake_fa):
        s = C.build_trade_setup("X", None, None)
    assert s["verdict"] == "NO_TRADE"
    assert "conflict" in s["reason"].lower()


def test_validated_strategy_blocked_by_regime_counts_neutral():
    fake_fa = {
        "symbol": "X", "quote": {"price": 100.0, "change_pct": 0.0},
        "indicator_consensus": {"lean": "NEUTRAL"},
        "smc": {}, "regime": {"regime": "TRENDING"},
        "deployed_strategies": [
            {"name": "RSI thing", "signal": "BUY", "regime_ok": False, "symbol": "X"},
        ],
        "institutional": {}, "fused_signal": {"action": "NEUTRAL"},
        "trade_plan": {"atr_14": 2.0, "if_buy": {}, "if_sell": {}},
    }
    with patch("app.modules.full_analysis.full_analysis", return_value=fake_fa):
        s = C.build_trade_setup("X", None, None)
    blocked = [f for f in s["confluence"]["factors"] if "BLOCKED" in f["detail"]]
    assert blocked and blocked[0]["direction"] == "NEUTRAL"
    assert s["verdict"] == "NO_TRADE"


def test_target_capped_at_resistance():
    fake_fa = {
        "symbol": "X", "quote": {"price": 100.0, "change_pct": 1.0},
        "indicator_consensus": {"lean": "BULLISH", "bullish": 6, "bearish": 0},
        "smc": {
            "market_structure": {"trend": "BULLISH", "recent_labels": ["HH", "HL"],
                                  "bos": {"direction": "BULLISH", "meaning": "bos"},
                                  "choch": None},
            "premium_discount": {"zone": "DISCOUNT (buy-favored)", "position": 0.3},
            "liquidity_sweeps": [],
            "support_resistance": [
                {"level": 102.5, "kind": "RESISTANCE", "touches": 5, "distance_pct": 2.5},
            ],
            "adx": {"adx": 28.0},
        },
        "regime": {"regime": "TRENDING"},
        "deployed_strategies": [], "institutional": {},
        "fused_signal": {"action": "BUY", "score": 0.5, "confidence": 0.7},
        "trade_plan": {"atr_14": 2.0,
                       "if_buy": {"stop_loss": 97.0, "target": 104.5},
                       "if_sell": {}},
    }
    with patch("app.modules.full_analysis.full_analysis", return_value=fake_fa):
        s = C.build_trade_setup("X", None, None)
    assert s["verdict"] == "BUY"
    assert s["trade_plan"]["target_capped_at_resistance"] == 102.5
