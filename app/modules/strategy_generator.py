"""Auto strategy generator with honest out-of-sample validation.

Generates many parameterized strategy variants (EMA cross, RSI reversion,
Donchian breakout, MACD, Bollinger), grid-searches them on a TRAIN split,
then re-tests the best candidates on a held-out TEST split they never saw.

WHY THE SPLIT MATTERS (overfitting warning): if you search hundreds of
parameter combinations on the same data you score them on, the "best" one is
usually just the luckiest fit to past noise — it will not repeat live. A
variant here is only marked `validated` when its edge survives on unseen data:
  * train profit factor >= 1.3 AND
  * test profit factor >= 1.2 AND test expectancy > 0 AND
  * enough trades in both splits to mean anything.
Everything else is labeled honestly (OVERFIT / WEAK), never hidden.
"""
from __future__ import annotations

import logging
from itertools import product
from typing import Callable, Optional

import pandas as pd

from .indicators import calculate_bollinger_bands, calculate_ema, calculate_rsi
from .strategies import backtest_strategy

logger = logging.getLogger("elco.strategy_generator")

TRAIN_FRACTION = 0.7
MIN_TRADES_TRAIN = 12
MIN_TRADES_TEST = 5


# --- Parameterized strategy templates ---------------------------------------
# Each factory returns a signal function (df -> "BUY"|"SELL"|None) built from
# concrete parameters, plus a human-readable name.

def _make_ema_cross(fast: int, slow: int) -> Callable[[pd.DataFrame], Optional[str]]:
    def signal(df: pd.DataFrame) -> Optional[str]:
        if len(df) < slow + 5:
            return None
        f = calculate_ema(df["close"], fast)
        s = calculate_ema(df["close"], slow)
        if f.iloc[-2] <= s.iloc[-2] and f.iloc[-1] > s.iloc[-1]:
            return "BUY"
        if f.iloc[-2] >= s.iloc[-2] and f.iloc[-1] < s.iloc[-1]:
            return "SELL"
        return None
    return signal


def _make_rsi_reversion(period: int, oversold: int, overbought: int):
    def signal(df: pd.DataFrame) -> Optional[str]:
        if len(df) < period + 6:
            return None
        rsi = calculate_rsi(df["close"], period)
        if rsi.iloc[-2] < oversold and rsi.iloc[-1] >= oversold:
            return "BUY"
        if rsi.iloc[-2] > overbought and rsi.iloc[-1] <= overbought:
            return "SELL"
        return None
    return signal


def _make_donchian(window: int):
    def signal(df: pd.DataFrame) -> Optional[str]:
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
    return signal


def _make_macd(fast: int, slow: int, sig_period: int):
    def signal(df: pd.DataFrame) -> Optional[str]:
        if len(df) < slow + sig_period + 5:
            return None
        macd = calculate_ema(df["close"], fast) - calculate_ema(df["close"], slow)
        sig = calculate_ema(macd, sig_period)
        if macd.iloc[-2] <= sig.iloc[-2] and macd.iloc[-1] > sig.iloc[-1]:
            return "BUY"
        if macd.iloc[-2] >= sig.iloc[-2] and macd.iloc[-1] < sig.iloc[-1]:
            return "SELL"
        return None
    return signal


def _make_bollinger(period: int, std: float):
    def signal(df: pd.DataFrame) -> Optional[str]:
        if len(df) < period + 5:
            return None
        bb = calculate_bollinger_bands(df["close"], period, std)
        close = df["close"]
        if close.iloc[-2] < bb["Lower_Band"].iloc[-2] and close.iloc[-1] >= bb["Lower_Band"].iloc[-1]:
            return "BUY"
        if close.iloc[-2] > bb["Upper_Band"].iloc[-2] and close.iloc[-1] <= bb["Upper_Band"].iloc[-1]:
            return "SELL"
        return None
    return signal


# --- SMC / price-action templates (from smc_analysis) ------------------------

