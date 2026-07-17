"""ESG analysis module — governance-quality read as a directional signal.

Full ESG scoring needs external environmental/social datasets that the mock
provider does not expose. We therefore read the available GOVERNANCE proxies
from fundamentals — auditor opinion (clean vs qualified) and promoter share
pledging — and treat clean governance as a mild bullish quality premium and
governance red flags as bearish. Confidence is kept modest because these are
proxies, not a full ESG rating.
"""
import logging

from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.esg")


class ESGModule(AnalysisModule):
    name = "esg"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            fund = self.provider.get_fundamentals(symbol) or {}

            reasons: list[str] = []
            components: list[float] = []   # each in [-1, +1], + = good governance
            data_points = 0

            reasons.append(
                "ESG proxy read: governance signals only (audit opinion, "
                "promoter pledge) — environmental/social data unavailable"
            )

            # ---- 1. Auditor opinion (governance red flag) -----------------
            qualified = fund.get("auditor_qualified_opinion")
            if qualified is not None:
                if bool(qualified):
                    g = -1.0
                    reasons.append(
                        "Auditor issued a QUALIFIED opinion -> serious governance "
                        f"red flag ({g:+.2f})"
                    )
                else:
                    g = 0.5
                    reasons.append(
                        f"Auditor clean/unqualified opinion -> governance positive ({g:+.2f})"
                    )
                components.append(g)
                data_points += 1

            # ---- 2. Promoter share pledge --------------------------------
            pledge = fund.get("promoter_pledge_pct")
            if pledge is not None:
                pf = float(pledge)
                # Values may be a fraction (0.05) or a percentage (5.0). Normalize.
                pledge_frac = pf / 100.0 if pf > 1.0 else pf
                # 0% pledge -> +0.5 clean; 25%+ pledge -> -1.0 high risk.
                p_score = max(-1.0, min(0.5, 0.5 - (pledge_frac / 0.25) * 1.5))
                components.append(p_score)
                data_points += 1
                reasons.append(
                    f"Promoter pledge {pledge_frac * 100:.1f}% of holding -> {p_score:+.2f}"
                )

            # ---- 3. Beneish M-score (earnings-manipulation governance) ----
            m_score = fund.get("beneish_m_score")
            if m_score is not None:
                mf = float(m_score)
                # Beneish: > -1.78 flags likely manipulation; lower is cleaner.
                if mf > -1.78:
                    b = -0.8
                    reasons.append(
                        f"Beneish M-score {mf:.2f} above -1.78 -> earnings-quality flag ({b:+.2f})"
                    )
                else:
                    b = 0.4
                    reasons.append(
                        f"Beneish M-score {mf:.2f} below -1.78 -> clean earnings quality ({b:+.2f})"
                    )
                components.append(b)
                data_points += 1

            if data_points == 0:
                return ModuleSignal(
                    self.name, 0.0, 0.15,
                    ["esg: no governance proxies available — neutral"],
                )

            score = sum(components) / len(components)
            score = max(-1.0, min(1.0, score))

            # Modest confidence: proxies only, no full ESG dataset.
            confidence = 0.25 + 0.10 * data_points   # 1 -> 0.35, 3 -> 0.55
            confidence = min(confidence, 0.55)

            if score >= 0.35:
                headline = (
                    f"GOVERNANCE PREMIUM: clean governance proxies -> mild bullish "
                    f"quality tilt (score {score:+.2f})"
                )
            elif score <= -0.35:
                headline = (
                    f"GOVERNANCE RISK: red flags in governance proxies -> bearish "
                    f"(score {score:+.2f})"
                )
            else:
                headline = (
                    f"GOVERNANCE NEUTRAL: mixed governance proxies (score {score:+.2f})"
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
