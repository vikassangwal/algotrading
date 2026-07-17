"""Offline tests for the full-analysis module (MockProvider, no network)."""
from app.data.mock_provider import MockProvider
from app.engine import SignalFusionEngine
from app.modules.full_analysis import full_analysis, _consensus


def _run(symbol="RELIANCE"):
    provider = MockProvider()
    engine = SignalFusionEngine(provider)
    return full_analysis(symbol, provider, engine)


def test_full_analysis_structure():
    r = _run()
    for key in ("quote", "indicators", "indicator_consensus", "regime",
                "base_strategy_signals", "deployed_strategies",
                "institutional", "fused_signal", "trade_plan", "disclaimer"):
        assert key in r, f"missing {key}"


def test_indicators_have_readings():
    r = _run()
    ind = r["indicators"]
    for name in ("rsi_14", "macd_12_26_9", "ema_stack", "bollinger_20_2",
                 "supertrend_7_3", "volume", "fifty_two_week"):
        assert name in ind
    assert ind["rsi_14"]["reading"]  # non-empty
    assert 0 <= ind["rsi_14"]["value"] <= 100


def test_consensus_tally_math():
    fake = {
        "a": {"reading": "BULLISH"},
        "b": {"reading": "BULLISH (oversold)"},
        "c": {"reading": "BEARISH"},
        "d": {"reading": "NEUTRAL"},
    }
    c = _consensus(fake)
    assert c["bullish"] == 2 and c["bearish"] == 1 and c["neutral"] == 1


def test_trade_plan_uses_r3_math():
    r = _run()
    tp = r["trade_plan"]
    assert tp["atr_14"] > 0
    buy = tp["if_buy"]
    assert buy["stop_loss"] < buy["target"]


def test_base_signals_are_valid_values():
    r = _run()
    for name, sig in r["base_strategy_signals"].items():
        assert sig in ("BUY", "SELL", None), f"{name} returned {sig}"


def test_insufficient_data_is_honest():
    class TinyProvider(MockProvider):
        def get_candles(self, symbol, timeframe="1d", count=280):
            return super().get_candles(symbol, timeframe=timeframe, count=count)[:10]

    provider = TinyProvider()
    engine = SignalFusionEngine(provider)
    r = full_analysis("RELIANCE", provider, engine)
    assert "error" in r
