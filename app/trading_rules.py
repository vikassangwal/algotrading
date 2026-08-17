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
  R8  Daily loss limit checked DIRECTLY at entry (defense in depth — the
      risk manager also halts, but no entry may even be attempted past it).
  R9  Max concurrent open positions (concentration brake).

Exit discipline (enforced by command_center.auto_manage_positions):
  D1  Breakeven move: after +1R in favor, SL moves to entry — a winner is
      never allowed to become a full loser.
  D2  Trailing stop: after +1.5R, SL trails 1R behind the peak. Stops only
      ever TIGHTEN, never loosen.
  D3  Time stop: positions older than TIME_STOP_DAYS are closed — capital
      is not left parked in trades that go nowhere.
  D4  Live EOD square-off: live positions (INTRADAY product at the broker)
      are force-closed at 15:15 IST — never carried into broker auto-square.

Position-size, exposure, and daily-loss rules already live in RiskManager
(calculate_position_size) — these are the EXECUTION-level rules that complete
the chain.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict

from .config import config, AutoTradeState

logger = logging.getLogger("elco.rules")

IST = timezone(timedelta(hours=5, minutes=30))

# --- Tunables (kept conservative; can move to config later) ------------------
MAX_TRADES_PER_DAY = 10
SL_COOLDOWN_MINUTES = 30          # no re-entry on a symbol this soon after a SL hit
MAX_CONSECUTIVE_LOSSES = 3        # third straight loser halts the day
MIN_REWARD_RISK = 2.0             # target distance must be >= 2x SL distance (1:2 RR minimum)
SL_ATR_MULT = 4.0                 # mandatory SL distance
TARGET_ATR_MULT = 0.25            # default target
MAX_OPEN_POSITIONS = 3            # R9: concentration brake
# Exit discipline (D1-D4), consumed by command_center.auto_manage_positions:
BREAKEVEN_AT_R = 1.0              # D1: +1R in favor -> SL to entry
TRAIL_START_R = 1.5               # D2: +1.5R -> trail SL 1R behind peak
TIME_STOP_DAYS = 10               # D3: close positions older than this
EOD_SQUARE_OFF_HHMM = (15, 15)    # D4: live INTRADAY square-off time (IST)


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


def check_entry_rules(symbol: str, is_live: bool,
                      open_positions_count: int = 0) -> RuleVerdict:
    """R1, R2, R5-R9 — called by execute_signal BEFORE placing anything."""
    now = _now_ist()
    _state.roll_day_if_needed(now)

    # R9 — concentration brake: never more than MAX_OPEN_POSITIONS at once.
    if open_positions_count >= MAX_OPEN_POSITIONS:
        return RuleVerdict(
            False,
            f"R9: {open_positions_count} positions already open — max "
            f"{MAX_OPEN_POSITIONS} concurrent positions (concentration brake)."
        )

    # R8 — daily loss limit checked directly at entry (defense in depth).
    try:
        from .risk_manager import risk_manager
        from .config import config as _cfg
        max_daily_loss = _cfg.capital * (_cfg.risk.daily_loss_limit_pct / 100.0)
        if risk_manager.daily_pnl <= -max_daily_loss:
            return RuleVerdict(
                False,
                f"R8: daily loss ₹{-risk_manager.daily_pnl:,.0f} has hit the "
                f"limit (₹{max_daily_loss:,.0f}) — no more entries today."
            )
    except Exception as e:
        logger.warning(f"R8 daily-loss check unavailable ({e}) — continuing with other rules.")

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


def compute_mandatory_stops(side: str, entry_price: float, atr: float, style: str = "INTRADAY", confidence: float = 0.75) -> Dict[str, float]:
    """R3 + R4 — every trade gets an SL and target at entry. ATR-based.
    Dynamically adjusts Risk-Reward based on Trading Style and AI Confidence."""
    
    # Default fallback multipliers
    dyn_sl_mult = SL_ATR_MULT
    dyn_tgt_mult = TARGET_ATR_MULT
    
    style_upper = (style or "INTRADAY").upper()
    
    if style_upper == "SCALPING":
        dyn_sl_mult = 1.0
        dyn_tgt_mult = 2.0   # RR 1:2 (User enforced minimum)
    elif style_upper == "INTRADAY":
        dyn_sl_mult = 1.5
        dyn_tgt_mult = 3.0   # RR 1:2
    elif style_upper == "SWING":
        dyn_sl_mult = 2.0
        dyn_tgt_mult = 6.0   # RR 1:3
    elif style_upper == "POSITION":
        dyn_sl_mult = 3.0
        dyn_tgt_mult = 12.0  # RR 1:4
        
    # Scale target slightly based on AI confidence (higher confidence -> stretch target by up to 20%)
    if confidence > 0.8:
        dyn_tgt_mult *= 1.2
        
    if atr is None or atr <= 0:
        atr = entry_price * 0.02 / dyn_sl_mult
        
    sl_dist = atr * dyn_sl_mult
    tgt_dist = max(atr * dyn_tgt_mult, sl_dist * MIN_REWARD_RISK)  # R4 floor
    
    if side == "BUY":
        return {"stop_loss": round(entry_price - sl_dist, 2),
                "target": round(entry_price + tgt_dist, 2)}
    return {"stop_loss": round(entry_price + sl_dist, 2),
            "target": round(entry_price - tgt_dist, 2)}


def record_entry():
    """Called after a successful entry (any mode)."""
    _state.roll_day_if_needed(_now_ist())
    _state.trades_today += 1
    _persist()


def _persist():
    """Rule state must survive restarts — a restart is not a rule reset."""
    try:
        from .state_store import persist_all
        persist_all()
    except Exception:  # persistence must never block trading logic
        pass


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
    _persist()


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
        "max_open_positions": MAX_OPEN_POSITIONS,
        "exit_discipline": {
            "breakeven_at_r": BREAKEVEN_AT_R,
            "trail_start_r": TRAIL_START_R,
            "time_stop_days": TIME_STOP_DAYS,
            "live_eod_square_off": f"{EOD_SQUARE_OFF_HHMM[0]:02d}:{EOD_SQUARE_OFF_HHMM[1]:02d} IST",
        },
    }
