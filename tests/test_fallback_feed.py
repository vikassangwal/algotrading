"""Offline tests for the no-Dhan fallback quote chain (BSE/NSE pollers)."""
from unittest.mock import patch

from app.data.live_feed import FallbackPoller, LiveTickCache, DhanLiveFeed


def _mk():
    cache = LiveTickCache()
    feed = DhanLiveFeed(cache)
    return cache, FallbackPoller(cache, feed)


def test_subscribe_normalizes_symbols():
    _, fp = _mk()
    fp.subscribe(["reliance", " ITC ", ""])
    assert fp.status()["subscribed"] == ["ITC", "RELIANCE"]


def test_poll_writes_bse_equity_and_nse_index_ticks():
    cache, fp = _mk()
    fp.subscribe(["RELIANCE", "NIFTY"])

    fake_bse = {"RELIANCE": {"symbol": "RELIANCE", "ltp": 1326.5, "change_pct": 2.59,
                             "source": "bse_web", "delayed": False, "time": 1.0}}
    fake_nse = {"data": [{"index": "NIFTY 50", "last": 24334.3,
                          "percentChange": 1.09, "previousClose": 24071.9}]}

    with patch("app.data.bse_provider.bse_provider.get_many", return_value=fake_bse), \
         patch("app.data.nse_provider.nse_provider._get_json", return_value=fake_nse):
        fp._poll(["RELIANCE", "NIFTY"])

    rel = cache.get("RELIANCE")
    assert rel["ltp"] == 1326.5 and rel["source"] == "bse_web"
    nif = cache.get("NIFTY")
    assert nif["ltp"] == 24334.3 and nif["source"] == "nse_web"


def test_dhan_ticks_are_never_overwritten():
    """Real ticks win: a fresh Dhan tick must not be clobbered by the poller."""
    import time as _t
    cache, fp = _mk()
    cache.put("RELIANCE", {"symbol": "RELIANCE", "ltp": 1330.0,
                           "source": "dhan", "time": _t.time()})

    fake_bse = {"RELIANCE": {"symbol": "RELIANCE", "ltp": 1326.5,
                             "source": "bse_web", "delayed": False, "time": 1.0}}
    with patch("app.data.bse_provider.bse_provider.get_many", return_value=fake_bse), \
         patch("app.data.nse_provider.nse_provider._get_json", return_value=None):
        fp._poll(["RELIANCE"])

    assert cache.get("RELIANCE")["source"] == "dhan"  # untouched
    assert cache.get("RELIANCE")["ltp"] == 1330.0


def test_stale_dhan_tick_gets_replaced():
    """A Dhan tick older than DHAN_FRESH_SEC is stale — fallback takes over."""
    cache, fp = _mk()
    cache.put("RELIANCE", {"symbol": "RELIANCE", "ltp": 1330.0,
                           "source": "dhan", "time": 100.0})  # ancient

    fake_bse = {"RELIANCE": {"symbol": "RELIANCE", "ltp": 1326.5,
                             "source": "bse_web", "delayed": False, "time": 1.0}}
    with patch("app.data.bse_provider.bse_provider.get_many", return_value=fake_bse), \
         patch("app.data.nse_provider.nse_provider._get_json", return_value=None):
        fp._poll(["RELIANCE"])

    assert cache.get("RELIANCE")["source"] == "bse_web"


def test_provider_failure_is_swallowed_not_fatal():
    cache, fp = _mk()
    fp.subscribe(["RELIANCE"])
    with patch("app.data.bse_provider.bse_provider.get_many", side_effect=RuntimeError("down")), \
         patch("app.data.nse_provider.nse_provider._get_json", side_effect=RuntimeError("down")):
        fp._poll(["RELIANCE", "NIFTY"])  # must not raise
    assert cache.get("RELIANCE") is None  # and must not invent data
