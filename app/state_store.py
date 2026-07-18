"""Runtime-state persistence — turns rule discipline from a promise into
architecture that survives restarts.

Without this file, a mid-day server restart would silently reset:
  * R5's trades-today counter        (overtrading brake)
  * R6's stop-loss cooldowns         (revenge-trade brake)
  * R7's consecutive-loss counter and the HALTED state itself
  * R8's daily P&L                   (daily loss limit)
  * every open position's stop-loss/target/trailing state

— i.e. a restart would BYPASS the rules. Now every mutation persists a
snapshot to runtime_state.json (atomic tmp+replace, gitignored), and startup
restores it: same-IST-day state fully, and open positions always (swing
positions legitimately span days).
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("elco.state")

_STATE_DIR = Path(os.getenv("ELCO_STATE_DIR", "")) if os.getenv("ELCO_STATE_DIR") else Path(__file__).resolve().parent.parent
STATE_PATH = _STATE_DIR / "runtime_state.json"
IST = timezone(timedelta(hours=5, minutes=30))

_lock = threading.Lock()
_execution_engine = None  # registered at startup


def register(execution_engine) -> None:
    global _execution_engine
    _execution_engine = execution_engine


def _today() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def persist_all() -> bool:
    """Snapshot rules + risk + halt state + open positions to disk.
    Called after every entry, exit and rule mutation. Never raises."""
    try:
        from . import trading_rules as R
        from .risk_manager import risk_manager
        from .config import config

        state = {
            "saved_at": datetime.now(IST).isoformat(timespec="seconds"),
            "day": _today(),
            "rules": {
                "day": R._state.day,
                "trades_today": R._state.trades_today,
                "consecutive_losses": R._state.consecutive_losses,
                "last_sl_exit": {s: t.isoformat() for s, t in R._state.last_sl_exit.items()},
            },
            "risk": {
                "daily_pnl": risk_manager.daily_pnl,
                "portfolio_exposure": risk_manager.portfolio_exposure,
            },
            "auto_trade": str(config.auto_trade.value),
            "open_positions": (
                {sym: asdict(t) for sym, t in _execution_engine.open_positions.items()}
                if _execution_engine is not None else {}
            ),
        }
        with _lock:
            tmp = STATE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
            os.replace(str(tmp), str(STATE_PATH))
        return True
    except Exception as e:
        logger.error(f"State persist failed: {e}")
        return False


def restore_all() -> dict:
    """Restore state at startup. Same-IST-day: rule counters, cooldowns,
    daily P&L and the HALTED flag (a restart must never bypass R7/R8).
    Open positions: always restored — their SL/target/trailing must keep
    being enforced no matter when the server comes back."""
    result = {"restored": False, "positions": 0, "same_day": False, "detail": ""}
    try:
        if not STATE_PATH.exists():
            result["detail"] = "no prior state file"
            return result
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

        same_day = state.get("day") == _today()
        result["same_day"] = same_day

        if same_day:
            from . import trading_rules as R
            from .risk_manager import risk_manager
            from .config import config, AutoTradeState

            rules = state.get("rules", {})
            R._state.day = rules.get("day", "")
            R._state.trades_today = int(rules.get("trades_today", 0))
            R._state.consecutive_losses = int(rules.get("consecutive_losses", 0))
            R._state.last_sl_exit = {
                s: datetime.fromisoformat(t)
                for s, t in (rules.get("last_sl_exit") or {}).items()
            }
            risk = state.get("risk", {})
            risk_manager.daily_pnl = float(risk.get("daily_pnl", 0.0))
            risk_manager.portfolio_exposure = float(risk.get("portfolio_exposure", 0.0))
            # HALTED survives a restart; ACTIVE does not auto-resume (the
            # human must arm auto-trading again — safe default).
            if state.get("auto_trade") == "halted":
                config.auto_trade = AutoTradeState.HALTED

        restored_positions = 0
        if _execution_engine is not None:
            from .execution import TradeRecord
            for sym, d in (state.get("open_positions") or {}).items():
                if sym in _execution_engine.open_positions:
                    continue
                try:
                    trade = TradeRecord(**d)
                    _execution_engine.open_positions[sym] = trade
                    _execution_engine.journal.append(trade)
                    restored_positions += 1
                except Exception as e:
                    logger.error(f"Could not restore position {sym}: {e}")

        result.update({"restored": True, "positions": restored_positions,
                       "detail": f"state from {state.get('saved_at')}"})
        if restored_positions:
            logger.info(f"Restored {restored_positions} open position(s) with SL/target intact.")
        if same_day:
            logger.info("Same-day restart: rule counters, cooldowns, daily P&L and halt state restored.")
        return result
    except Exception as e:
        logger.error(f"State restore failed: {e}")
        result["detail"] = str(e)
        return result
