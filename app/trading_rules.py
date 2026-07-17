"""MANDATORY trading rules — enforced inside ExecutionEngine.execute_signal.

Every rule here is checked on EVERY trade, no matter who initiates it (API
endpoint, dashboard button, auto-trader, or future code). There is no bypass
parameter on purpose: if a trade violates a rule, it is rejected and the
rejection reason is logged + returned.

Rules enforced:
  R1  System not HALTED (daily-loss / crash-radar halt is sacred).
  R2  Market hours only (NSE 09:15–15:30 IST, Mon–Fri) for LIVE orders.
      Paper trades are allowed anytime (testing/simulation is the point).
  R3  Mandatory stop-loss: every entry gets an ATR-based SL and target
      attached at entry time (no naked positions, ever).
  R4  Minimum reward:risk of 1:1 — the target must be at least as far as SL.
  R5  Max trades per day (overtrading brake).
  R6  Cooldown after a stop-loss exit on the same symbol (revenge-trade brake).
  R7  Max consecutive losing trades in a day → auto-halt for the day.

Position-size, exposure, and daily-loss rules already live in RiskManager
(calculate_position_size) — these are the EXECUTION-level rules that complete
the chain.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from .config import config, AutoTradeState

logger = logging.getLogger("elco.rules")

IST = timezone(timedelta(hours=5, minutes=30))

# --- Tunables (kept conservative; can move to config later) ------------------
MAX_TRADES_PER_DAY = 10
SL_COOLDOWN_MINUTES = 30          # no re-entry on a symbol this soon after a SL hit
MAX_CONSECUTIVE_LOSSES = 3        # third straight loser halts the day
MIN_REWARD_RISK = 1.0             # target distance must be >= SL distance
SL_ATR_MULT = 1.5                 # mandatory SL distance
TARGET_ATR_MULT = 2.25            # default target (1:1.5 R:R)


@dataclass
class RuleState:
    """Mutable per-day rule-tracking state (process-lifetime)."""
    day: str = ""
    trades_today: int = 0
    consecutive_losses: int = 0
    last_sl_exit: Dict[str, datetime] = field(default_factory=dict)

    def roll_day_if_needed(self, now_ist: datetime):
        d = now_ist.strftime("%Y-%m-%d")
        if d != self.day:
            self.day = d
            self.trades_today = 0
            self.consecutive_losses = 0
            self.last_sl_exit.clear()


_state = RuleState()


@dataclass
class RuleVerdict:
    allowed: bool
    reason: str = ""


def _now_ist() -> datetime:
    return datetime.now(IST)


def _market_open(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= minutes <= (15 * 60 + 30)


def check_entry_rules(symbol: str, is_live: bool) -> RuleVerdict:
    """R1, R2, R5, R6, R7 — called by execute_signal BEFORE placing anything."""
    now = _now_ist()
    _state.roll_day_if_needed(now)

    # R1 — halted system trades nothing, ever.
    if config.auto_trade == AutoTradeState.HALTED:
        return RuleVerdict(False, "R1: System is HALTED (daily loss / crash radar). Manual approval required to resume.")

    # R7 — consecutive-loss circuit breaker.
    if _state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        return RuleVerdict(False, f"R7: {MAX_CONSECUTIVE_LOSSES} consecutive losses today — trading stopped for the day.")

    # R5 — overtrading brake.
    if _state.trades_today >= MAX_TRADES_PER_DAY:
        return RuleVerdict(False, f"R5: Max {MAX_TRADES_PER_DAY} trades/day reached — overtrading brake.")

    # R6 — revenge-trade cooldown after a stop-loss on this symbol.
    last_sl = _state.last_sl_exit.get(symbol.upper())
    if last_sl is not None:
        elapsed_min = (now - last_sl).total_seconds() / 60.0
        if elapsed_min < SL_COOLDOWN_MINUTES:
            return RuleVerdict(
                False,
                f"R6: {symbol} hit stop-loss {elapsed_min:.0f} min ago — "
                f"cooldown {SL_COOLDOWN_MINUTES} min (revenge-trade brake)."
            )

    # R2 — live orders only during NSE market hours.
    if is_live and not _market_open(now):
        return RuleVerdict(False, "R2: NSE market is closed (09:15–15:30 IST Mon–Fri) — live order refused.")

    return RuleVerdict(True)


def compute_mandatory_stops(side: str, entry_price: float, atr: float) -> Dict[str, float]:
    """R3 + R4 — every trade gets an SL and target at entry. ATR-based; if ATR
    is unusable, falls back to 2% of price (still never naked)."""
    if atr is None or atr <= 0:
        atr = entry_price * 0.02 / SL_ATR_MULT
    sl_dist = atr * SL_ATR_MULT
    tgt_dist = max(atr * TARGET_ATR_MULT, sl_dist * MIN_REWARD_RISK)  # R4 floor
    if side == "BUY":
        return {"stop_loss": round(entry_price - sl_dist, 2),
                "target": round(entry_price + tgt_dist, 2)}
    return {"stop_loss": round(entry_price + sl_dist, 2),
            "target": round(entry_price - tgt_dist, 2)}


def record_entry():
    """Called after a successful entry (any mode)."""
    _state.roll_day_if_needed(_now_ist())
    _state.trades_today += 1


def record_exit(symbol: str, pnl: float, was_stop_loss: bool):
    """Called after any close. Feeds R6/R7 and triggers the R7 halt."""
    now = _now_ist()
    _state.roll_day_if_needed(now)
    if pnl <= 0:
        _state.consecutive_losses += 1
    else:
        _state.consecutive_losses = 0
    if was_stop_loss:
        _state.last_sl_exit[symbol.upper()] = now
    if _state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        logger.critical(
            f"R7 TRIPPED: {_state.consecutive_losses} consecutive losses — halting system for the day."
        )
        try:
            from .risk_manager import risk_manager
            risk_manager.trigger_system_halt(
                f"{_state.consecutive_losses} consecutive losing trades (R7 circuit breaker)"
            )
        except Exception as e:
            logger.error(f"R7 halt trigger failed: {e}")


def rules_status() -> dict:
    """Expose current rule state for the UI / API."""
    now = _now_ist()
    _state.roll_day_if_needed(now)
    return {
        "day": _state.day,
        "trades_today": _state.trades_today,
        "max_trades_per_day": MAX_TRADES_PER_DAY,
        "consecutive_losses": _state.consecutive_losses,
        "max_consecutive_losses": MAX_CONSECUTIVE_LOSSES,
        "sl_cooldown_minutes": SL_COOLDOWN_MINUTES,
        "symbols_in_cooldown": {
            s: round(max(0.0, SL_COOLDOWN_MINUTES - (now - t).total_seconds() / 60.0), 1)
            for s, t in _state.last_sl_exit.items()
            if (now - t).total_seconds() / 60.0 < SL_COOLDOWN_MINUTES
        },
        "market_open_now": _market_open(now),
        "system_halted": config.auto_trade == AutoTradeState.HALTED,
        "mandatory_sl_atr_mult": SL_ATR_MULT,
        "target_atr_mult": TARGET_ATR_MULT,
    }