def _make_bos_follow(swing_lookback: int):
    """Trade a Break of Structure in the direction of the trend."""
    def signal(df: pd.DataFrame) -> Optional[str]:
        if len(df) < 60:
            return None
        from .smc_analysis import detect_structure
        s = detect_structure(df.iloc[-120:].reset_index(drop=True), lookback=swing_lookback)
        bos = s.get("bos")
        if bos and bos["direction"] == "BULLISH":
            return "BUY"
        if bos and bos["direction"] == "BEARISH":
            return "SELL"
        return None
    return signal


def _make_sweep_reversal(recent_bars: int):
    """Fade a liquidity sweep: sell-side sweep (stop hunt below) -> BUY."""
    def signal(df: pd.DataFrame) -> Optional[str]:
        if len(df) < 60:
            return None
        from .smc_analysis import liquidity_sweeps
        sweeps = liquidity_sweeps(df.iloc[-120:].reset_index(drop=True), recent_bars=recent_bars)
        fresh = [s for s in sweeps if s["bars_ago"] == 0]
        if any(s["kind"] == "SELL_SIDE_SWEEP" for s in fresh):
            return "BUY"
        if any(s["kind"] == "BUY_SIDE_SWEEP" for s in fresh):
            return "SELL"
        return None
    return signal


def _make_sr_bounce(tolerance_pct: float):
    """Bounce off a multi-touch S/R zone: near support+green -> BUY, near
    resistance+red -> SELL."""
    def signal(df: pd.DataFrame) -> Optional[str]:
        if len(df) < 60:
            return None
        from .smc_analysis import support_resistance_zones
        zones = support_resistance_zones(df.iloc[-150:].reset_index(drop=True))
        close = float(df["close"].iloc[-1])
        opn = float(df["open"].iloc[-1])
        for z in zones:
            if z["touches"] < 3 or abs(z["distance_pct"]) > tolerance_pct:
                continue
            if z["kind"] == "SUPPORT" and close > opn:
                return "BUY"
            if z["kind"] == "RESISTANCE" and close < opn:
                return "SELL"
        return None
    return signal


def build_variants(max_variants: int = 120) -> list:
    """Enumerate parameterized strategy variants across all templates.

    Grids are intentionally coarse — finer grids multiply overfitting risk
    without adding genuinely different behavior.
    """
    variants = []

    for fast, slow in product((5, 10, 20), (20, 50, 100)):
        if fast >= slow:
            continue
        variants.append((f"EMA Cross {fast}/{slow}", _make_ema_cross(fast, slow),
                         {"template": "ema_cross", "fast": fast, "slow": slow}))

    for period, (lo, hi) in product((7, 14, 21), ((30, 70), (25, 75), (20, 80))):
        variants.append((f"RSI({period}) Reversion {lo}/{hi}", _make_rsi_reversion(period, lo, hi),
                         {"template": "rsi_reversion", "period": period, "oversold": lo, "overbought": hi}))

    for window in (10, 20, 40, 55):
        variants.append((f"Donchian Breakout {window}", _make_donchian(window),
                         {"template": "donchian", "window": window}))

    for fast, slow, sigp in ((8, 21, 5), (12, 26, 9), (19, 39, 9)):
        variants.append((f"MACD {fast}/{slow}/{sigp}", _make_macd(fast, slow, sigp),
                         {"template": "macd", "fast": fast, "slow": slow, "signal": sigp}))

    for period, std in product((20, 30), (2.0, 2.5)):
        variants.append((f"Bollinger {period}/{std}", _make_bollinger(period, std),
                         {"template": "bollinger", "period": period, "std": std}))

    # SMC / price-action — validated exactly like everything else.
    for lb in (3, 5):
        variants.append((f"BOS Follow (swing {lb})", _make_bos_follow(lb),
                         {"template": "bos_follow", "swing_lookback": lb}))
    for rb in (5, 10):
        variants.append((f"Liquidity Sweep Reversal ({rb}b)", _make_sweep_reversal(rb),
                         {"template": "sweep_reversal", "recent_bars": rb}))
    for tol in (1.0, 2.0):
        variants.append((f"S/R Zone Bounce ({tol}%)", _make_sr_bounce(tol),
                         {"template": "sr_bounce", "tolerance_pct": tol}))

    return variants[:max_variants]


