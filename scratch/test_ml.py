import logging
logging.basicConfig(level=logging.DEBUG)

from app.data.mock_provider import MockProvider
from app.modules.quant import QuantModule

provider = MockProvider()
mod = QuantModule(provider)

res = mod.analyze("RELIANCE")
for r in res.reasons:
    print(r)
