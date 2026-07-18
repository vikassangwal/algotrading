"""Quantitative statistics — the institutional risk-metrics block.

Two data sources, both real:
  * Closed trades from the DB journal  → Sharpe, Sortino, Calmar, max
    drawdown, volatility, Monte Carlo resampling of the equity curve.
  * Price history (yfinance)           → correlation matrix, beta/alpha
    vs NIFTY for any symbol list.

Honesty: with fewer than MIN_TRADES closed trades the trade-based ratios
are returned as null with the reason — tiny samples make these numbers
meaningless and we don't print meaningless numbers.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("elco.quant_stats")

MIN_TRADES = 10
TRADING_DAYS = 252
MC_RUNS = 2000


# --- trade-based metrics ------------------------------------------------------

def _closed_trade_returns() -> List[float]:
    """Per-trade returns (pnl / notional) from the DB, oldest first."""
    from ..db import SessionLocal, TradeRecord as DBTrade
    db = SessionLocal()
    try:
        rows = (db.query(DBTrade)
                .filter(DBTrade.status == "CLOSED")
                .order_by(DBTrade.timestamp.asc()).all())
        out = []
        for r in rows:
            notional = (r.price or 0) * (r.quantity or 0)
            if notional > 0:
                out.append((r.pnl or 0.0) / notional)
        return out
    finally:
        db.close()


def trade_stats() -> Dict[str, Any]:
    """Sharpe/Sortino/Calmar/max-DD from REAL closed trades."""
    rets = _closed_trade_returns()
    n = len(rets)
    base: Dict[str, Any] = {"closed_trades": n, "min_trades_required": MIN_TRADES}
    if n < MIN_TRADES:
        base.update({
            "sharpe": None, "sortino": None, "calmar": None,
            "max_drawdown_pct": None, "volatility_pct": None,
            "note": f"Only {n} closed trades — these ratios need >= {MIN_TRADES} "
                    "to mean anything. Trade more (paper) first.",
        })
        return base

    r = np.asarray(rets, float)
    mean, std = float(r.mean()), float(r.std(ddof=1))
    downside = r[r < 0]
    dstd = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0

    equity = np.cumprod(1 + r)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(dd.min())

    # Annualization by trade count is misleading; report per-trade ratios and
    # say so. (sqrt(n) scaling assumes independence we can't claim yet.)
    sharpe = round(mean / std, 3) if std > 0 else None
    sortino = round(mean / dstd, 3) if dstd > 0 else None
    total_return = float(equity[-1] - 1)
    calmar = round(total_return / abs(max_dd), 3) if max_dd < 0 else None

    base.update({
        "sharpe": sharpe, "sortino": sortino, "calmar": calmar,
        "max_drawdown_pct": round(max_dd * 100, 2),
        "volatility_pct": round(std * 100, 2),
        "avg_trade_return_pct": round(mean * 100, 3),
        "total_return_pct": round(total_return * 100, 2),
        "ratio_basis": "per-trade (not annualized — honest for small samples)",
    })
    return base


def monte_carlo(runs: int = MC_RUNS) -> Dict[str, Any]:
    """Resample the REAL trade-return sequence to see the range of equity
    outcomes the same trades could have produced in different orders."""
    rets = _closed_trade_returns()
    if len(rets) < MIN_TRADES:
        return {"available": False,
                "note": f"Needs >= {MIN_TRADES} closed trades (have {len(rets)})."}
    rng = np.random.default_rng(42)  # deterministic — reproducible report
    r = np.asarray(rets, float)
    finals, max_dds = [], []
    for _ in range(runs):
        sample = rng.choice(r, size=len(r), replace=True)
        eq = np.cumprod(1 + sample)
        peak = np.maximum.accumulate(eq)
        max_dds.append(float(((eq - peak) / peak).min()))
        finals.append(float(eq[-1] - 1))
    finals, max_dds = np.asarray(finals), np.asarray(max_dds)
    return {
        "available": True,
        "runs": runs,
        "trades_resampled": len(r),
        "final_return_pct": {
            "p5": round(float(np.percentile(finals, 5)) * 100, 2),
            "p50": round(float(np.percentile(finals, 50)) * 100, 2),
            "p95": round(float(np.percentile(finals, 95)) * 100, 2),
        },
        "max_drawdown_pct": {
            "p5_worst": round(float(np.percentile(max_dds, 5)) * 100, 2),
            "p50": round(float(np.percentile(max_dds, 50)) * 100, 2),
        },
        "prob_losing_overall": round(float((finals < 0).mean()) * 100, 1),
        "note": "Bootstrap of YOUR real trade returns — order-shuffled outcomes, "
                "not a market prediction.",
    }


# --- price-based metrics ------------------------------------------------------

def correlation_and_beta(symbols: List[str], benchmark: str = "^NSEI",
                         period: str = "1y") -> Dict[str, Any]:
    """Correlation matrix + beta/alpha vs NIFTY from real price history."""
    import pandas as pd
    import yfinance as yf

    symbols = [s.upper() for s in symbols][:15]
    tickers = [s if s.startswith("^") else f"{s}.NS" for s in symbols]
    try:
        raw = yf.download(tickers + [benchmark], period=period, interval="1d",
                          progress=False, auto_adjust=True, group_by="ticker",
                          threads=True)
    except Exception as e:
        return {"error": f"download failed: {e}"}

    closes: Dict[str, Any] = {}
    for sym, tk in zip(symbols + ["NIFTY_BENCH"], tickers + [benchmark]):
        try:
            df = raw[tk] if isinstance(raw.columns, pd.MultiIndex) else raw
            c = df["Close"].dropna()
            if len(c) > 60:
                closes[sym] = c
        except Exception:
            continue
    if "NIFTY_BENCH" not in closes or len(closes) < 2:
        return {"error": "not enough usable price series", "got": list(closes.keys())}

    prices = pd.DataFrame(closes).dropna()
    rets = prices.pct_change().dropna()
    corr = rets.drop(columns=["NIFTY_BENCH"]).corr().round(2)

    bench = rets["NIFTY_BENCH"]
    bvar = float(bench.var())
    betas = {}
    for sym in corr.columns:
        cov = float(rets[sym].cov(bench))
        beta = cov / bvar if bvar > 0 else None
        # Jensen's alpha (annualized, rf≈0 for simplicity — stated).
        alpha = float(rets[sym].mean() - (beta or 0) * bench.mean()) * TRADING_DAYS
        betas[sym] = {"beta": round(beta, 2) if beta is not None else None,
                      "alpha_annual_pct": round(alpha * 100, 2)}

    return {
        "period": period,
        "benchmark": "NIFTY 50",
        "correlation_matrix": corr.to_dict(),
        "beta_alpha": betas,
        "note": "Alpha assumes rf=0 (stated simplification). Real daily closes.",
    }
