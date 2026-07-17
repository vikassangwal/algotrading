"""Institutional quant/statistical metrics — real formulas, no random, no mock.

Pure functions over return series (numpy arrays / lists of floats). These are the
building blocks used by the risk desk, portfolio analytics, and the /api/quant
endpoints. Everything here is deterministic and unit-tested.

Conventions:
- "returns" = simple periodic returns (e.g. daily), not log returns, unless noted.
- Annualization uses `periods_per_year` (252 trading days by default).
- risk_free is an ANNUAL rate (e.g. 0.06 for 6%); it is de-annualized internally.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numpy as np

TRADING_DAYS = 252


def returns_from_prices(prices: Sequence[float]) -> np.ndarray:
    """Simple periodic returns from a price series: r_t = P_t / P_{t-1} - 1."""
    p = np.asarray(prices, dtype=float)
    if p.size < 2:
        return np.array([])
    return p[1:] / p[:-1] - 1.0


def standard_deviation(returns: Sequence[float], annualize: bool = False,
                       periods_per_year: int = TRADING_DAYS) -> float:
    """Sample standard deviation of returns (ddof=1)."""
    r = np.asarray(returns, dtype=float)
    if r.size < 2:
        return 0.0
    sd = float(np.std(r, ddof=1))
    return sd * math.sqrt(periods_per_year) if annualize else sd


def max_drawdown(returns: Sequence[float]) -> float:
    """Maximum peak-to-trough drawdown of the cumulative equity curve.

    Returns a POSITIVE fraction (e.g. 0.22 = 22% drawdown). 0.0 if never underwater.
    """
    r = np.asarray(returns, dtype=float)
    if r.size == 0:
        return 0.0
    equity = np.cumprod(1.0 + r)
    running_peak = np.maximum.accumulate(equity)
    drawdowns = (running_peak - equity) / running_peak
    return float(np.max(drawdowns))


def sharpe_ratio(returns: Sequence[float], risk_free: float = 0.0,
                 periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized Sharpe ratio. risk_free is an annual rate."""
    r = np.asarray(returns, dtype=float)
    if r.size < 2:
        return 0.0
    rf_per_period = risk_free / periods_per_year
    excess = r - rf_per_period
    sd = np.std(excess, ddof=1)
    if sd == 0:
        return 0.0
    return float(np.mean(excess) / sd * math.sqrt(periods_per_year))


