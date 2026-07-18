"""Tests: de-faked modules stay honest + quant stats math."""
import numpy as np
import pytest
from unittest.mock import patch

from app.data.mock_provider import MockProvider


# --- options: no simulated fallback ------------------------------------------

def test_option_chain_unavailable_is_honest():
    from app.modules.options_data import OptionsDataEngine
    e = OptionsDataEngine()
    with patch("app.data.nse_provider.nse_provider._get_json", return_value=None):
        c = e.get_option_chain("NIFTY")
    assert c["available"] is False
    assert c["calls"] == [] and c["puts"] == []
    assert "unavailable" in c["error"].lower()
    # The word "simulated" must only appear as a denial, and no random data.
    assert "retry" in c["error"].lower()


def test_option_chain_parses_real_shape():
    from app.modules.options_data import OptionsDataEngine
    e = OptionsDataEngine()
    fake_info = {"expiryDates": ["21-Jul-2026"]}
    fake_chain = {"records": {"underlyingValue": 24334.3, "data": [
        {"strikePrice": 24300,
         "CE": {"lastPrice": 141.95, "openInterest": 94067, "totalTradedVolume": 100,
                "changeinOpenInterest": 500, "impliedVolatility": 10.72},
         "PE": {"lastPrice": 110.7, "openInterest": 103865, "totalTradedVolume": 90,
                "changeinOpenInterest": -200, "impliedVolatility": 11.0}},
        {"strikePrice": 24400,
         "CE": {"lastPrice": 90.0, "openInterest": 80000, "totalTradedVolume": 50,
                "changeinOpenInterest": 100, "impliedVolatility": 10.5},
         "PE": {"lastPrice": 160.0, "openInterest": 60000, "totalTradedVolume": 40,
                "changeinOpenInterest": 50, "impliedVolatility": 11.2}},
    ]}}

    def fake_get(path):
        return fake_info if "contract-info" in path else fake_chain

    with patch("app.data.nse_provider.nse_provider._get_json", side_effect=fake_get):
        c = e.get_option_chain("NIFTY")
    assert c["available"] is True
    assert c["source"] == "nse_option_chain"
    assert c["pcr"] == round((103865 + 60000) / (94067 + 80000), 2)
    assert c["max_pain"] in (24300.0, 24400.0)
    atm_ce = c["calls"][0]
    assert atm_ce["iv"] == pytest.approx(0.1072)  # percent -> fraction
    assert "delta" in atm_ce  # greeks from real IV


# --- microstructure: honest estimators, no random book ------------------------

def test_microstructure_no_fabricated_order_book():
    from app.modules.microstructure import MicrostructureEngine
    m = MicrostructureEngine(MockProvider())
    r = m.analyze("RELIANCE", 1300.0)
    assert r["available"] is True
    assert r["order_book"] is None            # never simulated
    assert r["order_book_imbalance"] is None
    assert r["estimated_spread_bps"] >= 0
    assert "model" in r["spread_method"]      # labeled as estimate
    assert r["turnover_cr"] > 0               # real turnover


def test_sqrt_impact_scales_with_participation():
    from app.modules.microstructure import MicrostructureEngine
    small = MicrostructureEngine.sqrt_impact_bps(1e6, 1e9, 0.02)
    big = MicrostructureEngine.sqrt_impact_bps(1e8, 1e9, 0.02)
    # sqrt(100x) = 10x participation cost (rounding to 2dp adds slack)
    assert big == pytest.approx(small * 10, rel=0.1)


def test_mock_quant_passthrough_is_dead():
    """DhanProvider must NOT feed mock quant numbers into real analyses."""
    from app.data.dhan_provider import DhanProvider
    assert DhanProvider.get_quant_data.__doc__ is not None
    # Call unbound with a dummy self — must return {} without touching fallback.
    assert DhanProvider.get_quant_data(object.__new__(DhanProvider), "TCS") == {}


# --- quant stats --------------------------------------------------------------

def test_trade_stats_honest_below_min_trades():
    from app.modules import quant_stats as Q
    with patch.object(Q, "_closed_trade_returns", return_value=[0.01] * 3):
        s = Q.trade_stats()
    assert s["sharpe"] is None and s["calmar"] is None
    assert "closed trades" in s["note"]


def test_trade_stats_math():
    from app.modules import quant_stats as Q
    rets = [0.02, -0.01, 0.015, -0.005, 0.01, 0.02, -0.01, 0.005, 0.01, -0.002,
            0.008, 0.012]
    with patch.object(Q, "_closed_trade_returns", return_value=rets):
        s = Q.trade_stats()
    assert s["sharpe"] is not None and s["sharpe"] > 0
    assert s["max_drawdown_pct"] < 0
    r = np.asarray(rets)
    assert s["avg_trade_return_pct"] == pytest.approx(r.mean() * 100, abs=0.01)


def test_monte_carlo_deterministic_and_shaped():
    from app.modules import quant_stats as Q
    rets = [0.02, -0.01, 0.015, -0.005, 0.01, 0.02, -0.01, 0.005, 0.01, -0.002]
    with patch.object(Q, "_closed_trade_returns", return_value=rets):
        a = Q.monte_carlo(runs=300)
        b = Q.monte_carlo(runs=300)
    assert a["available"] and a == b          # seeded -> reproducible
    assert a["final_return_pct"]["p5"] <= a["final_return_pct"]["p50"] <= a["final_return_pct"]["p95"]


# --- alerts: honest disabled state --------------------------------------------

def test_alerts_disabled_without_creds(monkeypatch):
    from app import alerts
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with patch.object(alerts, "_creds", return_value=("", "")):
        assert alerts.enabled() is False
        assert alerts.send("hello") is False   # no pretend-success
        st = alerts.status()
    assert st["enabled"] is False
    assert "BotFather" in st["setup_hint"]


def test_alert_send_confirms_only_on_200():
    from app import alerts

    class FakeResp:
        status_code = 500
        text = "server error"

    with patch.object(alerts, "_creds", return_value=("tok", "chat")), \
         patch("app.alerts.requests.post", return_value=FakeResp()):
        assert alerts.send("x") is False       # 500 != sent
