"""Auto-screener daemon — the full-market scan runs itself once every
trading day after NSE publishes the bhavcopy (~18:00-19:00 IST).

Each evening run: 2000+ NSE symbols → liquidity gate → top-300 scored →
results saved to screener_daily.json (survives restarts) → Telegram alert
with the top picks. The morning you wake up, yesterday's evening scan is
already waiting at GET /api/screener/auto/status.

Manual scans via /api/screener/market keep working independently.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("elco.screener_daemon")

IST = timezone(timedelta(hours=5, minutes=30))
RUN_AFTER_HHMM = (19, 7)          # bhavcopy is reliably up by then
CHECK_INTERVAL_SEC = 600          # poll clock every 10 min
RESULTS_PATH = Path(__file__).resolve().parent.parent / "screener_daily.json"


class ScreenerDaemon:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.last_error: Optional[str] = None

    # -- schedule ------------------------------------------------------------

    @staticmethod
    def _today_ist() -> str:
        return datetime.now(IST).strftime("%Y-%m-%d")

    def _last_run_day(self) -> str:
        try:
            if RESULTS_PATH.exists():
                return json.loads(RESULTS_PATH.read_text(encoding="utf-8")).get("run_day", "")
        except Exception:
            pass
        return ""

    def _should_run(self) -> bool:
        now = datetime.now(IST)
        if now.weekday() >= 5:              # weekend: no new bhavcopy
            return False
        past_time = (now.hour, now.minute) >= RUN_AFTER_HHMM
        return past_time and self._last_run_day() != self._today_ist()

    # -- work ----------------------------------------------------------------

    def run_scan(self) -> Dict[str, Any]:
        """One full-market scan; saves + alerts. Also callable on demand."""
        from .modules.stock_ranker import market_scan

        result = market_scan(top_n=15, max_symbols=300)
        payload = {
            "run_day": self._today_ist(),
            "run_at": datetime.now(IST).isoformat(timespec="seconds"),
            "result": result,
        }
        try:
            tmp = RESULTS_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
            import os
            os.replace(str(tmp), str(RESULTS_PATH))
        except Exception as e:
            logger.error(f"Screener results save failed: {e}")

        if not result.get("error"):
            longs = result.get("best_long") or []
            shorts = result.get("best_short") or []
            try:
                from .alerts import send_async
                msg = ["📊 <b>Daily market scan</b> "
                       f"({result.get('scored', 0)} stocks scored)"]
                if longs:
                    msg.append("🟢 Long: " + ", ".join(
                        f"{s['symbol']}({s['score']:+d})" for s in longs[:5]))
                if shorts:
                    msg.append("🔴 Short: " + ", ".join(
                        f"{s['symbol']}({s['score']:+d})" for s in shorts[:5]))
                msg.append("Screening only — hunt+validate before deploying.")
                send_async("\n".join(msg), kind="screener")
            except Exception:
                pass
        logger.info(f"Auto-screener run complete: scored={result.get('scored')}")
        return payload

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop():
            logger.info("Auto-screener daemon started (daily post-bhavcopy scan).")
            while not self._stop.is_set():
                try:
                    if self._should_run():
                        self.run_scan()
                except Exception as e:
                    self.last_error = str(e)
                    logger.error(f"Auto-screener failed: {e}")
                self._stop.wait(CHECK_INTERVAL_SEC)

        self._thread = threading.Thread(target=_loop, daemon=True, name="ScreenerDaemon")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def status(self) -> Dict[str, Any]:
        last: Dict[str, Any] = {}
        try:
            if RESULTS_PATH.exists():
                last = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            last = {"error": f"results unreadable: {e}"}
        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "schedule": f"daily after {RUN_AFTER_HHMM[0]:02d}:{RUN_AFTER_HHMM[1]:02d} IST (Mon-Fri)",
            "last_run_at": last.get("run_at"),
            "last_error": self.last_error,
            "last_result": last.get("result"),
        }


screener_daemon = ScreenerDaemon()
