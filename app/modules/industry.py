"""Industry analysis module — industry-level tailwind/headwind read.

Distinct from the sector module: this focuses on the narrower industry read —
theme momentum, policy support, structural entry barriers, industry breadth
(% of constituents above the 200DMA), relative strength vs Nifty, and FII flow
direction into the industry. Strong momentum + policy tailwinds + broad
participation -> bullish; weakness/outflows -> bearish.
"""
import logging

from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.industry")

_MOMENTUM_MAP = {
    "high": 1.0, "strong": 1.0, "positive": 0.6, "moderate": 0.2,
    "neutral": 0.0, "flat": 0.0, "low": -0.6, "weak": -0.6,
    "declining": -1.0, "negative": -1.0,
}
_POLICY_MAP = {
    "positive": 1.0, "supportive": 1.0, "favorable": 0.8, "neutral": 0.0,
    "mixed": 0.0, "negative": -1.0, "adverse": -1.0, "restrictive": -0.8,
}
_BARRIER_MAP = {
    "high": 1.0, "strong": 1.0, "medium": 0.3, "moderate": 0.3,
    "low": -0.5, "weak": -0.5, "none": -1.0,
}
_FLOW_MAP = {
    "buying": 1.0, "inflow": 1.0, "accumulation": 1.0, "neutral": 0.0,
    "balanced": 0.0, "selling": -1.0, "outflow": -1.0, "distribution": -1.0,
}


def _map(value, table, default=0.0) -> float:
    if value is None:
        return default
    return table.get(str(value).strip().lower(), default)


class IndustryModule(AnalysisModule):
    name = "industry"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            # Sector/industry data keyed by symbol (mock ignores the arg but the
            # signature requires it). This is the industry-structure slice.
            data = self.provider.get_sector_data(symbol) or {}

            reasons: list[str] = []
            components: list[float] = []   # each in [-1, +1], + = bullish
            data_points = 0

            # ---- 1. Theme / industry momentum -----------------------------
            theme = data.get("theme_momentum")
            if theme is not None:
                m = _map(theme, _MOMENTUM_MAP)
                components.append(m)
                data_points += 1
                reasons.append(f"Industry theme momentum '{theme}' -> {m:+.2f}")

            # ---- 2. Government policy support -----------------------------
            policy = data.get("government_policy_support")
            if policy is not None:
                p = _map(policy, _POLICY_MAP)
                components.append(p)
                data_points += 1
                reasons.append(f"Policy support '{policy}' -> {p:+.2f}")

            # ---- 3. Entry barriers (structural moat) ----------------------
            barriers = data.get("entry_barriers")
            if barriers is not None:
                b = _map(barriers, _BARRIER_MAP)
                components.append(b)
                data_points += 1
                reasons.append(f"Entry barriers '{barriers}' -> {b:+.2f}")

            # ---- 4. Relative strength vs Nifty ----------------------------
            rs = data.get("sector_rs_vs_nifty")
            if rs is not None:
                rsf = float(rs)
                # 1.0 = in line; scale +/-0.15 RS spread to full signal.
                rs_score = max(-1.0, min(1.0, (rsf - 1.0) / 0.15))
                components.append(rs_score)
                data_points += 1
                reasons.append(
                    f"Industry RS vs Nifty {rsf:.2f}x -> {rs_score:+.2f}"
                )

            # ---- 5. Breadth: % of stocks above 200DMA ---------------------
            breadth = data.get("stocks_above_200dma_pct")
            if breadth is not None:
                bp = float(breadth)
                # 50% = neutral; 85%+ broadly bullish, 20% broadly bearish.
                breadth_score = max(-1.0, min(1.0, (bp - 50.0) / 35.0))
                components.append(breadth_score)
                data_points += 1
                reasons.append(
                    f"{bp:.0f}% of industry above 200DMA -> {breadth_score:+.2f}"
                )

            # ---- 6. FII net flow into the industry ------------------------
            fii_flow = data.get("fii_sector_net_flow")
            if fii_flow is not None:
                f = _map(fii_flow, _FLOW_MAP)
                components.append(f)
                data_points += 1
                reasons.append(f"FII industry net flow '{fii_flow}' -> {f:+.2f}")

            if data_points == 0:
                return ModuleSignal(
                    self.name, 0.0, 0.15,
                    ["industry: no industry data available — neutral"],
                )

            score = sum(components) / len(components)
            score = max(-1.0, min(1.0, score))

            confidence = 0.30 + 0.10 * data_points   # 1 -> 0.40, 6 -> 0.90
            confidence = min(confidence, 0.90)

            if score >= 0.4:
                headline = (
                    f"INDUSTRY TAILWIND: strong momentum & participation "
                    f"(score {score:+.2f})"
                )
            elif score <= -0.4:
                headline = (
                    f"INDUSTRY HEADWIND: weak/declining industry (score {score:+.2f})"
                )
            else:
                headline = f"INDUSTRY NEUTRAL: mixed industry read (score {score:+.2f})"
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
