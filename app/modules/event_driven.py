"""Event-driven module.

Scans recent news headlines for positive vs negative catalysts, weighs whether
today is a major event day / news-volume spike (which amplifies event impact),
and blends in an earnings signal from fundamentals (EPS growth). Produces a net
catalyst score for the symbol. Provider-only, deterministic, never raises.
"""
import logging

from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.event_driven")

# Keyword catalyst lexicon — scanned case-insensitively against headlines.
_POSITIVE_KW = (
    "beat", "beats", "upgrade", "upgraded", "rally", "rallies", "growth", "surge",
    "surges", "record", "profit", "gains", "jump", "jumps", "outperform", "buyback",
    "expansion", "wins", "approval", "raises", "hikes guidance",
)
_NEGATIVE_KW = (
    "slide", "slides", "cut", "cuts", "fraud", "tension", "tensions", "downgrade",
    "downgraded", "miss", "misses", "slump", "plunge", "plunges", "loss", "probe",
    "fine", "default", "warning", "halt", "recall", "selling", "low", "crisis",
)


class EventDrivenModule(AnalysisModule):
    name = "event_driven"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            sym = (symbol or "").upper()

            # --- News headlines ---
            try:
                news = self.provider.get_news(20) or []
            except Exception:
                news = []

            # --- Sentiment/event context ---
            sent = {}
            if hasattr(self.provider, "get_sentiment_data"):
                sent = self.provider.get_sentiment_data(symbol) or {}
            is_event_day = bool(sent.get("is_major_event_day", False))
            vol_spike = float(sent.get("news_volume_spike", 1.0) or 1.0)

            # --- Fundamentals earnings signal ---
            fund = {}
            if hasattr(self.provider, "get_fundamentals"):
                fund = self.provider.get_fundamentals(symbol) or {}
            eps_growth = float(fund.get("eps_growth_yoy", 0.0) or 0.0)

            reasons = []

            # --- 1. Keyword-scan headlines for catalysts ---
            pos_hits, neg_hits, scanned = 0, 0, 0
            sample_pos, sample_neg = None, None
            for item in news:
                headline = getattr(item, "headline", "") or ""
                hl = headline.lower()
                # Prefer symbol-tagged news but headlines here are market-wide.
                tags = [t.upper() for t in (getattr(item, "symbols", None) or [])]
                if tags and sym and sym not in tags:
                    continue
                scanned += 1
                p = sum(1 for kw in _POSITIVE_KW if kw in hl)
                n = sum(1 for kw in _NEGATIVE_KW if kw in hl)
                if p > n:
                    pos_hits += 1
                    if sample_pos is None:
                        sample_pos = headline
                elif n > p:
                    neg_hits += 1
                    if sample_neg is None:
                        sample_neg = headline

            total_hits = pos_hits + neg_hits
            if total_hits > 0:
                catalyst_score = (pos_hits - neg_hits) / total_hits   # -1..+1
            else:
                catalyst_score = 0.0

            reasons.append(
                f"Scanned {scanned} headlines — {pos_hits} positive vs {neg_hits} negative catalysts "
                f"(net {catalyst_score:+.2f})."
            )
            if sample_pos:
                reasons.append(f"Bullish catalyst: \"{sample_pos}\"")
            if sample_neg:
                reasons.append(f"Bearish catalyst: \"{sample_neg}\"")
            if total_hits == 0:
                reasons.append("No keyword catalysts detected in the recent news flow.")

            # --- 2. Earnings signal from fundamentals ---
            if eps_growth >= 0.10:
                earn_score = min(eps_growth, 0.5) / 0.5   # scale up to +1
                reasons.append(f"EPS growth YoY {eps_growth*100:.0f}% — positive earnings catalyst.")
            elif eps_growth <= -0.05:
                earn_score = max(eps_growth, -0.5) / 0.5
                reasons.append(f"EPS growth YoY {eps_growth*100:.0f}% — negative earnings catalyst.")
            else:
                earn_score = 0.0
                reasons.append(f"EPS growth YoY {eps_growth*100:.0f}% — flat, no earnings catalyst.")

            # --- 3. Blend: headlines lead (0.7), earnings support (0.3) ---
            score = catalyst_score * 0.70 + earn_score * 0.30

            # --- 4. Event-day / volume-spike amplification ---
            amp = 1.0
            if is_event_day:
                amp += 0.25
                reasons.append("Major event day flagged — catalyst impact amplified.")
            if vol_spike >= 1.4:
                amp += min((vol_spike - 1.0) * 0.5, 0.35)
                reasons.append(f"News-volume spike x{vol_spike:.1f} — heightened event risk/opportunity.")
            score = max(-1.0, min(1.0, score * amp))

            # --- Confidence: more catalysts + event context => higher trust ---
            confidence = 0.30 + min(total_hits, 5) * 0.08
            if is_event_day:
                confidence += 0.10
            if vol_spike >= 1.4:
                confidence += 0.05
            if total_hits == 0 and abs(earn_score) < 0.2:
                confidence = min(confidence, 0.30)   # nothing concrete to trade
            confidence = max(0.0, min(1.0, confidence))

            headline = (
                "EVENT-DRIVEN: net BULLISH catalysts" if score >= 0.15
                else "EVENT-DRIVEN: net BEARISH catalysts" if score <= -0.15
                else "EVENT-DRIVEN: mixed / no clear catalyst"
            )
            reasons.insert(0, f"{headline} — net score {score:+.2f}")

            return ModuleSignal(self.name, round(score, 2), round(confidence, 2), reasons)

        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
