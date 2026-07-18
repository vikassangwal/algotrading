"""Auto-hunt daemon — the validation pipeline runs itself on weekends.

Every Saturday (after 10:00 IST, once per weekend):
  1. Take the latest auto-screener results (best_long + best_short).
  2. Pick the top names NOT already in the deployed book (max HUNT_MAX).
  3. Run the full out-of-sample hunt (60%+ win-rate gate) on each.
  4. AUTO-DEPLOY whatever validates; report the rest as no-edge.
  5. Telegram summary either way.

Saturday because each hunt burns ~1-2 min of CPU per symbol and the market
is closed — the trading loops get the machine on weekdays.

The 60%+ out-of-sample gate is the same one manual hunts use: nothing
enters the book without held-out proof, automated or not.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("elco.hunt_daemon")

IST = timezone(timedelta(hours=5, minutes=30))
RUN_DAY = 5                     # Saturday (Mon=0)
RUN_AFTER_HOUR = 10             # 10:00 IST
CHECK_INTERVAL_SEC = 1800       # poll every 30 min
HUNT_MAX = 5                    # symbols per weekend run
MIN_WIN_RATE = 60.0
STATE_PATH = Path(__file__).resolve().parent.parent / "hunt_daemon.json"


class HuntDaemon:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.running_now = False
        self.last_error: Optional[str] = None

    # -- schedule ------------------------------------------------------------

    @staticmethod
    def _weekend_key() -> str:
        """Same key Sat+Sun so one run covers the whole weekend."""
        now = datetime.now(IST)
        sat = now - timedelta(days=(now.weekday() - 5) % 7)
        return sat.strftime("%Y-%m-%d")

    def _last_run_key(self) -> str:
        try:
            if STATE_PATH.exists():
                return json.loads(STATE_PATH.read_text(encoding="utf-8")).get("weekend", "")
        except Exception:
            pass
        return ""

    def _should_run(self) -> bool:
        now = datetime.now(IST)
        if now.weekday() < RUN_DAY:          # Mon-Fri: never
            return False
        if now.weekday() == RUN_DAY and now.hour < RUN_AFTER_HOUR:
            return False
        return self._last_run_key() != self._weekend_key()

    # -- candidate selection ---------------------------------------------------

    @staticmethod
    def _candidates(limit: int) -> List[str]:
        """Top screener names not already deployed (longs first, then shorts)."""
        from .screener_daemon import RESULTS_PATH
        from .strategy_runtime import list_deployed
        try:
            data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
            result = data.get("result") or {}
        except Exception:
            return []
        have = {d["symbol"] for d in list_deployed(active_only=False)}
        picks: List[str] = []
        for row in (result.get("best_long") or []) + (result.get("best_short") or []):
            sym = row.get("symbol")
            if sym and sym not in have and sym not in picks:
                picks.append(sym)
            if len(picks) >= limit:
                break
        return picks

    # -- work ------------------------------------------------------------------

    def run_hunt(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Hunt + auto-deploy. Callable on demand with explicit symbols."""
        from .modules.strategy_generator import hunt_validated
        from . import strategy_runtime as SR

        self.running_now = True
        try:
            syms = symbols or self._candidates(HUNT_MAX)
            if not syms:
                out = {"hunted": [], "deployed": [], "no_edge": [],
                       "note": "No fresh candidates (screener results missing or all top names already deployed)."}
            else:
                r = hunt_validated(syms, min_win_rate=MIN_WIN_RATE, years=4)
                deployed = []
                for b in r["book"]:
                    d = SR.deploy(b["name"], b["symbol"], b["params"])
                    te = b["test"]
                    deployed.append({
                        "id": d["id"], "symbol": b["symbol"], "name": b["name"],
                        "test_win_rate": te["win_rate_pct"], "test_pf": te["profit_factor"],
                        "test_trades": te["trades"],
                    })
                out = {"hunted": syms, "deployed": deployed, "no_edge": r["no_edge"],
                       "min_win_rate": MIN_WIN_RATE}

            payload = {"weekend": self._weekend_key(),
                       "run_at": datetime.now(IST).isoformat(timespec="seconds"),
                       "result": out}
            try:
                import os
                tmp = STATE_PATH.with_suffix(".tmp")
                tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
                os.replace(str(tmp), str(STATE_PATH))
            except Exception as e:
                logger.error(f"Hunt state save failed: {e}")

            try:
                from .alerts import send_async
                dep = out.get("deployed") or []
                lines = [f"🔎 <b>Weekend auto-hunt</b> ({len(out.get('hunted') or [])} scanned)"]
                if dep:
                    lines += [f"✅ Deployed: {d['symbol']} {d['name']} "
                              f"({d['test_win_rate']}% test)" for d in dep]
                else:
                    lines.append("Koi 60%+ edge validate nahi hua — book unchanged (that's honesty, not failure).")
                send_async("\n".join(lines), kind="hunt")
            except Exception:
                pass

            logger.info(f"Auto-hunt complete: {len(out.get('deployed') or [])} deployed.")
            return payload
        finally:
            self.running_now = False

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop():
            logger.info("Auto-hunt daemon started (weekend validation pipeline).")
            while not self._stop.is_set():
                try:
                    if self._should_run():
                        self.run_hunt()
                except Exception as e:
                    self.last_error = str(e)
                    logger.error(f"Auto-hunt failed: {e}")
                self._stop.wait(CHECK_INTERVAL_SEC)

        self._thread = threading.Thread(target=_loop, daemon=True, name="HuntDaemon")
        self._thread.start()

    def status(self) -> Dict[str, Any]:
        last: Dict[str, Any] = {}
        try:
            if STATE_PATH.exists():
                last = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            last = {"error": str(e)}
        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "hunting_right_now": self.running_now,
            "schedule": "Saturdays after 10:00 IST (once per weekend)",
            "last_run_at": last.get("run_at"),
            "last_result": last.get("result"),
            "last_error": self.last_error,
        }


hunt_daemon = HuntDaemon()