def sortino_ratio(returns: Sequence[float], risk_free: float = 0.0,
                  periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized Sortino ratio — like Sharpe but penalizes only downside deviation.

    Downside deviation = RMS of negative excess returns (below the target=rf).
    """
    r = np.asarray(returns, dtype=float)
    if r.size < 2:
        return 0.0
    rf_per_period = risk_free / periods_per_year
    excess = r - rf_per_period
    downside = np.minimum(excess, 0.0)
    downside_dev = math.sqrt(np.mean(downside ** 2))
    if downside_dev == 0:
        return 0.0
    return float(np.mean(excess) / downside_dev * math.sqrt(periods_per_year))


def calmar_ratio(returns: Sequence[float],
                 periods_per_year: int = TRADING_DAYS) -> float:
    """Calmar ratio = annualized (CAGR) return / maximum drawdown."""
    r = np.asarray(returns, dtype=float)
    if r.size < 2:
        return 0.0
    mdd = max_drawdown(r)
    if mdd == 0:
        return 0.0
    total_growth = float(np.prod(1.0 + r))
    if total_growth <= 0:
        return 0.0
    cagr = total_growth ** (periods_per_year / r.size) - 1.0
    return float(cagr / mdd)


def beta(asset_returns: Sequence[float], market_returns: Sequence[float]) -> float:
    """CAPM beta = Cov(asset, market) / Var(market)."""
    a = np.asarray(asset_returns, dtype=float)
    m = np.asarray(market_returns, dtype=float)
    n = min(a.size, m.size)
    if n < 2:
        return 0.0
    a, m = a[-n:], m[-n:]
    var_m = np.var(m, ddof=1)
    if var_m == 0:
        return 0.0
    cov = np.cov(a, m, ddof=1)[0, 1]
    return float(cov / var_m)


def alpha_capm(asset_returns: Sequence[float], market_returns: Sequence[float],
               risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized Jensen's alpha from the CAPM regression.

    alpha = mean(asset_excess) - beta * mean(market_excess), then annualized.
    """
    a = np.asarray(asset_returns, dtype=float)
    m = np.asarray(market_returns, dtype=float)
    n = min(a.size, m.size)
    if n < 2:
        return 0.0
    a, m = a[-n:], m[-n:]
    rf_per_period = risk_free / periods_per_year
    b = beta(a, m)
    alpha_per_period = np.mean(a - rf_per_period) - b * np.mean(m - rf_per_period)
    return float(alpha_per_period * periods_per_year)


def correlation_matrix(series_map: Dict[str, Sequence[float]]) -> Dict[str, Dict[str, float]]:
    """Pearson correlation matrix of several return series.

    Input: {name: returns[]}. Series are truncated to the shortest common length.
    Output: nested dict {name_i: {name_j: corr}}. Empty dict if <2 series.
    """
    names = list(series_map.keys())
    if len(names) < 2:
        return {}
    arrays = [np.asarray(series_map[n], dtype=float) for n in names]
    n = min(a.size for a in arrays)
    if n < 2:
        return {}
    trimmed = [a[-n:] for a in arrays]
    matrix = np.corrcoef(np.vstack(trimmed))
    out: Dict[str, Dict[str, float]] = {}
    for i, ni in enumerate(names):
        out[ni] = {}
        for j, nj in enumerate(names):
            val = matrix[i, j]
            out[ni][nj] = float(round(val, 4)) if not math.isnan(val) else 0.0
    return out


def monte_carlo_var(returns: Sequence[float], horizon: int = 1, n_sims: int = 10000,
                    confidence: float = 0.95, seed: int = 42) -> Dict[str, float]:
    """Bootstrap Monte Carlo Value-at-Risk / Expected Shortfall.

    Resamples historical returns (with replacement) over `horizon` periods,
    `n_sims` times, then reports the loss at the given confidence level.
    Deterministic given `seed` (reproducible — no global RNG state).

    Returns fractions (e.g. var=0.031 => 3.1% loss). Positive = a loss.
    """
    r = np.asarray(returns, dtype=float)
    if r.size < 2:
        return {"var": 0.0, "expected_shortfall": 0.0, "mean": 0.0, "n_sims": 0}
    rng = np.random.default_rng(seed)
    draws = rng.choice(r, size=(n_sims, horizon), replace=True)
    horizon_returns = np.prod(1.0 + draws, axis=1) - 1.0
    losses = -horizon_returns  # positive = loss
    var = float(np.quantile(losses, confidence))
    tail = losses[losses >= var]
    es = float(np.mean(tail)) if tail.size else var
    return {
        "var": round(var, 6),
        "expected_shortfall": round(es, 6),
        "mean": round(float(np.mean(horizon_returns)), 6),
        "n_sims": n_sims,
    }


def full_performance_report(returns: Sequence[float], market_returns: Sequence[float] = None,
                            risk_free: float = 0.06,
                            periods_per_year: int = TRADING_DAYS) -> Dict[str, float]:
    """One-shot institutional performance summary from a return series."""
    r = np.asarray(returns, dtype=float)
    report = {
        "periods": int(r.size),
        "std_dev_annual": round(standard_deviation(r, annualize=True, periods_per_year=periods_per_year), 4),
        "sharpe": round(sharpe_ratio(r, risk_free, periods_per_year), 3),
        "sortino": round(sortino_ratio(r, risk_free, periods_per_year), 3),
        "calmar": round(calmar_ratio(r, periods_per_year), 3),
        "max_drawdown": round(max_drawdown(r), 4),
    }
    if market_returns is not None and len(market_returns) >= 2:
        report["beta"] = round(beta(r, market_returns), 3)
        report["alpha_annual"] = round(alpha_capm(r, market_returns, risk_free, periods_per_year), 4)
    return report
