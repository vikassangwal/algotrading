import time
import threading
import logging
import urllib.request

logger = logging.getLogger("elco.keep_alive")

LIVE_URL = "https://elco-backend.onrender.com/healthz"

class KeepAliveDaemon:
    def __init__(self):
        self._thread = None
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("KeepAlive daemon started (pinging every 8 minutes)")

    def _loop(self):
        # Initial sleep before first ping to allow server startup to complete
        time.sleep(30)
        while self._running:
            try:
                req = urllib.request.Request(LIVE_URL, headers={"User-Agent": "ELCO-KeepAlive/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info("Self-ping keep-alive successful (200 OK)")
            except Exception as e:
                logger.warning(f"Keep-alive self-ping failed: {e}")
                
            # Sleep 8 minutes (480 seconds) -> well under Render's 15-minute timeout
            for _ in range(480):
                if not self._running:
                    break
                time.sleep(1)

keep_alive_daemon = KeepAliveDaemon()
