"""Behavioral finance module.

Reads crowd-psychology proxies (fear/greed, retail FOMO, social buzz, news
polarity) and applies a *contrarian* lens: crowd euphoria (extreme greed +
FOMO) is treated as a late-cycle warning, while crowd panic (extreme fear) is
treated as a mean-reversion opportunity. Every read is derived from provider
data only — no randomness, never raises.
"""
import logging

from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.behavioral")


class BehavioralModule(AnalysisModule):
    name = "behavioral"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            data = {}
            if hasattr(self.provider, "get_sentiment_data"):
                data = self.provider.get_sentiment_data(symbol) or {}

            # --- Extract crowd-psychology proxies (with safe defaults) ---
            fgi = float(data.get("fear_greed_index", 50) or 50)          # 0..100
            fomo = bool(data.get("retail_fomo_flag", False))
            buzz = float(data.get("social_buzz_score", 0.0) or 0.0)      # 0..1
            polarity = float(data.get("news_polarity_score", 0.0) or 0.0)  # -1..1

            fgi = max(0.0, min(100.0, fgi))
            buzz = max(0.0, min(1.0, buzz))
            polarity = max(-1.0, min(1.0, polarity))

            reasons = []
            score = 0.0

            # --- 1. Fear & Greed: the contrarian backbone ---
            # 50 = neutral. Greed (>50) -> contrarian bearish, fear (<50) -> bullish.
            fgi_score = (50.0 - fgi) / 50.0            # +1 max-fear .. -1 max-greed
            score += fgi_score * 0.55
            if fgi >= 75:
                bias = "EXTREME GREED"
                reasons.append(
                    f"Fear/Greed at {fgi:.0f} — {bias}: crowd euphoria, contrarian bearish caution."
                )
            elif fgi <= 25:
                bias = "EXTREME FEAR"
                reasons.append(
                    f"Fear/Greed at {fgi:.0f} — {bias}: crowd panic, contrarian bullish opportunity."
                )
            elif fgi >= 60:
                reasons.append(f"Fear/Greed at {fgi:.0f} — greed building, mild contrarian caution.")
            elif fgi <= 40:
                reasons.append(f"Fear/Greed at {fgi:.0f} — fear building, mild contrarian support.")
            else:
                reasons.append(f"Fear/Greed at {fgi:.0f} — neutral crowd positioning.")

            # --- 2. Retail FOMO flag: euphoric chasing = crowded long ---
            if fomo:
                score -= 0.18
                reasons.append(
                    "Retail FOMO flag ON — herding into longs; late-money crowding is a fade signal."
                )
            else:
                reasons.append("Retail FOMO flag OFF — no euphoric retail chase detected.")

            # --- 3. Social buzz amplifies whichever extreme is in play ---
            if buzz >= 0.7:
                if fgi >= 60:
                    score -= buzz * 0.20
                    reasons.append(
                        f"Social buzz very high ({buzz:.2f}) into greed — crowded narrative, contrarian bearish."
                    )
                elif fgi <= 40:
                    score += buzz * 0.15
                    reasons.append(
                        f"Social buzz very high ({buzz:.2f}) into fear — capitulation chatter, contrarian bullish."
                    )
                else:
                    reasons.append(f"Social buzz elevated ({buzz:.2f}) but crowd mood neutral.")
            else:
                reasons.append(f"Social buzz moderate ({buzz:.2f}) — no attention-driven mispricing.")

            # --- 4. News polarity vs positioning: euphoria confirmation ---
            if polarity >= 0.5 and fgi >= 65:
                score -= 0.10
                reasons.append(
                    f"News polarity strongly positive ({polarity:+.2f}) amid greed — good news fully priced in."
                )
            elif polarity <= -0.5 and fgi <= 35:
                score += 0.10
                reasons.append(
                    f"News polarity strongly negative ({polarity:+.2f}) amid fear — bad news likely exhausted."
                )

            score = max(-1.0, min(1.0, score))

            # --- Confidence: high when the crowd is at an extreme (clear signal) ---
            extremity = abs(fgi - 50.0) / 50.0        # 0 neutral .. 1 extreme
            confidence = 0.35 + extremity * 0.55
            if fomo and buzz >= 0.7:
                confidence += 0.05                     # corroborating euphoria signals
            confidence = max(0.0, min(1.0, confidence))

            headline = (
                "BEHAVIORAL: contrarian BEARISH (crowd greed)" if score <= -0.15
                else "BEHAVIORAL: contrarian BULLISH (crowd fear)" if score >= 0.15
                else "BEHAVIORAL: crowd mood neutral"
            )
            reasons.insert(0, f"{headline} — net score {score:+.2f}")

            return ModuleSignal(self.name, round(score, 2), round(confidence, 2), reasons)

        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
