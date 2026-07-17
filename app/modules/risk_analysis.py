"""Risk analysis module — downside-risk read as a directional signal.

This is an ANALYSIS signal (risk-on / risk-off tilt), NOT the risk_manager.
It reads tail-risk and volatility estimates from the quant provider plus
realized volatility computed from daily candles, and maps elevated downside
risk to a bearish (risk-off) tilt and contained risk to a mild bullish tilt.
"""
import logging

import numpy as np
import pandas as pd

from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.risk_analysis")


class RiskAnalysisModule(AnalysisModule):
    name = "risk_analysis"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            quant = self.provider.get_quant_data(symbol) or {}

            reasons: list[str] = []
            components: list[float] = []   # each in [-1, +1], + = risk-off/bearish
            data_points = 0

            # ---- 1. Value at Risk (95%) -----------------------------------
            # var_95_pct is a negative return (e.g. -0.04 = -4% daily loss tail).
            var_95 = quant.get("var_95_pct")
            if var_95 is not None:
                var_mag = abs(float(var_95))
                # 2% loss -> mild, 6%+ -> severe. Scale into [0, 1].
                var_risk = min(var_mag / 0.06, 1.0)
                components.append(var_risk)
                data_points += 1
                reasons.append(
                    f"VaR(95%) daily tail loss {float(var_95) * 100:.1f}% "
                    f"-> risk load {var_risk:.2f}"
                )

            # ---- 2. Conditional VaR / Expected Shortfall ------------------
            cvar_95 = quant.get("cvar_95_pct")
            if cvar_95 is not None:
                cvar_mag = abs(float(cvar_95))
                # ES beyond the tail; 3% -> mild, 8%+ -> severe.
                cvar_risk = min(cvar_mag / 0.08, 1.0)
                components.append(cvar_risk)
                data_points += 1
                reasons.append(
                    f"CVaR(95%) expected shortfall {float(cvar_95) * 100:.1f}% "
                    f"-> risk load {cvar_risk:.2f}"
                )

            # ---- 3. GARCH forecast volatility -----------------------------
            garch_vol = quant.get("garch_vol_forecast")
            if garch_vol is not None:
                gv = abs(float(garch_vol))
                # daily sigma: 1% calm, 3%+ stressed.
                garch_risk = min(gv / 0.03, 1.0)
                components.append(garch_risk)
                data_points += 1
                reasons.append(
                    f"GARCH forecast vol {gv * 100:.1f}%/day -> risk load {garch_risk:.2f}"
                )

            # ---- 4. Realized volatility from candles -----------------------
            realized_vol = None
            try:
                candles = self.provider.get_candles(symbol, "1d", 60) or []
                if len(candles) >= 20:
                    closes = pd.Series([c.close for c in candles], dtype="float64")
                    rets = closes.pct_change().dropna()
                    if len(rets) >= 15:
                        realized_vol = float(rets.std())
            except Exception as e:
                logger.warning(f"{self.name}: realized-vol calc failed on {symbol}: {e}")

            if realized_vol is not None and np.isfinite(realized_vol):
                rv_risk = min(realized_vol / 0.03, 1.0)
                components.append(rv_risk)
                data_points += 1
                reasons.append(
                    f"Realized vol (60d) {realized_vol * 100:.1f}%/day -> risk load {rv_risk:.2f}"
                )

            # ---- 5. Price z-score extension (stretched = fragile) ---------
            z = quant.get("price_z_score")
            if z is not None:
                zf = float(z)
                # |z| >= 2 is stretched and fragile in either direction.
                z_risk = min(abs(zf) / 2.5, 1.0)
                components.append(z_risk)
                data_points += 1
                reasons.append(
                    f"Price z-score {zf:+.2f} -> extension/fragility load {z_risk:.2f}"
                )

            if data_points == 0:
                return ModuleSignal(
                    self.name, 0.0, 0.15,
                    ["risk_analysis: no risk metrics available — neutral"],
                )

            # Aggregate risk load in [0, 1]; higher = more downside risk.
            risk_load = float(np.mean(components))

            # Map risk load to a directional score.
            # Low risk (load ~0.2) -> mild bullish (risk-on).
            # High risk (load ~1.0) -> bearish (risk-off).
            # Neutral pivot at 0.35: below is risk-on, above is risk-off.
            score = float((0.35 - risk_load) / 0.65)
            score = max(-1.0, min(1.0, score))

            # Confidence scales with how many independent metrics we had.
            confidence = 0.30 + 0.12 * data_points   # 1 -> 0.42, 5 -> 0.90
            confidence = min(confidence, 0.90)

            if risk_load >= 0.66:
                headline = (
                    f"RISK-OFF: elevated downside risk (load {risk_load:.2f}) -> "
                    f"bearish tilt {score:+.2f}"
                )
            elif risk_load <= 0.35:
                headline = (
                    f"RISK-ON: contained downside risk (load {risk_load:.2f}) -> "
                    f"mild bullish tilt {score:+.2f}"
                )
                confidence = min(confidence + 0.05, 0.90)
            else:
                headline = (
                    f"BALANCED RISK: moderate downside risk (load {risk_load:.2f}) -> "
                    f"tilt {score:+.2f}"
                )
            reasons.insert(0, headline)

            return ModuleSignal(
                module=self.name,
                score=round(score, 2),
                confidence=round(confidence, 2),
                reasons=reasons[:6],
            )
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
