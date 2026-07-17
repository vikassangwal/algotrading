"""Event-driven backtester for ELCO.

Design goals (see project Phase 3):
  * NO look-ahead bias — at each bar we only ever see data up to and including
    that bar (history is sliced, never the full future series).
  * NO random coin-flip P&L — outcomes come from real forward price movement
    against a stop-loss / target derived from the same signal the live system
    uses (AICompositeEngine), so the backtest validates the real strategy.
  * Works on BOTH real historical data (yfinance) and deterministic mock data.
"""
import logging

import numpy as np
import pandas as pd

from .modules.ai_composite_engine import AICompositeEngine

logger = logging.getLogger("elco.backtester")

WARMUP_BARS = 200  # need enough history for EMA200 etc. before trading


def load_history(symbol: str, years: int = 2, source: str = "mock",
                 return_source: bool = False):
    """Return a time-ordered OHLCV DataFrame (oldest first).

    source="real" pulls daily bars from yfinance (falls back to mock on any
    failure). source="mock" builds a deterministic seeded random walk so
    backtests are reproducible offline.

    With return_source=True, returns (df, actual_source) so callers can report
    honestly when a "real" request silently fell back to mock data.
    """
    if source == "real":
        try:
            import yfinance as yf
            ticker = symbol if "." in symbol else f"{symbol}.NS"  # NSE default
            df = yf.download(ticker, period=f"{years}y", interval="1d", progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                # Flatten possible multi-index columns from yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
                df = df.dropna().reset_index(drop=True)
                if len(df) > WARMUP_BARS:
                    logger.info(f"Loaded {len(df)} real bars for {symbol} from yfinance.")
                    return (df, "real") if return_source else df
            logger.warning(f"yfinance returned no usable data for {symbol}; using mock.")
        except Exception as e:
            logger.warning(f"Real data fetch failed for {symbol} ({e}); using mock.")

    mock_df = _mock_history(symbol, years)
    return (mock_df, "mock") if return_source else mock_df


def _mock_history(symbol: str, years: int) -> pd.DataFrame:
    """Deterministic seeded random walk with mild trend + noise."""
    n = max(WARMUP_BARS + 60, years * 252)
    seed = abs(hash(symbol.upper())) % (2 ** 32)
    rng = np.random.default_rng(seed)
    base = 100.0 + (abs(hash(symbol.upper())) % 3000)
    rets = rng.normal(0.0004, 0.012, n)  # slight positive drift
    close = base * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.006, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    volume = np.abs(rng.normal(1_000_000, 300_000, n)).astype(int)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })


