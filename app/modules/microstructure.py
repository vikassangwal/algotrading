"""Market microstructure — HONEST version.

The old engine fabricated a random L2 order book and fed fake
"institutional walls" downstream. Real L2 depth needs a live depth feed
(Dhan full-packet mode) which is not wired yet — so this module now returns
ONLY what daily OHLCV can honestly support, each figure labeled as the
model estimate it is:

  * Bid-ask spread   — Corwin-Schultz (2012) high-low estimator, a
                       published academic method for estimating spreads
                       from OHLC data. An ESTIMATE, labeled as such.
  * Liquidity        — real 20-day average turnover.
  * Slippage         — square-root market-impact model (standard
                       institutional pre-trade cost model) from real
                       volatility + real participation rate.
  * Order book / imbalance — available: False. Never simulated.
"""
import logging
import math
from typing import Any, Dict

import numpy as np

logger = logging.getLogger("elco.module.microstructure")


class MicrostructureEngine:
    def __init__(self, provider):
        self.provider = provider

    # -- estimators ----------------------------------------------------------

    @staticmethod
    def corwin_schultz_spread(high: np.ndarray, low: np.ndarray) -> float:
        """Corwin-Schultz high-low spread estimator over recent bars.
        Returns the estimated proportional spread (e.g. 0.0008 = 8 bps)."""
        h, l = np.asarray(high, float), np.asarray(low, float)
        n = min(len(h), len(l))
        if n < 21:
            return 0.0
        h, l = h[-21:], l[-21:]
        spreads = []
        for i in range(1, len(h)):
            if min(h[i - 1], h[i], l[i - 1], l[i]) <= 0:
                continue
            beta = (math.log(h[i - 1] / l[i - 1])) ** 2 + (math.log(h[i] / l[i])) ** 2
            hh, ll = max(h[i - 1], h[i]), min(l[i - 1], l[i])
            gamma = (math.log(hh / ll)) ** 2
            denom = 3 - 2 * math.sqrt(2)
            alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / denom - math.sqrt(gamma / denom)
            s = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
            spreads.append(max(s, 0.0))
        return float(np.mean(spreads)) if spreads else 0.0

    @staticmethod
    def sqrt_impact_bps(order_value: float, daily_turnover: float,
                        daily_vol_pct: float) -> float:
        """Square-root market-impact model: cost ≈ σ · sqrt(Q/V).
        Standard institutional pre-trade estimate — a MODEL, not a quote."""
        if daily_turnover <= 0 or order_value <= 0:
            return 0.0
        participation = order_value / daily_turnover
        return round(daily_vol_pct * 100.0 * math.sqrt(participation), 2)  # bps

    # -- public --------------------------------------------------------------

    def analyze(self, symbol: str, current_price: float,
                order_value: float = 100000.0) -> Dict[str, Any]:
        """Honest microstructure estimates from real daily bars."""
        try:
            candles = self.provider.get_candles(symbol, "1d", 40)
            if not candles or len(candles) < 21:
                return {"symbol": symbol, "available": False,
                        "error": "not enough daily bars for estimates"}

            high = np.array([c.high for c in candles], float)
            low = np.array([c.low for c in candles], float)
            close = np.array([c.close for c in candles], float)
            volume = np.array([c.volume for c in candles], float)

            spread = self.corwin_schultz_spread(high, low)
            turnover = float((close[-20:] * volume[-20:]).mean())
            rets = np.diff(np.log(close[-21:]))
            daily_vol = float(np.std(rets))
            impact_bps = self.sqrt_impact_bps(order_value, turnover, daily_vol)

            return {
                "symbol": symbol,
                "estimated_spread_bps": round(spread * 1e4, 2),
                "spread_method": "Corwin-Schultz high-low estimator (model, not L2 quote)",
                "avg_daily_turnover": round(turnover, 0),
                "turnover_cr": round(turnover / 1e7, 2),
                "daily_volatility_pct": round(daily_vol * 100, 2),
                "estimated_impact_bps": impact_bps,
                "impact_model": f"square-root impact for a ₹{order_value:,.0f} order (model)",
                "order_book": None,
                "order_book_imbalance": None,
                "l2_note": (
                    "Real L2 depth/imbalance requires a live depth feed "
                    "(Dhan full-packet mode) — reported as unavailable, "
                    "never simulated."
                ),
                "available": True,
            }
        except Exception as e:
            logger.error(f"Microstructure estimates failed for {symbol}: {e}")
            return {"symbol": symbol, "available": False, "error": str(e)}
