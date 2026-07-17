"""Concrete, named trading strategies + an honest backtest harness.

Each strategy is a set of explicit entry rules over REAL indicators. Given an
as-of OHLCV frame (oldest->newest), a strategy returns a signal for its LAST
bar only — so walking the frame forward one row at a time is look-ahead free.

The harness reports the metrics that actually matter, not just win rate:
  * win_rate      — % of closed trades that were profitable
  * profit_factor — gross profit / gross loss  (>1 means edge)
  * expectancy    — average P&L per trade (in R multiples)
  * sharpe        — annualized, on per-trade returns
  * max_drawdown  — worst peak-to-trough on the equity curve

IMPORTANT HONESTY NOTE: a real, tradable strategy almost never sustains an 80%+
win rate. This harness reports whatever the data produces. It flags a strategy
as "recommended" based on a positive edge (profit factor and expectancy), NOT on
hitting an arbitrary win-rate target — because a high win rate alone does not
mean a strategy is profitable.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_supertrend,
    calculate_bollinger_bands,
)

logger = logging.getLogger("elco.strategies")

# Trades entered when a signal fires. SL/target are ATR multiples of the entry.
DEFAULT_SL_ATR = 1.5
DEFAULT_TARGET_ATR = 3.0  # 2:1 reward:risk

# Round-trip transaction cost as a fraction of notional: brokerage + STT +
# exchange charges + slippage for an Indian discount broker. Applied to EVERY
# backtested trade so reported edges are net of costs, not gross fantasy.
DEFAULT_COST_PCT = 0.001  # 0.1% round trip


def _atr(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    if pd.isna(atr):
        m = tr.mean()
        atr = float(m) if not pd.isna(m) else 0.0
    return float(atr)


# --- Strategy signal functions -------------------------------------------------
# Each returns "BUY", "SELL", or None for the LAST row of the given frame.

def ema_trend_crossover(df: pd.DataFrame) -> Optional[str]:
    """Trend following: fast EMA(20) crossing slow EMA(50)."""
    if len(df) < 55:
        return None
    fast = calculate_ema(df["close"], 20)
    slow = calculate_ema(df["close"], 50)
    if fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
        return "BUY"
    if fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
        return "SELL"
    return None


def rsi_mean_reversion(df: pd.DataFrame) -> Optional[str]:
    """Mean reversion: enter when RSI(14) exits oversold/overbought extremes."""
    if len(df) < 20:
        return None
    rsi = calculate_rsi(df["close"], 14)
    if rsi.iloc[-2] < 30 and rsi.iloc[-1] >= 30:
        return "BUY"
    if rsi.iloc[-2] > 70 and rsi.iloc[-1] <= 70:
        return "SELL"
    return None


def donchian_breakout(df: pd.DataFrame, window: int = 20) -> Optional[str]:
    """Breakout: close breaks the prior N-bar high (long) or low (short)."""
    if len(df) < window + 2:
        return None
    prior_high = df["high"].iloc[-(window + 1):-1].max()
    prior_low = df["low"].iloc[-(window + 1):-1].min()
    close = df["close"].iloc[-1]
    if close > prior_high:
        return "BUY"
    if close < prior_low:
        return "SELL"
    return None


def macd_momentum(df: pd.DataFrame) -> Optional[str]:
    """Momentum: MACD line crossing its signal line."""
    if len(df) < 40:
        return None
    ema12 = calculate_ema(df["close"], 12)
    ema26 = calculate_ema(df["close"], 26)
    macd = ema12 - ema26
    signal = calculate_ema(macd, 9)
    if macd.iloc[-2] <= signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]:
        return "BUY"
    if macd.iloc[-2] >= signal.iloc[-2] and macd.iloc[-1] < signal.iloc[-1]:
        return "SELL"
    return None


def supertrend_flip(df: pd.DataFrame) -> Optional[str]:
    """Trend: close crossing the Supertrend line.

    Uses the price-vs-line relationship directly rather than the indicator's
    Direction column (whose sign convention has been flagged as unreliable).
    """
    if len(df) < 20:
        return None
    st = calculate_supertrend(df)["Supertrend"]
    close = df["close"]
    prev_above = close.iloc[-2] > st.iloc[-2]
    now_above = close.iloc[-1] > st.iloc[-1]
    if not prev_above and now_above:
        return "BUY"
    if prev_above and not now_above:
        return "SELL"
    return None


def bollinger_reversion(df: pd.DataFrame) -> Optional[str]:
    """Mean reversion: price closing back inside the Bollinger bands."""
    if len(df) < 25:
        return None
    bb = calculate_bollinger_bands(df["close"], 20, 2.0)
    close = df["close"]
    if close.iloc[-2] < bb["Lower_Band"].iloc[-2] and close.iloc[-1] >= bb["Lower_Band"].iloc[-1]:
        return "BUY"
    if close.iloc[-2] > bb["Upper_Band"].iloc[-2] and close.iloc[-1] <= bb["Upper_Band"].iloc[-1]:
        return "SELL"
    return None


STRATEGIES: dict[str, Callable[[pd.DataFrame], Optional[str]]] = {
    "EMA Trend Crossover": ema_trend_crossover,
    "RSI Mean Reversion": rsi_mean_reversion,
    "Donchian Breakout": donchian_breakout,
    "MACD Momentum": macd_momentum,
    "Supertrend Flip": supertrend_flip,
    "Bollinger Reversion": bollinger_reversion,
}


@dataclass
class StrategyResult:
    name: str
    total_trades: int
    win_rate: float          # %
    profit_factor: Optional[float]
    expectancy_r: float      # avg P&L per trade in R (risk) multiples
    sharpe: float
    max_drawdown_pct: float
    total_return_pct: float
    recommended: bool        # positive edge (PF>1.3 and expectancy>0)

    def to_dict(self) -> dict:
        # JSON has no Infinity: PF=inf (zero losing trades) serializes as the
        # string "inf" so the API stays valid JSON without hiding the result.
        if self.profit_factor is None:
            pf = None
        elif math.isinf(self.profit_factor):
            pf = "inf"
        else:
            pf = round(self.profit_factor, 2)
        return {
            "name": self.name,
            "total_trades": self.total_trades,
            "win_rate_pct": round(self.win_rate, 1),
            "profit_factor": pf,
            "expectancy_r": round(self.expectancy_r, 3),
            "sharpe": round(self.sharpe, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "recommended": self.recommended,
        }


def backtest_strategy(
    name: str,
    signal_fn: Callable[[pd.DataFrame], Optional[str]],
    df: pd.DataFrame,
    warmup: int = 60,
    sl_atr: float = DEFAULT_SL_ATR,
    target_atr: float = DEFAULT_TARGET_ATR,
    cost_pct: float = DEFAULT_COST_PCT,
) -> StrategyResult:
    """Walk `df` forward one bar at a time; one open position at a time.

    Entry at the signal bar's close; exits filled against the NEXT bar's
    high/low (SL or target). No look-ahead: the signal only ever sees bars
    up to and including the current one.
    """
    df = df.reset_index(drop=True)
    n = len(df)
    trade_r = []          # per-trade return in R multiples (risk units)
    equity = 1.0          # normalized equity, 1R risked per trade * 1% notional
    peak = 1.0
    max_dd = 0.0
    wins = 0
    gross_profit = 0.0
    gross_loss = 0.0

    position = None       # dict(side, entry, sl, target, risk)

    # Indicators only need bounded history — cap the as-of slice so the walk is
    # O(n·window) instead of O(n²). 250 bars comfortably covers EMA(50)/MACD.
    LOOKBACK = 250

    for i in range(warmup, n):
        cur = df.iloc[i]

        # --- manage an open position first: the bar AFTER entry (and every
        # bar since) is checked against SL/target. Entry happens at bar close,
        # so the earliest possible exit is the very next bar — bar `i` here.
        if position is not None:
            exit_price = None
            if position["side"] == "BUY":
                if cur["low"] <= position["sl"]:
                    exit_price = position["sl"]
                elif cur["high"] >= position["target"]:
                    exit_price = position["target"]
            else:
                if cur["high"] >= position["sl"]:
                    exit_price = position["sl"]
                elif cur["low"] <= position["target"]:
                    exit_price = position["target"]

            if exit_price is not None:
                if position["side"] == "BUY":
                    pnl = exit_price - position["entry"]
                else:
                    pnl = position["entry"] - exit_price
                # Net of round-trip transaction costs (brokerage/STT/slippage):
                # cost_pct of the entry notional, expressed per share here.
                pnl -= position["entry"] * cost_pct
                r = pnl / position["risk"] if position["risk"] > 0 else 0.0
                trade_r.append(r)
                if r > 0:
                    wins += 1
                    gross_profit += r
                else:
                    gross_loss += -r
                # Risk 1% of equity per trade -> equity compounds by r * 1%.
                equity *= (1 + 0.01 * r)
                peak = max(peak, equity)
                dd = (peak - equity) / peak if peak else 0.0
                max_dd = max(max_dd, dd)
                position = None
            continue

        if i >= n - 1:
            break  # last bar: a fresh entry could never be exited

        hist = df.iloc[max(0, i + 1 - LOOKBACK): i + 1]
        side = signal_fn(hist)
        if side not in ("BUY", "SELL"):
            continue
        entry = float(hist["close"].iloc[-1])
        atr = _atr(hist)
        if atr <= 0 or entry <= 0:
            continue
        risk = atr * sl_atr
        if side == "BUY":
            sl = entry - risk
            target = entry + atr * target_atr
        else:
            sl = entry + risk
            target = entry - atr * target_atr
        position = {"side": side, "entry": entry, "sl": sl, "target": target, "risk": risk}

    total = len(trade_r)
    win_rate = 100.0 * wins / total if total else 0.0
    # PF semantics: no trades -> None; wins but zero losses -> inf (a REAL,
    # best-possible result — kept as inf so it ranks first, serialized as null).
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = math.inf
    else:
        profit_factor = None
    expectancy = float(np.mean(trade_r)) if total else 0.0

    # Sharpe on per-trade R returns, annualized by average trades/year (~252 bars/yr).
    if total > 1 and np.std(trade_r) > 0:
        trades_per_year = total / max(1.0, (n - warmup) / 252.0)
        sharpe = float(np.mean(trade_r) / np.std(trade_r) * math.sqrt(trades_per_year))
    else:
        sharpe = 0.0

    total_return = (equity - 1.0) * 100.0

    # Positive-edge gate — NOT a win-rate target. PF and expectancy must be real.
    # PF=inf (zero losing trades over >=20 trades) is the strongest possible edge.
    recommended = (
        total >= 20
        and profit_factor is not None
        and profit_factor >= 1.3
        and expectancy > 0
    )

    return StrategyResult(
        name=name,
        total_trades=total,
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy_r=expectancy,
        sharpe=sharpe,
        max_drawdown_pct=max_dd * 100.0,
        total_return_pct=total_return,
        recommended=recommended,
    )


def rank_strategies(df: pd.DataFrame) -> list[dict]:
    """Backtest every strategy on `df` and return them ranked by profit factor.

    Ranks by real edge (profit factor, then expectancy) — never by win rate.
    """
    results = []
    for name, fn in STRATEGIES.items():
        try:
            results.append(backtest_strategy(name, fn, df))
        except Exception as e:
            logger.warning(f"Strategy '{name}' failed to backtest: {e}")
    results.sort(
        key=lambda r: (
            r.profit_factor if r.profit_factor is not None else -1.0,
            r.expectancy_r,
        ),
        reverse=True,
    )
    return [r.to_dict() for r in results]
