import pandas as pd
import numpy as np
import logging

from .indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_supertrend,
    calculate_mfi,
    calculate_obv,
)

logger = logging.getLogger("elco.module.ai_composite")


class AICompositeEngine:
    """Composite technical scorer.

    Every sub-score is derived from a REAL indicator on the supplied OHLCV
    frame — no random numbers. Scores are 0-100 where 50 is neutral, >50 is
    bullish, <50 is bearish. The frame must be time-ordered oldest->newest and
    is used as-of its last row, so passing a truncated (as-of-date) frame keeps
    the backtester free of look-ahead bias.
    """

    def __init__(self, df: pd.DataFrame, options_data: dict = None, order_flow_data: dict = None):
        self.df = df
        self.options_data = options_data or {}
        self.order_flow_data = order_flow_data or {}

    def calculate_scores(self) -> dict:
        if self.df is None or self.df.empty or len(self.df) < 20:
            return self._default_scores()

        trend_score = self._calc_trend_score()
        momentum_score = self._calc_momentum_score()
        volume_score = self._calc_volume_score()
        volatility_score = self._calc_volatility_score()
        smart_money_score = self._calc_smart_money_score()
        options_score = self._calc_options_score()
        risk_score = self._calc_risk_score(volatility_score)

        # Weighted average: Trend 25, Momentum 20, Volume 15, Smart Money 15,
        # Volatility 10, Options 15.
        composite_raw = (
            trend_score * 0.25
            + momentum_score * 0.20
            + volume_score * 0.15
            + smart_money_score * 0.15
            + volatility_score * 0.10
            + options_score * 0.15
        )

        probability_pct = int(round(composite_raw))
        probability_pct = max(0, min(100, probability_pct))

        if probability_pct >= 80:
            action = "Strong Buy"
        elif probability_pct >= 60:
            action = "Buy"
        elif probability_pct <= 20:
            action = "Strong Sell"
        elif probability_pct <= 40:
            action = "Sell"
        else:
            action = "Hold"

        confidence_pct = max(10, min(100, int(abs(probability_pct - 50) * 2)))

        # ATR-based trade setup off the last close.
        last_close = float(self.df['close'].iloc[-1])
        atr = self._atr()
        if atr <= 0:
            atr = last_close * 0.01

        if action in ["Strong Buy", "Buy"]:
            entry = last_close
            sl = entry - (atr * 4.0)
            t1 = entry + (atr * 0.25)
            t2 = entry + (atr * 0.5)
        elif action in ["Strong Sell", "Sell"]:
            entry = last_close
            sl = entry + (atr * 4.0)
            t1 = entry - (atr * 0.25)
            t2 = entry - (atr * 0.5)
        else:
            entry = last_close
            sl = last_close - (atr * 4.0)
            t1 = last_close + (atr * 0.25)
            t2 = last_close + (atr * 0.5)

        return {
            "action": action,
            "confidence_pct": confidence_pct,
            "probability_pct": probability_pct,
            "risk_score": int(round(risk_score)),
            "sub_scores": {
                "trend": int(round(trend_score)),
                "momentum": int(round(momentum_score)),
                "volume": int(round(volume_score)),
                "volatility": int(round(volatility_score)),
                "smart_money": int(round(smart_money_score)),
                "options": int(round(options_score)),
                "risk": int(round(risk_score)),
            },
            "trade_setup": {
                "entry": round(entry, 2),
                "stop_loss": round(sl, 2),
                "target_1": round(t1, 2),
                "target_2": round(t2, 2),
            },
        }

    # ---- real indicator-based sub-scores ----

    def _calc_trend_score(self) -> float:
        """EMA 20/50/200 alignment + Supertrend direction. 0-100."""
        close = self.df['close']
        last = float(close.iloc[-1])
        score = 50.0

        ema20 = float(calculate_ema(close, 20).iloc[-1])
        ema50 = float(calculate_ema(close, 50).iloc[-1]) if len(close) >= 50 else ema20
        ema200 = float(calculate_ema(close, 200).iloc[-1]) if len(close) >= 200 else ema50

        # Price above each EMA and bullish EMA stack each add weight.
        if last > ema20:
            score += 8
        else:
            score -= 8
        if ema20 > ema50:
            score += 8
        else:
            score -= 8
        if ema50 > ema200:
            score += 9
        else:
            score -= 9

        # Supertrend direction (+1 uptrend, -1 downtrend)
        try:
            st = calculate_supertrend(self.df)
            if float(st['Direction'].iloc[-1]) > 0:
                score += 15
            else:
                score -= 15
        except Exception:
            pass

        return max(0.0, min(100.0, score))

    def _calc_momentum_score(self) -> float:
        """RSI mapped to 0-100 momentum, blended with short rate-of-change."""
        close = self.df['close']
        rsi = calculate_rsi(close, 14).iloc[-1]
        rsi = 50.0 if pd.isna(rsi) else float(rsi)

        # Rate of change over ~10 bars, scaled into +/-25 around neutral.
        if len(close) > 10:
            roc = (float(close.iloc[-1]) / float(close.iloc[-11]) - 1.0) * 100.0
        else:
            roc = 0.0
        roc_score = 50.0 + max(-25.0, min(25.0, roc * 2.5))

        # RSI already 0-100; average with roc component.
        return max(0.0, min(100.0, 0.6 * rsi + 0.4 * roc_score))

    def _calc_volume_score(self) -> float:
        """OBV slope + latest volume vs 20-bar average."""
        if 'volume' not in self.df.columns or self.df['volume'].sum() == 0:
            return 50.0
        score = 50.0
        obv = calculate_obv(self.df)
        if len(obv) > 5:
            recent = float(obv.iloc[-1] - obv.iloc[-6])
            score += 15 if recent > 0 else -15

        vol = self.df['volume']
        avg = float(vol.iloc[-20:].mean()) if len(vol) >= 20 else float(vol.mean())
        if avg > 0:
            ratio = float(vol.iloc[-1]) / avg
            # Above-average volume confirms; scale into +/-15.
            score += max(-15.0, min(15.0, (ratio - 1.0) * 15.0))
        return max(0.0, min(100.0, score))

    def _calc_volatility_score(self) -> float:
        """Lower relative volatility -> higher (calmer) score. 0-100."""
        atr = self._atr()
        last = float(self.df['close'].iloc[-1])
        if last <= 0:
            return 50.0
        atr_pct = (atr / last) * 100.0
        # ~1% ATR -> ~70, ~4%+ ATR -> ~25. Calmer regimes score higher.
        score = 90.0 - (atr_pct * 15.0)
        return max(10.0, min(95.0, score))

    def _calc_smart_money_score(self) -> float:
        """Money Flow Index — volume-weighted momentum as a smart-money proxy."""
        if 'volume' not in self.df.columns or self.df['volume'].sum() == 0:
            return 50.0
        mfi = calculate_mfi(self.df, 14).iloc[-1]
        return 50.0 if pd.isna(mfi) else max(0.0, min(100.0, float(mfi)))

    def _calc_options_score(self) -> float:
        """Options/OI score. Neutral 50 unless real options data is supplied
        (no synthetic randomness)."""
        pcr = self.options_data.get("pcr")
        if pcr is None:
            return 50.0
        # Put/Call ratio >1 is bullish (contrarian); map around 50.
        return max(0.0, min(100.0, 50.0 + (float(pcr) - 1.0) * 30.0))

    def _calc_risk_score(self, volatility_score: float) -> float:
        # Higher volatility (lower volatility_score) -> higher risk.
        return max(0.0, min(100.0, 100.0 - volatility_score))

    def _atr(self, period: int = 14) -> float:
        """Average True Range on the frame (last value)."""
        high, low, close = self.df['high'], self.df['low'], self.df['close']
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        if pd.isna(atr):
            atr = float(tr.mean()) if not pd.isna(tr.mean()) else 0.0
        return float(atr)

    def _default_scores(self) -> dict:
        return {
            "action": "Hold",
            "confidence_pct": 0,
            "probability_pct": 50,
            "risk_score": 50,
            "sub_scores": {
                "trend": 50, "momentum": 50, "volume": 50,
                "volatility": 50, "smart_money": 50, "options": 50, "risk": 50,
            },
            "trade_setup": {
                "entry": 0.0, "stop_loss": 0.0, "target_1": 0.0, "target_2": 0.0
            },
        }
