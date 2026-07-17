"""Cycle Analysis — business-cycle phase + price-cycle position."""
import logging
import pandas as pd
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.cycle")


class CycleModule(AnalysisModule):
    name = "cycle"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            reasons = []
            score = 0.0

            # --- Business cycle phase (macro) ---
            macro = self.provider.get_macro_data() or {}
            phase = str(macro.get("business_cycle_phase", "")).lower()
            if "expansion" in phase or "recovery" in phase:
                score += 0.3; reasons.append(f"Business cycle in {phase} (favourable)")
            elif "slowdown" in phase or "contraction" in phase or "recession" in phase:
                score -= 0.3; reasons.append(f"Business cycle in {phase} (headwind)")
            else:
                reasons.append(f"Business cycle phase: {phase or 'unknown'}")

            # --- Price cycle position from candles ---
            candles = self.provider.get_candles(symbol, "1d", 250)
            if len(candles) >= 60:
                close = pd.Series([c.close for c in candles])
                hi = float(close.max())
                lo = float(close.min())
                last = float(close.iloc[-1])
                if hi > lo:
                    pos = (last - lo) / (hi - lo)  # 0 = at cycle low, 1 = at cycle high
                    reasons.append(f"Price at {pos*100:.0f}% of 250d range")
                    if pos < 0.35:
                        score += 0.2; reasons.append("Near cycle low — mean-reversion upside")
                    elif pos > 0.85:
                        score -= 0.2; reasons.append("Near cycle high — late-cycle caution")

                # trend maturity: slope of last 20 vs prior 20
                if len(close) >= 40:
                    recent = close.iloc[-20:].mean()
                    prior = close.iloc[-40:-20].mean()
                    if recent > prior:
                        score += 0.1; reasons.append("Uptrend intact")
                    else:
                        score -= 0.1; reasons.append("Momentum fading")

            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), 0.6, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
