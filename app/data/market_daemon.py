import time
import threading
import logging
import yfinance as yf
from typing import Dict, Any, List

logger = logging.getLogger("elco.data.market_daemon")

class MarketDataDaemon:
    """
    A background worker that continuously fetches live market data
    (OHLC charts and Option Chains) and stores it in a thread-safe
    in-memory cache for the 18 Master Engines to query instantly.
    """
    def __init__(self, symbols: List[str], interval_seconds: int = 60):
        self.symbols = symbols
        self.interval_seconds = interval_seconds
        
        # Thread-safe cache
        self.cache: Dict[str, Any] = {
            "charts": {},
            "option_chains": {},
            "market_regime": None,
            "last_updated": None
        }
        self.lock = threading.Lock()
        
        # Threading controls
        self.is_running = False
        self.worker_thread = None

    def start(self):
        """Starts the background data fetching thread."""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._run_loop, daemon=True, name="MarketDataDaemonThread")
            self.worker_thread.start()
            logger.info("Market Data Daemon started in the background.")

    def stop(self):
        """Stops the background data fetching thread."""
        if self.is_running:
            self.is_running = False
            if self.worker_thread:
                self.worker_thread.join(timeout=2.0)
            logger.info("Market Data Daemon stopped.")

    def get_data(self) -> Dict[str, Any]:
        """Returns a safe copy of the current cached data."""
        with self.lock:
            return dict(self.cache)

    def _run_loop(self):
        """The main loop that runs in the background thread."""
        while self.is_running:
            try:
                self._fetch_latest_data()
            except Exception as e:
                logger.error(f"Error fetching market data in background: {e}")
                
            # Sleep for the designated interval before fetching again
            # We break the sleep into smaller chunks to allow quick termination on stop()
            for _ in range(self.interval_seconds):
                if not self.is_running:
                    break
                time.sleep(1)

    def _fetch_latest_data(self):
        """Fetches data using yfinance and updates the cache."""
        logger.debug("Fetching latest market data...")
        
        new_charts = {}
        new_option_chains = {}
        
        for symbol in self.symbols:
            try:
                ticker = yf.Ticker(symbol)
                
                # Fetch 1-minute chart data for the last day
                history = ticker.history(period="1d", interval="1m")
                if not history.empty:
                    new_charts[symbol] = history

                # Fetch Option Chain (nearest expiry)
                options_dates = ticker.options
                if options_dates:
                    nearest_expiry = options_dates[0]
                    opt_chain = ticker.option_chain(nearest_expiry)
                    
                    # Store both calls and puts
                    new_option_chains[symbol] = {
                        "expiry": nearest_expiry,
                        "calls": opt_chain.calls,
                        "puts": opt_chain.puts
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch data for {symbol}: {e}")

        # Update the thread-safe cache
        with self.lock:
            self.cache["charts"] = new_charts
            self.cache["option_chains"] = new_option_chains
            self.cache["last_updated"] = time.time()
            
            # Simple market regime proxy: Check if broader market (e.g., SPY or NIFTY) is up or down
            # If the first symbol is positive today, call it Bullish.
            if new_charts and self.symbols:
                first_sym = self.symbols[0]
                if first_sym in new_charts and not new_charts[first_sym].empty:
                    recent_data = new_charts[first_sym]
                    if len(recent_data) > 1:
                        open_px = recent_data['Open'].iloc[0]
                        close_px = recent_data['Close'].iloc[-1]
                        self.cache["market_regime"] = "Bullish" if close_px >= open_px else "Bearish"

        logger.info("Market Data cache updated successfully.")
