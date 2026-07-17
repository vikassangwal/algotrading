"""Alternative Data Analysis — web traffic, social buzz, dark-pool leading signals."""
import logging
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.alternative_data")


class AlternativeDataModule(AnalysisModule):
    name = "alternative_data"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            f = self.provider.get_fundamentals(symbol) or {}
            sent = self.provider.get_sentiment_data(symbol) or {}
            reasons = []
            score = 0.0

            # --- Web traffic growth (demand proxy) ---
            web = f.get("alt_data_web_traffic_growth")
            if web is not None:
                w = float(web)
                if w > 0.10:
                    score += 0.3; reasons.append(f"Web traffic growing +{w*100:.0f}% (demand up)")
                elif w < 0:
                    score -= 0.25; reasons.append(f"Web traffic declining {w*100:.0f}%")
                else:
                    reasons.append(f"Web traffic growth {w*100:.0f}%")

            # --- Social buzz ---
            buzz = sent.get("social_buzz_score")
            if buzz is not None:
                b = float(buzz)
                if b > 0.7:
                    score += 0.2; reasons.append(f"High social buzz ({b:.2f})")
                elif b < 0.3:
                    score -= 0.1; reasons.append(f"Low social buzz ({b:.2f})")

            # --- Dark-pool net flow (alt liquidity signal) ---
            dp_buy = float(sent.get("dark_pool_buy_volume", 0) or 0)
            dp_sell = float(sent.get("dark_pool_sell_volume", 0) or 0)
            if dp_buy + dp_sell > 0:
                imb = (dp_buy - dp_sell) / (dp_buy + dp_sell)
                if imb > 0.2:
                    score += 0.2; reasons.append(f"Dark-pool accumulation ({imb:+.2f})")
                elif imb < -0.2:
                    score -= 0.2; reasons.append(f"Dark-pool distribution ({imb:+.2f})")

            # --- News polarity as alt-signal ---
            pol = sent.get("news_polarity_score")
            if pol is not None:
                p = float(pol)
                if p > 0.3:
                    score += 0.1; reasons.append(f"Positive news polarity ({p:.2f})")
                elif p < -0.3:
                    score -= 0.1; reasons.append(f"Negative news polarity ({p:.2f})")

            if not reasons:
                return ModuleSignal(self.name, 0.0, 0.15, ["Insufficient alternative data."])
            return ModuleSignal(self.name, max(-1.0, min(1.0, score)), 0.6, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
