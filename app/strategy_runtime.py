"""Runtime for DEPLOYED strategies — connects generator output to execution.

A validated strategy from the generator is just a param dict. Deploying it
stores those params; this module rebuilds the exact signal function from the
params and evaluates it on fresh candles. When a signal fires and the caller
asks to execute, the order goes through the SAME chain as everything else:

    RiskManager.calculate_position_size (Kelly + caps + daily-loss)
        → ExecutionEngine.execute_signal (mandatory rules R1-R7, paper/live gate)

No deployed strategy can skip a single safety layer.
"""
from __future__ import annotations

import json
import logging
from typing import Callable, Optional

import pandas as pd

logger = logging.getLogger("elco.strategy_runtime")

_MIN_BARS = 120

# Regime compatibility — the biggest realized-win-rate lever there is.
# Mean-reversion strategies bleed in strong trends; trend strategies chop to
# death in ranges. A deployed strategy only trades when the CURRENT regime is
# one it historically works in. HIGH_VOLATILITY blocks everything (slippage +
# stop-hunts crush win rates across the board).
REGIME_COMPAT = {
    "rsi_reversion": {"RANGE_BOUND", "TRANSITIONING"},
    "bollinger": {"RANGE_BOUND", "TRANSITIONING"},
    "ema_cross": {"TRENDING", "TRANSITIONING"},
    "macd": {"TRENDING", "TRANSITIONING"},
    "donchian": {"TRENDING"},
    "bos_follow": {"TRENDING", "TRANSITIONING"},
    "sweep_reversal": {"RANGE_BOUND", "TRANSITIONING"},
    "sr_bounce": {"RANGE_BOUND", "TRANSITIONING"},
}


def _regime_ok(template: str, provider, symbol: str) -> tuple:
    """Returns (ok: bool, regime: str). Fails OPEN only if regime detection
    itself errors (we never block on our own infrastructure failure)."""
    allowed = REGIME_COMPAT.get(template)
    if not allowed:
        return True, "UNKNOWN_TEMPLATE"
    try:
        from .modules.ai_regime import MarketRegimeEngine
        regime = MarketRegimeEngine(provider).detect_regime(symbol).get("regime", "")
    except Exception as e:
        logger.warning(f"Regime detection failed for {symbol}: {e} — allowing trade.")
        return True, "DETECTION_FAILED"
    return (regime in allowed), regime


def _signal_fn_from_params(params: dict) -> Optional[Callable]:
    """Rebuild the exact generator signal function from stored params."""
    from .modules import strategy_generator as G
    t = params.get("template")
    try:
        if t == "ema_cross":
            return G._make_ema_cross(int(params["fast"]), int(params["slow"]))
        if t == "rsi_reversion":
            return G._make_rsi_reversion(int(params["period"]),
                                         int(params["oversold"]), int(params["overbought"]))
        if t == "donchian":
            return G._make_donchian(int(params["window"]))
        if t == "macd":
            return G._make_macd(int(params["fast"]), int(params["slow"]), int(params["signal"]))
        if t == "bollinger":
            return G._make_bollinger(int(params["period"]), float(params["std"]))
        if t == "bos_follow":
            return G._make_bos_follow(int(params["swing_lookback"]))
        if t == "sweep_reversal":
            return G._make_sweep_reversal(int(params["recent_bars"]))
        if t == "sr_bounce":
            return G._make_sr_bounce(float(params["tolerance_pct"]))
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Bad deployed-strategy params {params}: {e}")
    return None


def _candles_frame(provider, symbol: str, timeframe: str = "1d") -> Optional[pd.DataFrame]:
    """Bars on the strategy's own timeframe. Intraday note: the yfinance
    fallback path is ~15min delayed — on 15m bars that means the last bar may
    be one bar behind; the Dhan feed (when connected) is current."""
    try:
        candles = provider.get_candles(symbol, timeframe=timeframe, count=400)
    except Exception as e:
        logger.warning(f"Candle fetch failed for {symbol}: {e}")
        return None
    min_bars = _MIN_BARS if timeframe == "1d" else 100
    if not candles or len(candles) < min_bars:
        return None
    return pd.DataFrame({
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    })


def list_deployed(active_only: bool = False) -> list:
    from .db import SessionLocal, DeployedStrategy
    db = SessionLocal()
    try:
        q = db.query(DeployedStrategy)
        if active_only:
            q = q.filter(DeployedStrategy.active == 1)
        return [{
            "id": d.id, "name": d.name, "symbol": d.symbol,
            "params": json.loads(d.params or "{}"),
            "active": bool(d.active),
            "created_at": d.created_at.isoformat() if d.created_at else None,
        } for d in q.order_by(DeployedStrategy.id.desc()).all()]
    finally:
        db.close()


