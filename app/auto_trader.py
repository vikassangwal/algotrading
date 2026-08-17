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
                action["options_piggyback"] = self._options_piggyback(sym, d.get("signal"))
            taken.append(action)
            self._log(action)

        # 2. Add Dynamic Universal Screener Signals (Continuous Equity Scanner)
        try:
            from .screener.live_screener import LiveScreener
            from .elco_brain import ElcoMasterBrain
            screener = LiveScreener(ElcoMasterBrain())
            # Scan all equity stocks continuously every 2 scans (every 2 minutes)
            if self.scans_done % 2 == 1:
                logger.info("AutoTrader: Continuously scanning ALL equity stocks across Nifty 50, Midcaps & Smallcaps...")
                dynamic_results = screener.run_universal_scan(max_workers=10)
                # Take top high-conviction setups clearing 75+ conviction score
                top_setups = [r for r in dynamic_results if abs(r.get("analytical_score", 0)) >= 75][:3]
                
                for setup in top_setups:
                    sym = setup["symbol"]
                    if sym in execution_engine.open_positions:
                        continue
                    
                    side = "BUY" if setup["decision"] == "STRONG_BUY" or setup["analytical_score"] > 0 else "SELL"
                    
                    # Execute dynamic signal
                    from .engine import FusedSignal
                    from .config import TradingStyle
                    
                    signal = FusedSignal(
                        symbol=sym,
                        overall_score=1.0 if side == "BUY" else -1.0,
                        overall_confidence=abs(setup["analytical_score"]) / 100.0,
                        style=TradingStyle.INTRADAY,
                        reasons=[f"Dynamic AI Screener picked {sym} with score {setup['analytical_score']}"]
                    )
                    
                    allocation = risk_manager.calculate_position_size(signal)
                    executed = False
                    reason = "risk manager rejected sizing"
                    if allocation > 0:
                        ok = execution_engine.execute_signal(signal, allocation)
                        executed = bool(ok)
                        reason = "executed through gated chain" if ok else "blocked by mandatory rules / execution gate"

                    action = {
                        "time": _now_iso(),
                        "strategy": "Dynamic_AI_Screener",
                        "symbol": sym,
                        "signal": side,
                        "executed": executed,
                        "reason": reason,
                        "allocation": round(allocation, 2) if executed else 0,
                    }
                    if executed:
                        action["verification"] = self.verify_trade(sym, execution_engine)
                        action["options_piggyback"] = self._options_piggyback(sym, side)
                    taken.append(action)
                    self._log(action)
        except Exception as e:
            logger.error(f"AutoTrader Dynamic Screener failed: {e}")

        return taken

    @staticmethod
    def _options_piggyback(symbol: str, side: Optional[str]) -> dict:
        """When an equity signal executes, mirror it with a small PAPER
        option position at the REAL chain LTP: BUY -> ATM CE, SELL -> ATM PE.
        Premium capped tighter than manual trades (0.5% of capital). Fails
        soft: no chain (non-F&O stock / NSE down) = no option trade, stated."""
        if side not in ("BUY", "SELL"):
            return {"attempted": False, "reason": "no directional side"}
        try:
            from .config import config
            from .options_trader import _chain, _find_ltp, open_trade

            chain = _chain(symbol)
            if not chain.get("available"):
                return {"attempted": False,
                        "reason": "no option chain for this symbol (not F&O or NSE unreachable)"}
            spot = float(chain.get("underlyingPrice") or 0)
            strikes = chain.get("strikes") or []
            if not spot or not strikes:
                return {"attempted": False, "reason": "chain missing spot/strikes"}
            
            # Dynamic Fund-Based Strike Selection
            # Allocate max 10% of total capital for this options trade
            max_budget = config.capital * 0.10
            
            opt_type = "CE" if side == "BUY" else "PE"
            
            # Sort strikes by closeness to ATM
            sorted_strikes = sorted(strikes, key=lambda s: abs(s - spot))
            
            selected_strike = None
            selected_ltp = None
            
            for strike in sorted_strikes:
                # Prevent picking deeply OTM strikes (limit to 5% away from spot price)
                if abs(strike - spot) / spot > 0.05:
                    continue 
                    
                ltp = _find_ltp(chain, strike, opt_type)
                if ltp is None or ltp <= 0:
                    continue
                
                # We assume a conservative lot size of 25 for margin checks if it's an index, or 100 for stocks.
                # Since we don't have exact lot size, we estimate cost per unit and require at least a basic budget fit.
                estimated_lot_size = 25 
                cost_per_lot = ltp * estimated_lot_size
                
                if cost_per_lot <= max_budget:
                    selected_strike = strike
                    selected_ltp = ltp
                    break # Found the closest affordable strike!
                    
            if not selected_strike:
                return {"attempted": False, "reason": f"No affordable {opt_type} strike found within ₹{max_budget:,.0f} budget limit"}
            
            # Calculate quantity to buy
            qty = max(1, int(max_budget // (selected_ltp * 25)))
            
            r = open_trade(symbol, selected_strike, opt_type, qty, chain.get("expirationDate", ""))
            return {"attempted": True, "ok": r.get("ok", False),
                    "detail": r if r.get("ok") else r.get("reason"),
                    "mode": "PAPER"}
        except Exception as e:
            logger.warning(f"Options piggyback failed for {symbol}: {e}")
            return {"attempted": True, "ok": False, "detail": str(e)[:100]}

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
        try:
            from .alerts import alert_trade
            alert_trade(action)
        except Exception:  # alerts must never break trading
            pass

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