def _metrics(result) -> dict:
    d = result.to_dict()
    return {
        "trades": d["total_trades"],
        "win_rate_pct": d["win_rate_pct"],
        "profit_factor": d["profit_factor"],
        "expectancy_r": d["expectancy_r"],
        "max_drawdown_pct": d["max_drawdown_pct"],
    }


def _pf_ok(pf, threshold: float) -> bool:
    """profit_factor can be float, None, or the string 'inf' (serialized)."""
    if pf is None:
        return False
    if pf == "inf":
        return True
    return float(pf) >= threshold


# Exit profiles: (sl_atr, target_atr) pairs. Win rate depends heavily on the
# reward:risk shape — a tight 1:1 target books profit sooner (higher win rate,
# smaller wins); a 1:2 target wins less often but bigger. Gridding exits lets
# the generator find HIGH-WIN-RATE variants honestly, without cooking numbers:
# with 1:1 R:R, a strategy needs >50% wins just to break even, so a validated
# 60%+ win rate at 1:1 is a real edge.
EXIT_PROFILES = (
    (1.5, 1.5),   # 1:1  — highest win-rate shape
    (2.0, 2.0),   # 1:1 wide — fewer stop-outs from noise
    (1.5, 3.0),   # 1:2  — classic trend shape (lower win rate, bigger wins)
)


def generate_strategies(df: pd.DataFrame, top_n: int = 10,
                        max_variants: int = 120,
                        min_win_rate: float = 0.0) -> dict:
    """Grid-search (entry-variant × exit-profile) on TRAIN; validate on TEST.

    min_win_rate (e.g. 60.0): require at least this win rate on BOTH splits.
    The gate always ALSO requires profitability (PF/expectancy) — a 60% win
    rate that loses money is worthless (small wins, big losses), so win rate
    alone is never the criterion.

    Returns {"validated": [...], "overfit": [...], ...}. `overfit` = looked
    good on train but failed unseen test data — shown deliberately.
    """
    n = len(df)
    if n < 300:
        raise ValueError("Need at least 300 bars to run a meaningful train/test split.")

    split = int(n * TRAIN_FRACTION)
    train_df = df.iloc[:split].reset_index(drop=True)
    test_df = df.iloc[split:].reset_index(drop=True)

    variants = build_variants(max_variants)
    train_scored = []
    for name, fn, params in variants:
        for sl_atr, target_atr in EXIT_PROFILES:
            rr = target_atr / sl_atr
            full_name = f"{name} [{'1:%.1f' % rr}]"
            try:
                res = backtest_strategy(full_name, fn, train_df,
                                        sl_atr=sl_atr, target_atr=target_atr)
            except Exception as e:
                logger.warning(f"Variant '{full_name}' failed on train: {e}")
                continue
            if res.total_trades < MIN_TRADES_TRAIN or res.profit_factor is None:
                continue
            if min_win_rate and res.win_rate < min_win_rate:
                continue
            full_params = dict(params, sl_atr=sl_atr, target_atr=target_atr)
            train_scored.append((full_name, fn, full_params, res))

    # Rank by train edge; only the top candidates advance to the test split.
    def _pf_key(r):
        import math
        pf = r.profit_factor
        return (float("inf") if (pf is not None and math.isinf(pf)) else (pf or -1.0), r.expectancy_r)

    train_scored.sort(key=lambda t: _pf_key(t[3]), reverse=True)
    candidates = [t for t in train_scored if _pf_ok(t[3].to_dict()["profit_factor"], 1.3)][:top_n * 2]

    validated, overfit = [], []
    for full_name, fn, full_params, train_res in candidates:
        try:
            test_res = backtest_strategy(
                full_name, fn, test_df, warmup=60,
                sl_atr=full_params["sl_atr"], target_atr=full_params["target_atr"],
            )
        except Exception as e:
            logger.warning(f"Variant '{full_name}' failed on test: {e}")
            continue
        entry = {
            "name": full_name,
            "params": full_params,
            "train": _metrics(train_res),
            "test": _metrics(test_res),
        }
        test_d = test_res.to_dict()
        ok = (
            test_res.total_trades >= MIN_TRADES_TEST
            and _pf_ok(test_d["profit_factor"], 1.2)
            and test_res.expectancy_r > 0
            and (not min_win_rate or test_res.win_rate >= min_win_rate)
        )
        if ok:
            entry["status"] = "VALIDATED"
            validated.append(entry)
        else:
            entry["status"] = "OVERFIT"
            entry["why"] = (
                "Train-split performance did not hold on unseen test data "
                f"(test: {test_res.total_trades} trades, win {test_d['win_rate_pct']}%, "
                f"PF {test_d['profit_factor']}, expectancy {test_d['expectancy_r']}R"
                + (f"; needed win rate ≥ {min_win_rate}%" if min_win_rate else "")
                + ")."
            )
            overfit.append(entry)

    validated = validated[:top_n]
    return {
        "bars_total": n,
        "bars_train": len(train_df),
        "bars_test": len(test_df),
        "min_win_rate_filter": min_win_rate or None,
        "variants_tried": len(variants) * len(EXIT_PROFILES),
        "variants_with_enough_trades": len(train_scored),
        "candidates_advanced_to_test": len(candidates),
        "validated": validated,
        "overfit": overfit,
        "note": (
            "VALIDATED = met every gate (incl. win-rate filter if set) on train "
            "AND held-out test data. High win rate is achieved via exit shape "
            "(1:1 R:R books profit sooner) — but profitability gates always "
            "apply too, because a high win rate alone can still lose money."
        ),
    }


