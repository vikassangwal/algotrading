"""Volume Analysis — OBV, volume vs average, MFI, price-volume confirmation."""
import logging
import pandas as pd
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal
from .indicators import calculate_obv, calculate_mfi

logger = logging.getLogger("elco.module.volume")


class VolumeModule(AnalysisModule):
    name = "volume"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            candles = self.provider.get_candles(symbol, "1d", 250)
            if len(candles) < 30:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient candles for volume analysis."])
            df = pd.DataFrame([{"open": c.open, "high": c.high, "low": c.low,
                                "close": c.close, "volume": c.volume} for c in candles])
            reasons = []
            score = 0.0

            # --- OBV slope ---
            obv = calculate_obv(df)
            obv_slope = float(obv.iloc[-1] - obv.iloc[-6])
            if obv_slope > 0:
                score += 0.25; reasons.append("OBV rising — accumulation")
            else:
                score -= 0.25; reasons.append("OBV falling — distribution")

            # --- Volume vs 20-day average ---
            vol = df["volume"]
            avg = float(vol.iloc[-20:].mean())
            last_vol = float(vol.iloc[-1])
            ratio = last_vol / avg if avg > 0 else 1.0
            reasons.append(f"Latest volume {ratio:.2f}x of 20d avg")

            # --- Price-volume confirmation ---
            price_chg = float(df["close"].iloc[-1] - df["close"].iloc[-2])
            if price_chg > 0 and ratio > 1.2:
                score += 0.25; reasons.append("Up move on above-average volume (bullish confirmation)")
            elif price_chg > 0 and ratio < 0.8:
                score -= 0.1; reasons.append("Up move on weak volume (unconfirmed)")
            elif price_chg < 0 and ratio > 1.2:
                score -= 0.25; reasons.append("Down move on heavy volume (bearish)")

            # --- MFI ---
            mfi = calculate_mfi(df, 14).iloc[-1]
            if not pd.isna(mfi):
                mfi = float(mfi)
                if mfi > 80:
                    score -= 0.15; reasons.append(f"MFI {mfi:.0f} overbought")
                elif mfi < 20:
                    score += 0.15; reasons.append(f"MFI {mfi:.0f} oversold")
                else:
                    reasons.append(f"MFI {mfi:.0f}")

            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), 0.75, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
