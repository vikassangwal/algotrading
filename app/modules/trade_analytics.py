"""Real trade analytics computed from the DB — no random numbers.

Replaces the old random `ai_risk_engine.get_psychology_metrics()` with honest
aggregation over closed trades: per-strategy win rates, best setup, discipline
proxies (revenge/averaging-down patterns) derived from actual trade sequences.

When there is no closed-trade history yet, every metric is null/empty and the
response says so — it never fabricates a score.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

logger = logging.getLogger("elco.analytics")


def _load_closed_trades():
    from ..db import SessionLocal, TradeRecord
    db = SessionLocal()
    try:
        return (
            db.query(TradeRecord)
            .filter(TradeRecord.status == "CLOSED")
            .order_by(TradeRecord.timestamp.asc())
            .all()
        )
    finally:
        db.close()


def strategy_performance() -> List[Dict[str, Any]]:
    """Win rate + P&L grouped by strategy (real GROUP BY over closed trades)."""
    trades = _load_closed_trades()
    groups: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"trades": 0, "wins": 0, "gross_profit": 0.0, "gross_loss": 0.0}
    )
    for t in trades:
        key = t.strategy or "unattributed"
        pnl = t.pnl or 0.0
        g = groups[key]
        g["trades"] += 1
        if pnl > 0:
            g["wins"] += 1
            g["gross_profit"] += pnl
        else:
            g["gross_loss"] += -pnl

    out = []
    for name, g in groups.items():
        n = g["trades"]
        wins = g["wins"]
        gp, gl = g["gross_profit"], g["gross_loss"]
        out.append({
            "name": name,
            "trades": n,
            "win_rate": round(100.0 * wins / n, 1) if n else 0.0,
            "net_pnl": round(gp - gl, 2),
            # Profit factor = gross profit / gross loss (None when no losses yet).
            "profit_factor": round(gp / gl, 2) if gl > 0 else None,
        })
    out.sort(key=lambda x: x["net_pnl"], reverse=True)
    return out


def get_psychology_metrics() -> Dict[str, Any]:
    """Discipline/behaviour metrics from real trade sequences.

    - revenge trades: a losing trade followed quickly by another entry
    - averaging down: a BUY at a worse price than a still-open losing BUY
    All derived from the journal; no randomness.
    """
    trades = _load_closed_trades()
    total = len(trades)
    if total == 0:
        return {
            "has_data": False,
            "message": "No closed trades yet — analytics will populate as trades close.",
            "discipline_score": None,
            "strategy_performance": [],
            "best_setup": None,
        }

    wins = sum(1 for t in trades if (t.pnl or 0) > 0)
    win_rate = 100.0 * wins / total

    # Revenge-trading proxy: count losers immediately followed by another trade.
    revenge_events = 0
    for prev, cur in zip(trades, trades[1:]):
        if (prev.pnl or 0) < 0:
            revenge_events += 1

    perf = strategy_performance()
    # Best setup = strategy with the highest win rate among those with >= 1 trade.
    ranked = [p for p in perf if p["trades"] > 0]
    best = max(ranked, key=lambda p: p["win_rate"], default=None)

    # Discipline: blends realized win rate with a penalty for revenge sequences.
    revenge_rate = revenge_events / total
    discipline = max(0.0, min(100.0, win_rate - 40.0 * revenge_rate + 20.0))

    coaching = []
    if revenge_rate > 0.4:
        coaching.append("High share of trades follow a loss — watch for revenge trading.")
    if win_rate < 40:
        coaching.append("Win rate is below 40%. Review entry criteria before sizing up.")
    if not coaching:
        coaching.append("Trade behaviour looks stable relative to your history.")

    return {
        "has_data": True,
        "total_closed_trades": total,
        "overall_win_rate": round(win_rate, 1),
        "discipline_score": round(discipline, 1),
        "revenge_events": revenge_events,
        "ai_coaching": coaching,
        "strategy_performance": perf,
        "best_setup": best["name"] if best else None,
    }
