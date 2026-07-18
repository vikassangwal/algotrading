"""Unified Trading Command Center.

Powers a single panel that shows, for one symbol:
  * a verdict for EVERY trading type (intraday / swing / positional / options / …)
  * directional probability — if you take the trade, what % says it goes UP vs DOWN
  * a trade plan (entry / stop-loss / targets) from real ATR levels
  * every analysis module's read on one side, plus an overall verdict
  * auto-execution on a strong "best setup", and auto position management
    (exit on target, exit on stop-loss, and exit if the market mood flips).

Everything respects the paper/live safety gate in execution.py.
"""
from __future__ import annotations

import logging
from typing import Dict

import pandas as pd

from .config import config, TradingStyle, AutoTradeState, DISCLAIMER
from .modules.ai_composite_engine import AICompositeEngine

logger = logging.getLogger("elco.command_center")

# A setup is "best / auto-tradeable" when the fused conviction clears this bar.
AUTO_SCORE_THRESHOLD = 0.5      # |score| >= this
AUTO_CONFIDENCE_THRESHOLD = 0.6  # confidence >= this
# Exit an open auto-position if the mood flips this far against it.
MOOD_FLIP_EXIT = 0.4


def _candles_to_df(candles) -> pd.DataFrame:
    return pd.DataFrame([{
        "open": c.open, "high": c.high, "low": c.low, "close": c.close,
        "volume": getattr(c, "volume", 0),
    } for c in candles])


def _directional_probability(score: float, confidence: float) -> dict:
    """Map fused score (-1..+1) + confidence (0..1) into UP/DOWN percentages.

    score 0 -> 50/50. Full bullish score at full confidence -> ~95% up.
    This is the 'agar trade lein to upar/neeche jaane ka % chance' the user
    asked for (green bar up, red bar down)."""
    tilt = max(-1.0, min(1.0, score)) * max(0.0, min(1.0, confidence))
    up_pct = round(50.0 + tilt * 45.0, 1)
    up_pct = max(5.0, min(95.0, up_pct))
    return {"up_pct": up_pct, "down_pct": round(100.0 - up_pct, 1)}


def build_command_center(symbol: str, engine, provider) -> dict:
    """Assemble the full command-center payload for one symbol."""
    styles = engine.analyze_all_styles(symbol)
    per_style = styles["per_style"]
    modules = styles["modules"]

    # Best trading type = the style with the highest conviction (|score|*confidence).
    best_style = None
    best_conv = -1.0
    for style_name, v in per_style.items():
        conv = abs(v["score"]) * v["confidence"]
        v["direction"] = _directional_probability(v["score"], v["confidence"])
        v["conviction_pct"] = round(conv * 100, 1)
        v["auto_tradeable"] = (
            abs(v["score"]) >= AUTO_SCORE_THRESHOLD
            and v["confidence"] >= AUTO_CONFIDENCE_THRESHOLD
        )
        if conv > best_conv:
            best_conv = conv
            best_style = style_name

    # Real ATR-based trade plan from candles.
    trade_plan = None
    try:
        candles = provider.get_candles(symbol, timeframe="1d", count=250)
        df = _candles_to_df(candles)
        if len(df) >= 20:
            setup = AICompositeEngine(df).calculate_scores()
            trade_plan = {
                "entry": setup["trade_setup"]["entry"],
                "stop_loss": setup["trade_setup"]["stop_loss"],
                "target_1": setup["trade_setup"]["target_1"],
                "target_2": setup["trade_setup"]["target_2"],
                "composite_action": setup["action"],
                "sub_scores": setup["sub_scores"],
            }
    except Exception as e:
        logger.warning(f"Trade plan unavailable for {symbol}: {e}")

    best = per_style.get(best_style, {}) if best_style else {}

    # Overall Bullish/Bearish verdict for EVERY trading type, using the
    # importance weight matrix (kis trading me kaunsi analysis ka kitna mahatva).
    from .trading_weights import verdicts_all_types
    type_verdicts = verdicts_all_types(modules)

    return {
        "symbol": symbol.upper(),
        "mode": config.auto_trade.value,            # off / active / halted
        "best_setup": {
            "trading_type": best_style,
            "action": best.get("action"),
            "conviction_pct": best.get("conviction_pct"),
            "direction": best.get("direction"),
            "auto_tradeable": best.get("auto_tradeable", False),
        },
        "trading_type_verdicts": type_verdicts,      # 14 types, each Bullish/Bearish + drivers
        "per_style": per_style,                      # style-engine verdicts
        "analysis_breakdown": modules,               # what each analysis says (one side)
        "trade_plan": trade_plan,                    # entry / SL / targets
        "disclaimer": DISCLAIMER,
    }