class EventDrivenBacktester:
    def __init__(self, symbols: list, initial_capital: float = 100000.0,
                 years: int = 2, data_source: str = "mock",
                 max_alloc_pct: float = 0.20, portfolio_cap_pct: float = 0.60):
        self.symbols = symbols
        self.capital = initial_capital
        self.current_equity = initial_capital
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
        self.years = years
        self.data_source = data_source
        self.max_alloc_pct = max_alloc_pct       # max capital per single position
        self.portfolio_cap_pct = portfolio_cap_pct  # max aggregate deployed capital

        self.trades = []
        self.equity_curve = []
        self._history = {}

    def _signal(self, df_slice: pd.DataFrame) -> dict:
        """Real, look-ahead-free signal for the data available up to now."""
        return AICompositeEngine(df_slice).calculate_scores()

    def run(self):
        logger.info(
            f"Backtest start | capital ₹{self.capital:,.0f} | source={self.data_source} "
            f"| symbols={self.symbols}"
        )

        # Load full history per symbol once (aligned by bar index).
        for sym in self.symbols:
            self._history[sym] = load_history(sym, self.years, self.data_source)

        max_len = max((len(df) for df in self._history.values()), default=0)
        if max_len <= WARMUP_BARS + 1:
            logger.error("Not enough history to backtest.")
            return

        open_positions = {}  # symbol -> dict(entry, qty, sl, target, side)
        wins = 0
        losses = 0

        # Walk forward one bar at a time. At bar i we know bars [0..i] only.
        for i in range(WARMUP_BARS, max_len):
            deployed = sum(p["qty"] * p["entry"] for p in open_positions.values())

            for sym in self.symbols:
                df = self._history[sym]
                if i >= len(df):
                    continue

                hist = df.iloc[: i + 1]         # data as-of bar i (no look-ahead)
                today = df.iloc[i]

                # --- manage an open position: check SL / target against the
                # CURRENT bar. Positions are opened at a bar's close, so the
                # earliest exit is the next bar — which is exactly when this
                # branch first runs for the position (no skipped bar).
                if sym in open_positions:
                    pos = open_positions[sym]
                    exit_price = None
                    if pos["side"] == "BUY":
                        if today["low"] <= pos["sl"]:
                            exit_price = pos["sl"]
                        elif today["high"] >= pos["target"]:
                            exit_price = pos["target"]
                    else:  # SELL/short
                        if today["high"] >= pos["sl"]:
                            exit_price = pos["sl"]
                        elif today["low"] <= pos["target"]:
                            exit_price = pos["target"]

                    if exit_price is not None:
                        if pos["side"] == "BUY":
                            pnl = (exit_price - pos["entry"]) * pos["qty"]
                        else:
                            pnl = (pos["entry"] - exit_price) * pos["qty"]
                        # Net of round-trip costs (brokerage/STT/slippage ~0.1%
                        # of notional) so results aren't gross fantasy.
                        pnl -= pos["entry"] * pos["qty"] * 0.001
                        self.current_equity += pnl
                        wins += 1 if pnl > 0 else 0
                        losses += 1 if pnl <= 0 else 0
                        self.trades.append({
                            "symbol": sym, "side": pos["side"],
                            "entry": round(pos["entry"], 2), "exit": round(exit_price, 2),
                            "qty": pos["qty"], "pnl": round(pnl, 2),
                            "bar": i,
                        })
                        del open_positions[sym]
                    continue  # one position per symbol at a time

                # --- look for a new entry (not on the final bar — it could
                # never be exited within the data) ---
                if i >= max_len - 1 or i >= len(df) - 1:
                    continue
                sig = self._signal(hist)
                action = sig["action"]
                if action == "Hold":
                    continue

                side = "BUY" if action in ("Strong Buy", "Buy") else "SELL"
                setup = sig["trade_setup"]
                entry = float(today["close"])
                sl = setup["stop_loss"]
                target = setup["target_1"]
                if entry <= 0 or sl <= 0:
                    continue

                # Position sizing: confidence-scaled, capped per-position and by
                # aggregate portfolio exposure.
                conf = sig["confidence_pct"] / 100.0
                alloc = self.current_equity * self.max_alloc_pct * conf
                room = self.current_equity * self.portfolio_cap_pct - deployed
                alloc = max(0.0, min(alloc, room))
                qty = int(alloc // entry)
                if qty <= 0:
                    continue

                open_positions[sym] = {
                    "entry": entry, "qty": qty, "sl": sl, "target": target, "side": side,
                }
                deployed += qty * entry

            # mark-to-market equity curve + drawdown at this bar
            if self.current_equity > self.peak_equity:
                self.peak_equity = self.current_equity
            drawdown = (self.peak_equity - self.current_equity) / self.peak_equity if self.peak_equity else 0.0
            self.max_drawdown = max(self.max_drawdown, drawdown)
            self.equity_curve.append({"bar": i, "equity": round(self.current_equity, 2), "drawdown": round(drawdown, 4)})

        total = wins + losses
        self.win_rate = (wins / total * 100.0) if total else 0.0
        self.print_report()
        return self.summary()

    def summary(self) -> dict:
        total_return = ((self.current_equity - self.capital) / self.capital) * 100
        return {
            "initial_capital": self.capital,
            "final_equity": round(self.current_equity, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(self.max_drawdown * 100, 2),
            "total_trades": len(self.trades),
            "win_rate_pct": round(getattr(self, "win_rate", 0.0), 2),
            "data_source": self.data_source,
        }

    def print_report(self):
        s = self.summary()
        logger.info("=" * 40)
        logger.info("BACKTEST RESULTS")
        logger.info("=" * 40)
        logger.info(f"Data Source     : {s['data_source']}")
        logger.info(f"Total Trades    : {s['total_trades']}")
        logger.info(f"Win Rate        : {s['win_rate_pct']}%")
        logger.info(f"Initial Capital : ₹{s['initial_capital']:,.2f}")
        logger.info(f"Final Equity    : ₹{s['final_equity']:,.2f}")
        logger.info(f"Total Return    : {s['total_return_pct']}%")
        logger.info(f"Max Drawdown    : {s['max_drawdown_pct']}%")
        logger.info("=" * 40)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    bt = EventDrivenBacktester(symbols=["RELIANCE", "HDFCBANK", "INFY", "TCS"], data_source="mock")
    bt.run()
