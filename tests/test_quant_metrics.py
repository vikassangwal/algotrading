"""Tests for app/modules/quant_metrics.py — real quant/statistical formulas."""
import math

import numpy as np
import pytest

from app.modules import quant_metrics as q


def test_returns_from_prices():
    r = q.returns_from_prices([100, 110, 99])
    assert r[0] == pytest.approx(0.10)
    assert r[1] == pytest.approx(-0.10)
    assert q.returns_from_prices([100]).size == 0


def test_standard_deviation_matches_numpy():
    r = [0.01, -0.02, 0.03, -0.01, 0.02]
    assert q.standard_deviation(r) == pytest.approx(np.std(r, ddof=1))
    # annualized scales by sqrt(252)
    assert q.standard_deviation(r, annualize=True) == pytest.approx(
        np.std(r, ddof=1) * math.sqrt(252)
    )


def test_max_drawdown_known():
    # +10% then -50% => equity 1.1 -> 0.55, peak 1.1 => DD = 0.5
    r = [0.10, -0.50]
    assert q.max_drawdown(r) == pytest.approx(0.5)
    # monotonic up => no drawdown
    assert q.max_drawdown([0.01, 0.02, 0.03]) == 0.0


def test_beta_exact():
    mkt = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
    assert q.beta(2 * mkt, mkt) == pytest.approx(2.0)
    assert q.beta(-1 * mkt, mkt) == pytest.approx(-1.0)


def test_alpha_zero_when_capm_holds():
    mkt = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
    # asset exactly beta*market with rf=0 => alpha ~ 0
    assert q.alpha_capm(2 * mkt, mkt, risk_free=0.0) == pytest.approx(0.0, abs=1e-9)


def test_sortino_only_penalizes_downside():
    # all-positive returns => downside deviation 0 => sortino 0 (guard)
    assert q.sortino_ratio([0.01, 0.02, 0.03]) == 0.0
    # mixed returns => finite
    s = q.sortino_ratio([0.02, -0.01, 0.03, -0.02, 0.01])
    assert math.isfinite(s)


def test_calmar_sign_follows_return():
    up = [0.02, 0.01, -0.01, 0.03, 0.02]
    down = [-0.02, -0.03, 0.01, -0.04, -0.01]
    assert q.calmar_ratio(up) > 0
    assert q.calmar_ratio(down) < 0


def test_correlation_matrix_bounds():
    cm = q.correlation_matrix({
        "A": [0.01, 0.02, -0.01, 0.03],
        "B": [0.01, 0.02, -0.01, 0.03],   # identical to A
        "C": [-0.01, -0.02, 0.01, -0.03],  # opposite of A
    })
    assert cm["A"]["A"] == pytest.approx(1.0)
    assert cm["A"]["B"] == pytest.approx(1.0)
    assert cm["A"]["C"] == pytest.approx(-1.0)


def test_monte_carlo_reproducible_and_bounded():
    r = [0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.015]
    mc1 = q.monte_carlo_var(r, seed=7)
    mc2 = q.monte_carlo_var(r, seed=7)
    assert mc1 == mc2  # deterministic given seed
    assert mc1["expected_shortfall"] >= mc1["var"]  # ES is deeper in the tail
    assert mc1["n_sims"] == 10000


def test_full_report_has_all_metrics():
    r = q.returns_from_prices([100, 102, 101, 105, 103, 108, 110, 107, 112, 115, 113, 118])
    mkt = q.returns_from_prices([100, 101, 100, 103, 102, 105, 106, 104, 108, 110, 109, 112])
    rep = q.full_performance_report(r, mkt)
    for key in ("sharpe", "sortino", "calmar", "max_drawdown", "std_dev_annual", "beta", "alpha_annual"):
        assert key in rep


def test_empty_inputs_safe():
    assert q.sharpe_ratio([]) == 0.0
    assert q.beta([], []) == 0.0
    assert q.max_drawdown([]) == 0.0
    assert q.correlation_matrix({"A": [0.01]}) == {}
