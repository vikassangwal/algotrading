"""Broker adapter stubs — pick one in Admin Panel, add keys, implement later.

Each real adapter must subclass DataProvider (and later OrderRouter).
They intentionally raise until credentials + SDK wiring are added:
  - Zerodha Kite:  pip install kiteconnect
  - Upstox:        pip install upstox-python-sdk
  - Angel One:     pip install smartapi-python
  - Fyers:         pip install fyers-apiv3
"""
from __future__ import annotations

from ..config import BrokerName
from .mock_provider import MockProvider
from .provider import DataProvider


class _NotWiredProvider(DataProvider):
    name = "unwired"

    def _fail(self):
        raise NotImplementedError(
            f"{self.name} adapter is not wired yet. Add API keys in the Admin Panel "
            "and implement the SDK calls in app/data/brokers.py."
        )

    def get_quote(self, symbol):        self._fail()
    def get_candles(self, symbol, timeframe, count):  self._fail()
    def get_option_chain(self, symbol): self._fail()
    def get_news(self, limit=20):       self._fail()
    def get_fundamentals(self, symbol): self._fail()
    def get_sentiment_buzz(self, symbol): self._fail()


class ZerodhaProvider(_NotWiredProvider):  name = "zerodha"
class UpstoxProvider(_NotWiredProvider):   name = "upstox"
class AngelOneProvider(_NotWiredProvider): name = "angel_one"
class FyersProvider(_NotWiredProvider):    name = "fyers"
class MStockProvider(_NotWiredProvider):   name = "mstock"      # mStock Trading API (Mirae Asset)
class KotakNeoProvider(_NotWiredProvider): name = "kotak_neo"   # Kotak Neo Trading API


def make_provider(broker: BrokerName) -> DataProvider:
    if broker == BrokerName.DHAN:
        # Real Dhan provider (yfinance quotes + gated live order routing).
        from .dhan_provider import DhanProvider
        return DhanProvider()
    return {
        BrokerName.MOCK: MockProvider,
        BrokerName.ZERODHA: ZerodhaProvider,
        BrokerName.UPSTOX: UpstoxProvider,
        BrokerName.ANGEL_ONE: AngelOneProvider,
        BrokerName.FYERS: FyersProvider,
        BrokerName.MSTOCK: MStockProvider,
        BrokerName.KOTAK_NEO: KotakNeoProvider,
    }[broker]()
