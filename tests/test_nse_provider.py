"""Offline tests for the NSE adapter — parsing & graceful degradation.

These stub the network layer (_get_json) so they run without hitting NSE.
"""
from app.data.nse_provider import NSEProvider


def _provider_returning(payloads):
    """Build an NSEProvider whose _get_json returns canned payloads by path substring."""
    p = NSEProvider()

    def fake_get_json(path):
        for needle, value in payloads.items():
            if needle in path:
                return value
        return None

    p._get_json = fake_get_json
    return p


def test_fii_dii_parsing():
    p = _provider_returning({
        "fiidiiTradeReact": [
            {"category": "FII/FPI *", "netValue": "-739.69", "date": "14-Jul-2026"},
            {"category": "DII **", "netValue": "2927.71", "date": "14-Jul-2026"},
        ]
    })
    flows = p.get_fii_dii_activity()
    assert flows["fii_net"] == -739.69
    assert flows["dii_net"] == 2927.71
    assert flows["date"] == "14-Jul-2026"


def test_delivery_parsing():
    p = _provider_returning({
        "quote-equity": {
            "securityWiseDP": {
                "deliveryToTradedQuantity": 62.5,
                "deliveryQuantity": 1250000,
                "quantityTraded": 2000000,
            }
        }
    })
    d = p.get_delivery_data("RELIANCE")
    assert d["delivery_percentage"] == 62.5
    assert d["delivery_volume"] == 1250000.0
    assert d["traded_volume"] == 2000000.0


def test_block_deal_sentiment_bullish():
    p = _provider_returning({
        "block-deal": {"data": [
            {"symbol": "RELIANCE", "buySell": "BUY"},
            {"symbol": "RELIANCE", "buySell": "BUY"},
            {"symbol": "RELIANCE", "buySell": "SELL"},
            {"symbol": "TCS", "buySell": "SELL"},
        ]}
    })
    assert p.get_block_deal_sentiment("RELIANCE") == "Bullish"
    assert p.get_block_deal_sentiment("TCS") == "Bearish"
    assert p.get_block_deal_sentiment("INFY") is None  # no deals for symbol


def test_graceful_degradation_on_network_failure():
    # _get_json returns None (as it does on any real failure) -> all None, no crash.
    p = NSEProvider()
    p._get_json = lambda path: None
    assert p.get_fii_dii_activity() is None
    assert p.get_delivery_data("RELIANCE") is None
    assert p.get_block_deals() is None
    assert p.get_block_deal_sentiment("RELIANCE") is None


def test_day_scoped_cache_avoids_refetch():
    calls = {"n": 0}

    def fake_get_json(path):
        calls["n"] += 1
        return [{"category": "FII", "netValue": "10", "date": "x"},
                {"category": "DII", "netValue": "20", "date": "x"}]

    p = NSEProvider()
    p._get_json = fake_get_json
    p.get_fii_dii_activity()
    p.get_fii_dii_activity()
    assert calls["n"] == 1  # second call served from the day cache