def hunt_validated(symbols: list, min_win_rate: float = 60.0, years: int = 4,
                   top_n: int = 3, source: str = "real",
                   interval: str = "1d") -> dict:
    """Scan a universe for strategies that validated at min_win_rate on BOTH
    splits — the honest way to build a '60%+ accuracy' book: trade ONLY where
    that accuracy has been demonstrated out-of-sample, skip everything else.

    interval="15m"/"5m" hunts INTRADAY strategies on real intraday history
    (~60 days for 15m — less history than daily, so treat intraday validation
    as weaker evidence; there is no mock fallback for intraday).

    Returns per-symbol validated lists + a flat 'book' ready to deploy.
    Symbols where nothing validates are reported honestly in 'no_edge'.
    """
    from ..backtester import load_history, load_intraday_history

    book, per_symbol, no_edge = [], {}, []
    for sym in symbols:
        sym = sym.upper().strip()
        try:
            if interval == "1d":
                df, actual = load_history(sym, years=years, source=source, return_source=True)
                if source == "real" and actual != "real":
                    no_edge.append({"symbol": sym, "reason": "real data unavailable — skipped (never hunt on mock)"})
                    continue
            else:
                df = load_intraday_history(sym, interval=interval)
            r = generate_strategies(df, top_n=top_n, min_win_rate=min_win_rate)
        except Exception as e:
            no_edge.append({"symbol": sym, "reason": f"scan failed: {e}"})
            continue
        if r["validated"]:
            for v in r["validated"]:
                v["params"]["timeframe"] = interval   # deploy carries the bar size
                book.append({"symbol": sym, **v})
            per_symbol[sym] = r["validated"]
        else:
            no_edge.append({"symbol": sym, "reason": f"nothing validated at {min_win_rate}%+ on unseen data"})

    return {
        "interval": interval,
        "min_win_rate": min_win_rate,
        "symbols_scanned": len(symbols),
        "symbols_with_edge": len(per_symbol),
        "book": book,
        "per_symbol": per_symbol,
        "no_edge": no_edge,
        "note": (
            f"The book contains ONLY strategy-symbol pairs that held {min_win_rate}%+ "
            "win rate on held-out test data net of costs. Symbols under no_edge "
            "should simply not be traded with these strategies — skipping them IS "
            "how the system's realized accuracy stays high."
        ),
    }
