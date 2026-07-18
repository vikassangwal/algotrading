"""AUTO-TRADER — automatic buy/sell from VALIDATED strategies, with
post-execution verification that the trade actually happened.

What it does, every scan (60s) during NSE market hours, ONLY while
config.auto_trade == ACTIVE:

  1. Evaluates every ACTIVE deployed strategy (the out-of-sample validated
     book) on fresh candles.
  2. When a strategy fires BUY/SELL and its regime gate passes, executes
     through the SAME chain as manual trades:
         Kelly sizing → mandatory rules R1-R7 → paper/live double gate.
     Auto mode gets NO shortcuts — R5 (max trades/day), R6 (cooldown) and
     R7 (loss streak halt) all apply and will stop a runaway loop.
  3. VERIFIES each execution and records the evidence:
         paper → position present in open_positions + journal entry exists
         live  → Dhan GET /orders/{id} status (CONFIRMED/PENDING/REJECTED)
     A trade that cannot be verified is logged as UNVERIFIED, never assumed.

Exits stay with PositionMonitor (30s SL/target sweeps). This loop only enters.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional

logger = logging.getLogger("elco.autotrader")

SCAN_INTERVAL_SEC = 60
IDLE_INTERVAL_SEC = 300
MAX_LOG = 50
IST = timezone(timedelta(hours=5, minutes=30))


def _now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= minutes <= (15 * 60 + 30)


class AutoTrader:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.scans_done = 0
        self.last_scan: Optional[str] = None
        self.actions: List[dict] = []      # rolling execution+verification log

    # -- lifecycle -------------------------------------------------------------

    def start(self, provider, execution_engine, risk_manager):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop():
            logger.info("Auto-trader thread started (acts only while auto_trade=ACTIVE).")
            while not self._stop.is_set():
                wait = IDLE_INTERVAL_SEC
                try:
                    from .config import config, AutoTradeState
                    if config.auto_trade == AutoTradeState.ACTIVE and _market_open():
                        self.scan_once(provider, execution_engine, risk_manager)
                        wait = SCAN_INTERVAL_SEC
                    elif _market_open():
                        wait = SCAN_INTERVAL_SEC  # armed check, auto off
                except Exception as e:
                    logger.error(f"Auto-trader scan crashed: {e}")
                self._stop.wait(wait)

        self._thread = threading.Thread(target=_loop, daemon=True, name="AutoTrader")
        self._thread.start()

    def stop(self):
        self._stop.set()

    # -- core ------------------------------------------------------------------

    def scan_once(self, provider, execution_engine, risk_manager) -> List[dict]:
        """One pass over the validated book. Returns actions taken this scan."""
        from .strategy_runtime import evaluate_deployed, execute_deployed

        self.scans_done += 1
        self.last_scan = _now_iso()
        taken: List[dict] = []

        for d in evaluate_deployed(provider):
            if not d.get("tradeable"):
                continue
            sym = d["symbol"]
            if sym in execution_engine.open_positions:
                continue  # one position per symbol — never average in

            result = execute_deployed(provider, execution_engine, risk_manager, d["id"])
            action = {
                "time": _now_iso(),
                "strategy": d["name"],
                "symbol": sym,
                "signal": d.get("signal"),
                "executed": result.get("executed", False),
                "reason": result.get("reason"),
                "allocation": result.get("allocation", 0),
            }
            if result.get("executed"):
                action["verification"] = self.verify_trade(sym, execution_engine)
            taken.append(action)
            self._log(action)

        return taken

    # -- verification ------------------------------------------------------------

    def verify_trade(self, symbol: str, execution_engine) -> dict:
        """Did the buy/sell ACTUALLY happen? Evidence, not assumption."""
        from .config import config

        trade = execution_engine.open_positions.get(symbol)
        if trade is None:
            return {"status": "FAILED", "detail": "No position found after execution — trade did not stick."}

        checks = {
            "position_open": True,
            "in_journal": any(t.trade_id == trade.trade_id for t in execution_engine.journal),
            "in_database": self._db_has_open_trade(symbol),
            "has_mandatory_sl": bool(trade.stop_loss) and bool(trade.target),
        }

        if config.paper_mode:
            ok = all(checks.values())
            return {
                "status": "CONFIRMED_PAPER" if ok else "PARTIAL",
                "mode": "paper",
                "checks": checks,
                "entry_price": trade.entry_price,
                "qty": trade.qty,
                "detail": ("Paper trade recorded in position book + journal + DB."
                           if ok else f"Some records missing: {checks}"),
            }

        # LIVE: ask the broker what actually happened to the order.
        order_id = getattr(trade, "broker_order_id", "") or ""
        if not order_id:
            return {"status": "UNVERIFIED", "mode": "live", "checks": checks,
                    "detail": "Live trade has no broker order id recorded — cannot confirm with Dhan."}
        try:
            rc = getattr(execution_engine.provider, "rest_client", None)
            status = rc.get_order_status(order_id) if rc else None
        except Exception as e:
            status = None
            logger.warning(f"Order verification failed for {order_id}: {e}")
        if status is None:
            return {"status": "UNVERIFIED", "mode": "live", "order_id": order_id, "checks": checks,
                    "detail": "Dhan order-status lookup failed; retry via /api/trades/verify."}
        return {
            "status": status["status"],  # CONFIRMED / PENDING / REJECTED / CANCELLED
            "mode": "live",
            "order_id": order_id,
            "broker_raw_status": status["raw_status"],
            "filled_qty": status["filled_qty"],
            "avg_price": status["avg_price"],
            "checks": checks,
        }

    def verify_all(self, execution_engine) -> dict:
        """Verify every OPEN position now (also exposed as an endpoint)."""
        results = {
            sym: self.verify_trade(sym, execution_engine)
            for sym in list(execution_engine.open_positions.keys())
        }
        return {
            "open_positions": len(results),
            "verified": results,
            "note": "CONFIRMED_PAPER/CONFIRMED = trade demonstrably happened; "
                    "UNVERIFIED/FAILED = do not assume it did.",
        }

    # -- helpers -----------------------------------------------------------------

    @staticmethod
    def _db_has_open_trade(symbol: str) -> bool:
        try:
            from .db import SessionLocal, TradeRecord as DBTrade
            db = SessionLocal()
            try:
                return db.query(DBTrade).filter(
                    DBTrade.symbol == symbol, DBTrade.status == "OPEN"
                ).count() > 0
            finally:
                db.close()
        except Exception:
            return False

    def _log(self, action: dict):
        self.actions.append(action)
        if len(self.actions) > MAX_LOG:
            self.actions = self.actions[-MAX_LOG:]
        logger.info(f"AUTO-TRADE action: {action}")

    def status(self) -> dict:
        from .config import config
        return {
            "thread_running": self._thread is not None and self._thread.is_alive(),
            "auto_trade_state": str(config.auto_trade.value),
            "market_open": _market_open(),
            "scan_interval_sec": SCAN_INTERVAL_SEC,
            "scans_done": self.scans_done,
            "last_scan": self.last_scan,
            "recent_actions": self.actions[-10:],
        }


auto_trader = AutoTrader()
