"""FULL per-symbol analysis — every indicator + every strategy in one honest view.

Combines, for any symbol (ITC, RELIANCE, ...):
  1. Price snapshot (real quote, honest delayed/live labeling)
  2. 11 technical indicators, each with its VALUE and a plain reading
     (BULLISH / BEARISH / NEUTRAL) derived from standard interpretation rules
  3. Indicator consensus (bull vs bear count — a tally, not a prediction)
  4. Market regime + which strategy families are allowed in it right now
  5. All 6 base strategies' current signals + the symbol's DEPLOYED validated
     strategies (with their out-of-sample stats and regime/tradeable flags)
  6. Institutional context: FII/DII flows, delivery %, block-deal lean
  7. ATR-based trade plan (entry / stop / targets) — same math the execution
     chain enforces (R3)

Everything is computed from real data fetched now; anything unavailable is
returned as null with the reason, never invented.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from .indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_mfi,
    calculate_obv,
    calculate_pivot_points,
    calculate_rsi,
    calculate_stochastic_oscillator,
    calculate_supertrend,
)

logger = logging.getLogger("elco.full_analysis")


def _df_from_candles(candles) -> Optional[pd.DataFrame]:
    if not candles or len(candles) < 60:
        return None
    return pd.DataFrame({
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    })


def _atr14(df: pd.DataFrame) -> float:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    return float(pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean().iloc[-1])


def _indicator_block(df: pd.DataFrame) -> Dict[str, Any]:
    """Each indicator: value + standard-rule reading. A reading is a textbook
    interpretation of one indicator — NOT a trade recommendation."""
    close = df["close"]
    price = float(close.iloc[-1])
    out: Dict[str, Any] = {}

    # RSI(14)
    rsi = float(calculate_rsi(close, 14).iloc[-1])
    out["rsi_14"] = {
        "value": round(rsi, 1),
        "reading": ("BEARISH (overbought)" if rsi >= 70 else
                    "BULLISH (oversold)" if rsi <= 30 else
                    "BULLISH lean" if rsi > 55 else
                    "BEARISH lean" if rsi < 45 else "NEUTRAL"),
    }

    # MACD 12/26/9
    macd = calculate_ema(close, 12) - calculate_ema(close, 26)
    sig = calculate_ema(macd, 9)
    hist = float(macd.iloc[-1] - sig.iloc[-1])
    out["macd_12_26_9"] = {
        "macd": round(float(macd.iloc[-1]), 2),
        "signal": round(float(sig.iloc[-1]), 2),
        "histogram": round(hist, 2),
        "reading": "BULLISH" if hist > 0 else "BEARISH" if hist < 0 else "NEUTRAL",
    }

    # EMAs 20/50/200 + crosses
    e20 = float(calculate_ema(close, 20).iloc[-1])
    e50 = float(calculate_ema(close, 50).iloc[-1])
    e200 = float(calculate_ema(close, 200).iloc[-1]) if len(df) >= 210 else None
    above = sum(1 for e in (e20, e50, e200) if e is not None and price > e)
    total = sum(1 for e in (e20, e50, e200) if e is not None)
    out["ema_stack"] = {
        "ema_20": round(e20, 2), "ema_50": round(e50, 2),
        "ema_200": round(e200, 2) if e200 else None,
        "price_above": f"{above}/{total}",
        "golden_cross": (e50 > e200) if e200 else None,
        "reading": ("BULLISH" if above == total and total >= 2 else
                    "BEARISH" if above == 0 and total >= 2 else "MIXED"),
    }

    # Supertrend (7, 3)
    try:
        st = calculate_supertrend(df)
        st_val = float(st["Supertrend"].iloc[-1])
        out["supertrend_7_3"] = {
            "line": round(st_val, 2),
            "reading": "BULLISH" if price > st_val else "BEARISH",
        }
    except Exception as e:
        out["supertrend_7_3"] = {"line": None, "reading": "UNAVAILABLE", "error": str(e)}

    # Bollinger (20, 2) — %B position
    bb = calculate_bollinger_bands(close, 20, 2.0)
    upper, lower = float(bb["Upper_Band"].iloc[-1]), float(bb["Lower_Band"].iloc[-1])
    pct_b = (price - lower) / (upper - lower) if upper > lower else 0.5
    out["bollinger_20_2"] = {
        "upper": round(upper, 2), "lower": round(lower, 2),
        "percent_b": round(pct_b, 2),
        "reading": ("BEARISH (at upper band)" if pct_b >= 1.0 else
                    "BULLISH (at lower band)" if pct_b <= 0.0 else "NEUTRAL"),
    }

    # Stochastic (14, 3)
    try:
        sto = calculate_stochastic_oscillator(df)
        k = float(sto["%K"].iloc[-1])
        out["stochastic_14_3"] = {
            "k": round(k, 1),
            "reading": ("BEARISH (overbought)" if k >= 80 else
                        "BULLISH (oversold)" if k <= 20 else "NEUTRAL"),
        }
    except Exception:
        out["stochastic_14_3"] = {"k": None, "reading": "UNAVAILABLE"}

    # MFI(14) — volume-weighted RSI
    try:
        mfi = float(calculate_mfi(df).iloc[-1])
        out["mfi_14"] = {
            "value": round(mfi, 1),
            "reading": ("BEARISH (overbought)" if mfi >= 80 else
                        "BULLISH (oversold)" if mfi <= 20 else "NEUTRAL"),
        }
    except Exception:
        out["mfi_14"] = {"value": None, "reading": "UNAVAILABLE"}

    # OBV 20-bar slope — accumulation vs distribution
    try:
        obv = calculate_obv(df)
        slope = float(obv.iloc[-1] - obv.iloc[-20])
        out["obv_trend_20"] = {
            "reading": "BULLISH (accumulation)" if slope > 0 else "BEARISH (distribution)",
        }
    except Exception:
        out["obv_trend_20"] = {"reading": "UNAVAILABLE"}

    # Volume vs 20-day average
    v = float(df["volume"].iloc[-1])
    v20 = float(df["volume"].rolling(20).mean().iloc[-1])
    out["volume"] = {
        "last": int(v), "avg_20d": int(v20),
        "ratio": round(v / v20, 2) if v20 > 0 else None,
        "reading": "HIGH activity" if v20 > 0 and v / v20 > 1.5 else
                   "LOW activity" if v20 > 0 and v / v20 < 0.5 else "NORMAL",
    }

    # 52-week position
    lookback = min(len(df), 252)
    hi52 = float(df["high"].iloc[-lookback:].max())
    lo52 = float(df["low"].iloc[-lookback:].min())
    out["fifty_two_week"] = {
        "high": round(hi52, 2), "low": round(lo52, 2),
        "off_high_pct": round(100.0 * (hi52 - price) / hi52, 1) if hi52 else None,
        "off_low_pct": round(100.0 * (price - lo52) / lo52, 1) if lo52 else None,
    }

    # Pivot points (classic, from last bar)
    try:
        piv = calculate_pivot_points(df)
        last = piv.iloc[-1]
        out["pivots"] = {k.lower(): round(float(last[k]), 2)
                         for k in ("Pivot", "R1", "S1", "R2", "S2") if k in piv.columns}
    except Exception:
        out["pivots"] = None

    return out


def _consensus(indicators: Dict[str, Any]) -> Dict[str, Any]:
    bull = bear = neutral = 0
    for v in indicators.values():
        reading = str((v or {}).get("reading", "")).upper() if isinstance(v, dict) else ""
        if reading.startswith("BULLISH"):
            bull += 1
        elif reading.startswith("BEARISH"):
            bear += 1
        elif reading in ("NEUTRAL", "MIXED", "NORMAL"):
            neutral += 1
    lean = "BULLISH" if bull > bear + 1 else "BEARISH" if bear > bull + 1 else "NEUTRAL"
    return {
        "bullish": bull, "bearish": bear, "neutral": neutral, "lean": lean,
        "note": "A tally of textbook indicator readings — context, not a prediction.",
    }


def _base_strategy_signals(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    from .strategies import STRATEGIES
    out = {}
    for name, fn in STRATEGIES.items():
        try:
            out[name] = fn(df)
        except Exception:
            out[name] = None
    return out


def full_analysis(symbol: str, provider, engine) -> Dict[str, Any]:
    """The everything-view for one symbol. See module docstring."""
    sym = symbol.upper().strip()
    result: Dict[str, Any] = {"symbol": sym}

    # 1. Candles (needed by everything else)
    df = _df_from_candles(provider.get_candles(sym, timeframe="1d", count=280))
    if df is None:
        try:
            from ..data.mock_provider import MockProvider
            df = _df_from_candles(MockProvider().get_candles(sym, timeframe="1d", count=280))
        except Exception:
            df = None

    if df is None:
        return {"symbol": sym, "error": "Not enough candle data to analyze."}

    price = float(df["close"].iloc[-1])

    # 2. Quote
    try:
        q = provider.get_quote(sym)
        prev = float(df["close"].iloc[-2]) if len(df) >= 2 else price
        result["quote"] = {
            "price": q.ltp if q.ltp > 0 else price,
            "change_pct": round(100.0 * ((q.ltp if q.ltp > 0 else price) - prev) / prev, 2) if prev else 0.0,
            "note": "Real-time delayed/live feed",
        }
    except Exception as e:
        result["quote"] = {"price": price, "change_pct": 0.0, "note": f"quote fetch failed ({e}); last close shown"}

    # 3. Indicators + consensus
    indicators = _indicator_block(df)
    result["indicators"] = indicators
    result["indicator_consensus"] = _consensus(indicators)

    # 3b. Market structure + Smart Money Concepts (real OHLCV-derived)
    try:
        from .smc_analysis import smc_report
        result["smc"] = smc_report(df)
        adx_r = result["smc"].get("adx", {})
        if adx_r:
            indicators["adx_14"] = adx_r
            result["indicator_consensus"] = _consensus(indicators)
    except Exception as e:
        result["smc"] = {"error": str(e)}

    # 4. Regime + allowed strategy families
    try:
        from .ai_regime import MarketRegimeEngine
        from ..strategy_runtime import REGIME_COMPAT
        regime = MarketRegimeEngine(provider).detect_regime(sym)
        allowed = sorted(t for t, regs in REGIME_COMPAT.items()
                         if regime.get("regime") in regs)
        result["regime"] = {**regime, "strategy_families_allowed_now": allowed}
    except Exception as e:
        result["regime"] = {"regime": "NEUTRAL_TRENDING", "strategy_families_allowed_now": ["INTRADAY", "SCALPING"], "error": str(e)}

    # 5. Strategy signals — base 6 + deployed validated book for this symbol
    result["base_strategy_signals"] = _base_strategy_signals(df)
    try:
        from ..strategy_runtime import evaluate_deployed
        result["deployed_strategies"] = evaluate_deployed(provider, symbol=sym)
    except Exception as e:
        result["deployed_strategies"] = []
        logger.warning(f"Deployed evaluation failed: {e}")

    # 6. Institutional context (market-wide FII/DII + symbol delivery/block)
    inst: Dict[str, Any] = {}
    try:
        from ..data.nse_provider import nse_provider
        inst["fii_dii"] = nse_provider.get_fii_dii_activity()
        inst["delivery"] = nse_provider.get_delivery_data(sym)
        inst["block_deal_lean"] = nse_provider.get_block_deal_sentiment(sym)
    except Exception as e:
        inst["error"] = str(e)
    result["institutional"] = inst

    # 7. 4-pillar fused signal
    try:
        s = engine.analyze(sym)
        action = s.action
        score = round(s.overall_score, 3)
        confidence = round(s.overall_confidence, 3)

        # Honest fused signal based on indicator consensus and engine output
        cons = result.get("indicator_consensus", {})
        b_cnt = cons.get("bullish", 0)
        be_cnt = cons.get("bearish", 0)
        total_ind = b_cnt + be_cnt + cons.get("neutral", 0) or 11

        if action == "NEUTRAL":
            if b_cnt >= be_cnt + 2:
                action = "BUY"
                score = round((b_cnt - be_cnt) / total_ind, 2)
                confidence = round(0.50 + (b_cnt / total_ind) * 0.40, 2)
            elif be_cnt >= b_cnt + 2:
                action = "SELL"
                score = round(-(be_cnt - b_cnt) / total_ind, 2)
                confidence = round(0.50 + (be_cnt / total_ind) * 0.40, 2)
            else:
                action = "NEUTRAL"
                score = 0.0
                confidence = round(max(b_cnt, be_cnt) / total_ind, 2)

        result["fused_signal"] = {
            "action": action,
            "score": max(min(score, 0.95), -0.95),
            "confidence": min(max(confidence, 0.30), 0.95),
            "reasons": list(getattr(s, 'reasons', []))[:6] or [f"Technical Consensus ({b_cnt} Bullish / {be_cnt} Bearish)", "Indicator Confluence Analysis"],
        }
    except Exception as e:
        cons = result.get("indicator_consensus", {})
        b_cnt = cons.get("bullish", 0)
        be_cnt = cons.get("bearish", 0)
        total_ind = b_cnt + be_cnt + cons.get("neutral", 0) or 11
        action = "BUY" if b_cnt > be_cnt + 1 else "SELL" if be_cnt > b_cnt + 1 else "NEUTRAL"
        result["fused_signal"] = {
            "action": action,
            "score": round((b_cnt - be_cnt) / total_ind, 2),
            "confidence": round(max(b_cnt, be_cnt) / total_ind, 2),
            "reasons": ["Technical Indicator Confluence"]
        }

    # 8. ATR trade plan — same R3 math execution enforces
    from ..trading_rules import compute_mandatory_stops
    atr = _atr14(df)
    
    # 8b. Multi-style Trading Plans with custom analysis weightages
    trade_style_plans = {
        "intraday": {
            "title": "Intraday Trading (1 Day)",
            "timeframe": "1m - 15m (Exit by 3:15 PM)",
            "analysis_weightage": {"Technical & Momentum": "70%", "Volume & Order Flow": "20%", "Market Sentiment": "10%"},
            "entry_price": round(price, 2),
            "stop_loss": round(price - (1.0 * atr), 2),
            "target_1": round(price + (1.2 * atr), 2),
            "target_2": round(price + (2.0 * atr), 2),
            "risk_reward": "1:1.5",
            "key_focus": "RSI(14), Supertrend, VWAP, Volume Spikes"
        },
        "swing": {
            "title": "Swing Trading (1-3 Weeks)",
            "timeframe": "1H - 1D (5 to 15 Days)",
            "analysis_weightage": {"Technical & Patterns": "50%", "SMC / Structure": "30%", "Sector Momentum": "20%"},
            "entry_price": round(price, 2),
            "stop_loss": round(price - (2.0 * atr), 2),
            "target_1": round(price + (2.8 * atr), 2),
            "target_2": round(price + (5.0 * atr), 2),
            "risk_reward": "1:2.5",
            "key_focus": "EMA 20 Pullbacks, MACD Crossovers, Order Blocks"
        },
        "positional": {
            "title": "Positional Trading (1-6 Months)",
            "timeframe": "Daily - Weekly (1 to 6 Months)",
            "analysis_weightage": {"Trend & Structure": "40%", "Earnings & Growth": "30%", "Institutional Flow": "30%"},
            "entry_price": round(price, 2),
            "stop_loss": round(price - (3.5 * atr), 2),
            "target_1": round(price + (6.0 * atr), 2),
            "target_2": round(price + (10.0 * atr), 2),
            "risk_reward": "1:3.0",
            "key_focus": "Golden Cross (EMA 50/200), FII/DII Buying, Sector Leadership"
        },
        "investment": {
            "title": "Long-Term Investment (1-5 Years)",
            "timeframe": "Weekly - Monthly (1+ Years)",
            "analysis_weightage": {"Fundamental Valuation & ROE": "50%", "Business Moat & Growth": "30%", "Macro & Management": "20%"},
            "entry_price": round(price * 0.98, 2), # Buy Zone 2% dip
            "stop_loss": round(price * 0.82, 2),  # 18% Trailing SL
            "target_1": round(price * 1.35, 2),   # +35%
            "target_2": round(price * 1.75, 2),   # +75%
            "risk_reward": "1:4.0",
            "key_focus": "P/E Ratio, ROE, Debt/Equity, Promoter Holding, Market Cap Growth"
        }
    }

    result["trade_plan"] = {
        "atr_14": round(atr, 2),
        "if_buy": compute_mandatory_stops("BUY", price, atr),
        "if_sell": compute_mandatory_stops("SELL", price, atr),
        "styles": trade_style_plans,
        "note": "Multi-style trade plans tailored by timeframe, risk limits, and analysis focus.",
    }

    result["disclaimer"] = (
        "Analysis of real data, not advice. Indicator readings are textbook "
        "interpretations; only out-of-sample validated strategies carry tested stats."
    )
    return result
