import pandas as pd
import numpy as np
import logging

from .indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_supertrend,
    calculate_mfi,
    calculate_obv,
    calculate_macd,
    calculate_adx,
    calculate_bollinger_bands,
    calculate_vwap,
    calculate_stochastic_oscillator,
    calculate_ichimoku
)

logger = logging.getLogger("elco.module.ai_composite")


class AICompositeEngine:
    """Composite technical scorer.

    Every sub-score is derived from a REAL indicator on the supplied OHLCV
    frame - no random numbers. Scores are 0-100 where 50 is neutral, >50 is
    bullish, <50 is bearish.
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
        
        # New comprehensive indicators
        macd_score = self._calc_macd_score()
        adx_score = self._calc_adx_score()
        bollinger_score = self._calc_bollinger_score()
        stochastic_score = self._calc_stochastic_score()
        vwap_score = self._calc_vwap_score()

        # Weighted average for comprehensive technical score
        # Using 10 indicators now!
        composite_raw = (
            trend_score * 0.15
            + momentum_score * 0.10
            + volume_score * 0.10
            + smart_money_score * 0.10
            + volatility_score * 0.05
            + options_score * 0.10
            + macd_score * 0.10
            + adx_score * 0.10
            + bollinger_score * 0.10
            + stochastic_score * 0.05
            + vwap_score * 0.05
        )

        probability_pct = int(round(composite_raw))
        probability_pct = max(0, min(100, probability_pct))

        if probability_pct >= 80:
            action = "Strong Buy"
        elif probability_pct >= 72:
            action = "Buy"
        elif probability_pct <= 20:
            action = "Strong Sell"
        elif probability_pct <= 28:
            action = "Sell"
        else:
            action = "Hold"

        confidence_pct = max(10, min(100, int(abs(probability_pct - 50) * 2)))

        # ATR-based trade setup
        last_close = float(self.df['close'].iloc[-1])
        atr = self._atr()
        if atr <= 0:
            atr = last_close * 0.01

        if action in ["Strong Buy", "Buy"]:
            entry = last_close
            sl = entry - (atr * 1.5)
            t1 = entry + (atr * 1.5)
            t2 = entry + (atr * 3.0)
        elif action in ["Strong Sell", "Sell"]:
            entry = last_close
            sl = entry + (atr * 1.5)
            t1 = entry - (atr * 1.5)
            t2 = entry - (atr * 3.0)
        else:
            entry = last_close
            sl = last_close - (atr * 1.5)
            t1 = last_close + (atr * 1.5)
            t2 = last_close + (atr * 3.0)

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
                "macd": int(round(macd_score)),
                "adx": int(round(adx_score)),
                "bollinger": int(round(bollinger_score)),
                "stochastic": int(round(stochastic_score)),
                "vwap": int(round(vwap_score))
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
        close = self.df['close']
        last = float(close.iloc[-1])
        score = 50.0

        ema20 = float(calculate_ema(close, 20).iloc[-1])
        ema50 = float(calculate_ema(close, 50).iloc[-1]) if len(close) >= 50 else ema20
        ema200 = float(calculate_ema(close, 200).iloc[-1]) if len(close) >= 200 else ema50

        if last > ema20: score += 8
        else: score -= 8
        if ema20 > ema50: score += 8
        else: score -= 8
        if ema50 > ema200: score += 9
        else: score -= 9

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
        close = self.df['close']
        rsi = calculate_rsi(close, 14).iloc[-1]
        rsi = 50.0 if pd.isna(rsi) else float(rsi)

        if len(close) > 10:
            roc = (float(close.iloc[-1]) / float(close.iloc[-11]) - 1.0) * 100.0
        else:
            roc = 0.0
        roc_score = 50.0 + max(-25.0, min(25.0, roc * 2.5))
        return max(0.0, min(100.0, 0.6 * rsi + 0.4 * roc_score))

    def _calc_volume_score(self) -> float:
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
            score += max(-15.0, min(15.0, (ratio - 1.0) * 15.0))
        return max(0.0, min(100.0, score))

    def _calc_volatility_score(self) -> float:
        atr = self._atr()
        last = float(self.df['close'].iloc[-1])
        if last <= 0: return 50.0
        atr_pct = (atr / last) * 100.0
        score = 90.0 - (atr_pct * 15.0)
        return max(10.0, min(95.0, score))

    def _calc_smart_money_score(self) -> float:
        if 'volume' not in self.df.columns or self.df['volume'].sum() == 0: return 50.0
        mfi = calculate_mfi(self.df, 14).iloc[-1]
        return 50.0 if pd.isna(mfi) else max(0.0, min(100.0, float(mfi)))

    def _calc_options_score(self) -> float:
        pcr = self.options_data.get("pcr")
        if pcr is None: return 50.0
        return max(0.0, min(100.0, 50.0 + (float(pcr) - 1.0) * 30.0))

    def _calc_risk_score(self, volatility_score: float) -> float:
        return max(0.0, min(100.0, 100.0 - volatility_score))

    # --- New Indicators ---
    def _calc_macd_score(self) -> float:
        try:
            macd_df = calculate_macd(self.df['close'])
            hist = macd_df['Histogram'].iloc[-1]
            macd_val = macd_df['MACD'].iloc[-1]
            score = 50.0
            if hist > 0: score += 15
            else: score -= 15
            if macd_val > 0: score += 10
            else: score -= 10
            return max(0.0, min(100.0, score))
        except:
            return 50.0

    def _calc_adx_score(self) -> float:
        try:
            adx_df = calculate_adx(self.df)
            adx_val = adx_df['ADX'].iloc[-1]
            p_di = adx_df['+DI'].iloc[-1]
            m_di = adx_df['-DI'].iloc[-1]
            score = 50.0
            if p_di > m_di:
                score += min(50.0, adx_val * 1.5)
            else:
                score -= min(50.0, adx_val * 1.5)
            return max(0.0, min(100.0, score))
        except:
            return 50.0

    def _calc_bollinger_score(self) -> float:
        try:
            bb = calculate_bollinger_bands(self.df['close'])
            last = float(self.df['close'].iloc[-1])
            upper = float(bb['Upper_Band'].iloc[-1])
            lower = float(bb['Lower_Band'].iloc[-1])
            # If price is near lower band it's oversold (bullish for mean reversion)
            # If it's breaking upper band it's strong trend
            # We map 0-100 position in the band
            pos = (last - lower) / (upper - lower)
            score = 50.0 + (pos - 0.5) * 50.0
            return max(0.0, min(100.0, score))
        except:
            return 50.0

    def _calc_stochastic_score(self) -> float:
        try:
            stoch = calculate_stochastic_oscillator(self.df)
            k = float(stoch['%K'].iloc[-1])
            score = 50.0
            if k < 20: score = 80.0 # Oversold, bullish
            elif k > 80: score = 20.0 # Overbought, bearish
            else: score = k
            return max(0.0, min(100.0, score))
        except:
            return 50.0

    def _calc_vwap_score(self) -> float:
        if 'volume' not in self.df.columns or self.df['volume'].sum() == 0: return 50.0
        try:
            vwap = calculate_vwap(self.df)
            last = float(self.df['close'].iloc[-1])
            v_val = float(vwap.iloc[-1])
            return 70.0 if last > v_val else 30.0
        except:
            return 50.0

    def _atr(self, period: int = 14) -> float:
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
                "macd": 50, "adx": 50, "bollinger": 50, "stochastic": 50, "vwap": 50
            },
            "trade_setup": {
                "entry": 0.0, "stop_loss": 0.0, "target_1": 0.0, "target_2": 0.0
            },
        }

class VectorizedAIEngine:
    """Vectorized version of AICompositeEngine for high-performance backtesting."""
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def _atr(self, period: int = 14) -> pd.Series:
        high, low, close = self.df['high'], self.df['low'], self.df['close']
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr.bfill().fillna(close * 0.01)

    def calculate_all(self) -> pd.DataFrame:
        df = self.df
        close = df['close']
        
        # 1. Trend
        ema20 = calculate_ema(close, 20)
        ema50 = calculate_ema(close, 50)
        ema200 = calculate_ema(close, 200)
        trend = pd.Series(50.0, index=df.index)
        trend += np.where(close > ema20, 8, -8)
        trend += np.where(ema20 > ema50, 8, -8)
        trend += np.where(ema50 > ema200, 9, -9)
        try:
            st = calculate_supertrend(df)
            trend += np.where(st['Direction'] > 0, 15, -15)
        except:
            pass
        trend_score = trend.clip(0, 100)

        # 2. Momentum
        rsi = calculate_rsi(close, 14).fillna(50.0)
        roc = (close / close.shift(10) - 1.0) * 100.0
        roc_score = 50.0 + (roc * 2.5).clip(-25.0, 25.0).fillna(0)
        momentum_score = (0.6 * rsi + 0.4 * roc_score).clip(0, 100)

        # 3. Volume
        vol = pd.Series(50.0, index=df.index)
        if 'volume' in df.columns and df['volume'].sum() > 0:
            obv = calculate_obv(df)
            recent_obv = obv - obv.shift(5)
            vol += np.where(recent_obv > 0, 15, -15)
            avg_vol = df['volume'].rolling(20).mean()
            ratio = df['volume'] / avg_vol
            vol += ((ratio - 1.0) * 15.0).clip(-15.0, 15.0).fillna(0)
        volume_score = vol.clip(0, 100)

        # 4. Volatility
        atr = self._atr()
        atr_pct = (atr / close) * 100.0
        volatility_score = (90.0 - (atr_pct * 15.0)).clip(10.0, 95.0)

        # 5. Smart Money
        if 'volume' in df.columns and df['volume'].sum() > 0:
            mfi = calculate_mfi(df, 14).fillna(50.0)
            smart_money_score = mfi.clip(0, 100)
        else:
            smart_money_score = pd.Series(50.0, index=df.index)

        # 6. Options (Dummy 50 for mock)
        options_score = pd.Series(50.0, index=df.index)

        # 7. MACD
        try:
            macd_df = calculate_macd(close)
            macd_s = pd.Series(50.0, index=df.index)
            macd_s += np.where(macd_df['Histogram'] > 0, 15, -15)
            macd_s += np.where(macd_df['MACD'] > 0, 10, -10)
            macd_score = macd_s.clip(0, 100)
        except:
            macd_score = pd.Series(50.0, index=df.index)

        # 8. ADX
        try:
            adx_df = calculate_adx(df)
            adx_s = pd.Series(50.0, index=df.index)
            adx_val = adx_df['ADX']
            adx_add = np.minimum(50.0, adx_val * 1.5)
            adx_s += np.where(adx_df['+DI'] > adx_df['-DI'], adx_add, -adx_add)
            adx_score = adx_s.clip(0, 100).fillna(50.0)
        except:
            adx_score = pd.Series(50.0, index=df.index)

        # 9. Bollinger
        try:
            bb = calculate_bollinger_bands(close)
            pos = (close - bb['Lower_Band']) / (bb['Upper_Band'] - bb['Lower_Band'])
            bb_score = (50.0 + (pos - 0.5) * 50.0).clip(0, 100).fillna(50.0)
        except:
            bb_score = pd.Series(50.0, index=df.index)

        # 10. Stochastic
        try:
            stoch = calculate_stochastic_oscillator(df)
            k = stoch['%K']
            st_score = k.copy()
            st_score = np.where(k < 20, 80.0, st_score)
            st_score = np.where(k > 80, 20.0, st_score)
            stochastic_score = pd.Series(st_score, index=df.index).clip(0, 100).fillna(50.0)
        except:
            stochastic_score = pd.Series(50.0, index=df.index)

        # 11. VWAP
        if 'volume' in df.columns and df['volume'].sum() > 0:
            try:
                vwap = calculate_vwap(df)
                vwap_score = pd.Series(np.where(close > vwap, 70.0, 30.0), index=df.index).fillna(50.0)
            except:
                vwap_score = pd.Series(50.0, index=df.index)
        else:
            vwap_score = pd.Series(50.0, index=df.index)

        # Composite
        composite_raw = (
            trend_score * 0.15 + momentum_score * 0.10 + volume_score * 0.10 +
            smart_money_score * 0.10 + volatility_score * 0.05 + options_score * 0.10 +
            macd_score * 0.10 + adx_score * 0.10 + bb_score * 0.10 +
            stochastic_score * 0.05 + vwap_score * 0.05
        )

        prob_pct = composite_raw.round().clip(0, 100).fillna(50).astype(int)
        
        # Action logic based on strict 80%+ conviction thresholds
        conditions = [
            prob_pct >= 80,
            prob_pct >= 72,
            prob_pct <= 20,
            prob_pct <= 28
        ]
        choices = ["Strong Buy", "Buy", "Strong Sell", "Sell"]
        action = np.select(conditions, choices, default="Hold")
        
        df['probability_pct'] = prob_pct
        df['action'] = action
        
        # Stops and targets
        df['atr'] = atr
        df['sl'] = np.where(np.isin(action, ["Strong Buy", "Buy"]), close - (atr * 1.5),
                   np.where(np.isin(action, ["Strong Sell", "Sell"]), close + (atr * 1.5), close - (atr * 1.5)))
        
        df['target_1'] = np.where(np.isin(action, ["Strong Buy", "Buy"]), close + (atr * 1.5),
                         np.where(np.isin(action, ["Strong Sell", "Sell"]), close - (atr * 1.5), close + (atr * 1.5)))
                         
        df['target_2'] = np.where(np.isin(action, ["Strong Buy", "Buy"]), close + (atr * 3.0),
                         np.where(np.isin(action, ["Strong Sell", "Sell"]), close - (atr * 3.0), close + (atr * 3.0)))
                         
        return df
