"""Background position monitor — makes the mandatory stop-loss REAL.

A stop-loss that only fires when someone calls an API endpoint is not a
stop-loss. This daemon thread sweeps every open position at a fixed interval
during NSE market hours and closes anything that hit its stop or target
(via command_center.auto_manage_positions — the same logic the dashboard
uses, so behavior is identical either way).

Outside market hours it idles cheaply (prices aren't moving; nothing to do).
Starts automatically with the app (see main.py startup hook).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("elco.position_monitor")

SWEEP_INTERVAL_SEC = 30        # in-hours sweep cadence
IDLE_INTERVAL_SEC = 300        # off-hours nap
IST = timezone(timedelta(hours=5, minutes=30))


def _market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= minutes <= (15 * 60 + 30)


class PositionMonitor:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.last_sweep: str | None = None
        self.last_actions: list = []
        self.sweeps_done = 0

    def start(self, engine, provider, execution_engine):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop():
            from .command_center import auto_manage_positions
            logger.info("Position monitor started (30s sweeps during market hours).")
            while not self._stop.is_set():
                try:
                    if execution_engine.open_positions and _market_open():
                        actions = auto_manage_positions(engine, provider, execution_engine)
                        self.sweeps_done += 1
                        self.last_sweep = datetime.now(IST).isoformat(timespec="seconds")
                        if actions:
                            self.last_actions = actions
                            logger.info(f"Monitor auto-exits: {actions}")
                        wait = SWEEP_INTERVAL_SEC
                    elif _market_open():
                        wait = SWEEP_INTERVAL_SEC  # no positions; cheap re-check
                    else:
                        wait = IDLE_INTERVAL_SEC   # market closed
                except Exception as e:
                    logger.error(f"Position monitor sweep failed: {e}")
                    wait = SWEEP_INTERVAL_SEC
                self._stop.wait(wait)
            logger.info("Position monitor stopped.")

        self._thread = threading.Thread(target=_loop, daemon=True, name="PositionMonitor")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def status(self) -> dict:
        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "market_open": _market_open(),
            "sweep_interval_sec": SWEEP_INTERVAL_SEC,
            "sweeps_done": self.sweeps_done,
            "last_sweep": self.last_sweep,
            "last_actions": self.last_actions,
        }


position_monitor = PositionMonitor()