def _apply_trailing_discipline(trade, ltp: float) -> None:
    """D1 + D2: breakeven move at +1R, then trail 1R behind the peak.
    The stop only ever TIGHTENS — a winner is never allowed to become a
    full loser. Mutates trade.stop_loss / trade.peak_price in place."""
    from .trading_rules import BREAKEVEN_AT_R, TRAIL_START_R

    risk = getattr(trade, "initial_risk", 0.0) or 0.0
    if risk <= 0:
        return
    entry = trade.entry_price

    if trade.action == "BUY":
        trade.peak_price = max(getattr(trade, "peak_price", entry) or entry, ltp)
        gain = trade.peak_price - entry
        if gain >= TRAIL_START_R * risk:
            new_sl = trade.peak_price - risk          # D2: trail 1R behind peak
        elif gain >= BREAKEVEN_AT_R * risk:
            new_sl = entry                            # D1: breakeven
        else:
            return
        if new_sl > (trade.stop_loss or 0.0):
            trade.stop_loss = round(new_sl, 2)
    else:  # SELL / short — mirror image
        low = min(getattr(trade, "peak_price", entry) or entry, ltp)
        trade.peak_price = low
        gain = entry - low
        if gain >= TRAIL_START_R * risk:
            new_sl = low + risk
        elif gain >= BREAKEVEN_AT_R * risk:
            new_sl = entry
        else:
            return
        if new_sl < (trade.stop_loss or float("inf")):
            trade.stop_loss = round(new_sl, 2)


def _trade_age_days(trade) -> float:
    """Age of the position in days from its entry timestamp (0.0 on parse failure)."""
    try:
        from datetime import datetime
        ts = str(getattr(trade, "timestamp", "") or "")
        entry_time = datetime.fromisoformat(ts.split("+")[0])
        return (datetime.now() - entry_time).total_seconds() / 86400.0
    except Exception:
        return 0.0


def _is_live_eod() -> bool:
    """D4 window: at/after the live square-off time during a weekday (IST)."""
    from datetime import datetime, timezone, timedelta
    from .trading_rules import EOD_SQUARE_OFF_HHMM
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return minutes >= EOD_SQUARE_OFF_HHMM[0] * 60 + EOD_SQUARE_OFF_HHMM[1]


def auto_manage_positions(engine, provider, execution_engine) -> list:
    """Full exit discipline for every open position:
    stop-loss / target / mood-flip exits, breakeven + trailing stop (D1/D2),
    time stop (D3) and live end-of-day square-off (D4).

    Called by the 30s position monitor and the dashboard endpoint alike.
    """
    from .trading_rules import TIME_STOP_DAYS

    actions = []
    live_eod = (not config.paper_mode) and _is_live_eod()

    for symbol in list(execution_engine.open_positions.keys()):
        trade = execution_engine.open_positions[symbol]
        try:
            ltp = provider.get_quote(symbol).ltp
        except Exception:
            continue

        # 0. D1/D2 — tighten the stop BEFORE checking exits this sweep.
        _apply_trailing_discipline(trade, ltp)

        # 1. Target / stop-loss from the stored trade plan (fallback to %).
        sl = getattr(trade, "stop_loss", 0.0) or trade.entry_price * 0.98
        target = getattr(trade, "target", 0.0) or trade.entry_price * 1.04
        reason = None
        if trade.action == "BUY":
            if ltp <= sl:
                reason = "stop_loss"
            elif ltp >= target:
                reason = "target"
        else:  # SELL / short
            if ltp >= sl:
                reason = "stop_loss"
            elif ltp <= target:
                reason = "target"

        # 2. D4 — square off at 15:15 IST: ALL positions in live mode (they're
        # INTRADAY product at the broker), and intraday-style positions even
        # in paper mode (paper must mirror what live would do).
        is_intraday_trade = getattr(trade, "timeframe", "") == "intraday"
        if reason is None and (live_eod or (is_intraday_trade and _is_live_eod())):
            reason = "eod_squareoff"

        # 3. D3 — time stop: capital doesn't stay parked in going-nowhere trades.
        if reason is None and _trade_age_days(trade) >= TIME_STOP_DAYS:
            reason = "time_stop"

        # 4. Mood flip — re-score and exit if conviction turned against us.
        if reason is None:
            try:
                s = engine.analyze(symbol)
                held_dir = 1 if trade.action == "BUY" else -1
                if s.overall_score * held_dir <= -MOOD_FLIP_EXIT:
                    reason = "mood_flip"
            except Exception:
                pass

        if reason:
            ok = execution_engine.close_position(symbol, exit_price=ltp)
            if ok:
                actions.append({"symbol": symbol, "exit_price": ltp, "reason": reason})
                logger.info(f"AUTO-EXIT {symbol} @ {ltp} ({reason})")

    # Trailing-stop tightenings (D1/D2) mutate stop levels — snapshot them so
    # a restart never rolls a stop back to a looser level.
    try:
        from .state_store import persist_all
        persist_all()
    except Exception:
        pass

    return actions


def maybe_auto_execute(symbol: str, engine, provider, execution_engine, risk_manager) -> dict:
    """If auto mode is ACTIVE and a best setup qualifies, size and place the
    trade automatically (respecting the paper/live gate + risk limits)."""
    if config.auto_trade != AutoTradeState.ACTIVE:
        return {"executed": False, "reason": "auto_trade not ACTIVE"}

    signal = engine.analyze(symbol)
    if signal.action == "NEUTRAL":
        return {"executed": False, "reason": "no strong setup"}
    if abs(signal.overall_score) < AUTO_SCORE_THRESHOLD or signal.overall_confidence < AUTO_CONFIDENCE_THRESHOLD:
        return {"executed": False, "reason": "conviction below auto threshold"}

    allocation = risk_manager.calculate_position_size(signal)
    if allocation <= 0:
        return {"executed": False, "reason": "risk manager rejected sizing"}

    executed = execution_engine.execute_signal(signal, allocation)
    return {
        "executed": executed,
        "action": signal.action,
        "score": round(signal.overall_score, 4),
        "confidence": round(signal.overall_confidence, 4),
    }