def deploy(name: str, symbol: str, params: dict) -> dict:
    """Store a strategy for live evaluation. Params must rebuild cleanly."""
    if _signal_fn_from_params(params) is None:
        raise ValueError(f"Unknown/invalid strategy params: {params}")
    from .db import SessionLocal, DeployedStrategy
    db = SessionLocal()
    try:
        row = DeployedStrategy(
            name=name, symbol=symbol.upper(), params=json.dumps(params), active=1
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"id": row.id, "name": row.name, "symbol": row.symbol}
    finally:
        db.close()


def set_active(strategy_id: int, active: bool) -> bool:
    from .db import SessionLocal, DeployedStrategy
    db = SessionLocal()
    try:
        row = db.query(DeployedStrategy).filter(DeployedStrategy.id == strategy_id).first()
        if row is None:
            return False
        row.active = 1 if active else 0
        db.commit()
        return True
    finally:
        db.close()


def evaluate_deployed(provider, symbol: str = "") -> list:
    """Evaluate ACTIVE deployed strategies on fresh candles — all of them,
    or only one symbol's when `symbol` is given (single-symbol callers like
    full_analysis shouldn't pay for the whole book).

    Returns a list of {id, name, symbol, signal} — signal is BUY/SELL/None.
    Read-only: nothing here places an order.
    """
    results = []
    frames: dict = {}
    want = symbol.upper().strip()
    for d in list_deployed(active_only=True):
        if want and d["symbol"] != want:
            continue
        fn = _signal_fn_from_params(d["params"])
        if fn is None:
            results.append({**d, "signal": None, "error": "invalid params"})
            continue
        sym = d["symbol"]
        tf = d["params"].get("timeframe", "1d")
        if (sym, tf) not in frames:
            frames[(sym, tf)] = _candles_frame(provider, sym, timeframe=tf)
        df = frames[(sym, tf)]
        if df is None:
            results.append({**d, "signal": None, "error": "insufficient candles"})
            continue
        try:
            sig = fn(df)
            ok, regime = _regime_ok(d["params"].get("template", ""), provider, sym)
            results.append({**d, "signal": sig, "regime": regime,
                            "regime_ok": ok,
                            "tradeable": sig in ("BUY", "SELL") and ok})
        except Exception as e:
            results.append({**d, "signal": None, "error": str(e)})
    return results


def execute_deployed(provider, execution_engine, risk_manager, strategy_id: int) -> dict:
    """Execute ONE deployed strategy's current signal through the full gated
    chain (Kelly sizing → mandatory rules → paper/live gate). Honest result."""
    from .engine import FusedSignal
    from .config import TradingStyle

    target = next((d for d in list_deployed(active_only=True) if d["id"] == strategy_id), None)
    if target is None:
        return {"executed": False, "reason": "strategy not found or inactive"}

    fn = _signal_fn_from_params(target["params"])
    tf = target["params"].get("timeframe", "1d")
    df = _candles_frame(provider, target["symbol"], timeframe=tf)
    if fn is None or df is None:
        return {"executed": False, "reason": "cannot evaluate (params/candles)"}

    side = fn(df)
    if side not in ("BUY", "SELL"):
        return {"executed": False, "reason": "no signal right now", "signal": None}

    # REGIME GATE — the strategy only trades in market conditions where its
    # validated win rate actually holds. Wrong regime = no trade, period.
    ok, regime = _regime_ok(target["params"].get("template", ""), provider, target["symbol"])
    if not ok:
        return {
            "executed": False, "signal": side, "regime": regime,
            "reason": (
                f"regime gate: current regime is {regime}, but "
                f"'{target['params'].get('template')}' strategies only keep their "
                f"win rate in {sorted(REGIME_COMPAT.get(target['params'].get('template'), []))}"
            ),
        }

    style = TradingStyle.INTRADAY if tf != "1d" else TradingStyle.SWING
    signal = FusedSignal(
        symbol=target["symbol"],
        overall_score=1.0 if side == "BUY" else -1.0,
        overall_confidence=0.75,  # deployed strategies size conservatively
        style=style,
        reasons=[f"Deployed strategy '{target['name']}' fired {side} on {tf} bars"],
    )
    allocation = risk_manager.calculate_position_size(signal)
    if allocation <= 0:
        return {"executed": False, "reason": "risk manager rejected sizing (limits/halt/off)", "signal": side}

    ok = execution_engine.execute_signal(signal, allocation)
    return {
        "executed": bool(ok),
        "signal": side,
        "allocation": round(allocation, 2) if ok else 0,
        "reason": "executed through gated chain" if ok else "blocked by mandatory rules / execution gate",
    }
