"""PAPER options trading — F&O ka safe, honest version.

Entry/exit prices come from the REAL NSE option chain (LTP as quoted), so
the P&L is what you would actually have seen — minus real-world slippage,
which paper cannot simulate (stated in every response).

Discipline (same spirit as equity rules):
  * R1: HALTED system -> no option entries either.
  * Max MAX_OPTION_POSITIONS open option positions.
  * BUY-only (long CE/PE): option SELLING has unlimited-loss tails and
    margin mechanics that paper cannot honestly simulate — refused.
  * Position cost capped at OPTION_MAX_COST_PCT of capital: premium you
    pay is premium you can lose, entirely.

LIVE options execution is deliberately NOT implemented. Cash-equity live
(with its readiness scorecard) comes first.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("elco.options_trader")

MAX_OPTION_POSITIONS = 3
OPTION_MAX_COST_PCT = 2.0   # premium per position <= 2% of capital


def _chain(underlying: str, expiry: str = ""):
    from .modules.options_data import OptionsDataEngine
    return OptionsDataEngine().get_option_chain(underlying, expiry)


def _find_ltp(chain: Dict[str, Any], strike: float, opt_type: str) -> Optional[float]:
    rows = chain.get("calls" if opt_type == "CE" else "puts") or []
    for r in rows:
        if abs(r["strike"] - strike) < 1e-6:
            return float(r["ltp"]) if r["ltp"] > 0 else None
    return None


def open_trade(underlying: str, strike: float, opt_type: str,
               qty: int, expiry: str = "") -> Dict[str, Any]:
    """Open a PAPER long option position at the real quoted LTP."""
    from .config import config, AutoTradeState
    from .db import SessionLocal, OptionsPaperTrade

    opt_type = opt_type.upper().strip()
    if opt_type not in ("CE", "PE"):
        return {"ok": False, "reason": "opt_type must be CE or PE"}
    if qty <= 0:
        return {"ok": False, "reason": "qty must be positive"}
    if config.auto_trade == AutoTradeState.HALTED:
        return {"ok": False, "reason": "R1: system HALTED — no option entries."}

    db = SessionLocal()
    try:
        open_count = db.query(OptionsPaperTrade).filter(
            OptionsPaperTrade.status == "OPEN").count()
        if open_count >= MAX_OPTION_POSITIONS:
            return {"ok": False,
                    "reason": f"Max {MAX_OPTION_POSITIONS} open option positions (have {open_count})."}

        chain = _chain(underlying.upper(), expiry)
        if not chain.get("available"):
            return {"ok": False, "reason": f"Real chain unavailable: {chain.get('error', '')[:120]}"}
        ltp = _find_ltp(chain, strike, opt_type)
        if ltp is None:
            return {"ok": False,
                    "reason": f"No quoted LTP for {underlying} {strike} {opt_type} "
                              f"({chain['expirationDate']}) — strike illiquid or wrong."}

        cost = ltp * qty
        max_cost = config.capital * OPTION_MAX_COST_PCT / 100.0
        if cost > max_cost:
            return {"ok": False,
                    "reason": f"Premium ₹{cost:,.0f} exceeds {OPTION_MAX_COST_PCT}% of capital "
                              f"(₹{max_cost:,.0f}). Options me poora premium doobta hai — size chhota rakho."}

        row = OptionsPaperTrade(
            underlying=underlying.upper(), strike=float(strike), opt_type=opt_type,
            expiry=chain["expirationDate"], qty=int(qty), entry_ltp=ltp,
            note=f"underlying@{chain.get('underlyingPrice')}",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "ok": True, "id": row.id, "entry_ltp": ltp, "cost": round(cost, 2),
            "expiry": row.expiry, "mode": "PAPER",
            "note": "Real NSE quoted LTP; paper cannot simulate slippage/spread-cross — "
                    "real fills would be slightly worse.",
        }
    finally:
        db.close()


def positions() -> Dict[str, Any]:
    """Open PAPER option positions re-priced at the CURRENT real chain LTP."""
    from .db import SessionLocal, OptionsPaperTrade
    db = SessionLocal()
    try:
        rows = db.query(OptionsPaperTrade).filter(
            OptionsPaperTrade.status == "OPEN").all()
        out: List[Dict[str, Any]] = []
        chains: Dict[str, Dict] = {}
        for r in rows:
            key = f"{r.underlying}|{r.expiry}"
            if key not in chains:
                chains[key] = _chain(r.underlying, r.expiry)
            ch = chains[key]
            cur = _find_ltp(ch, r.strike, r.opt_type) if ch.get("available") else None
            unreal = round((cur - r.entry_ltp) * r.qty, 2) if cur else None
            out.append({
                "id": r.id, "underlying": r.underlying, "strike": r.strike,
                "type": r.opt_type, "expiry": r.expiry, "qty": r.qty,
                "entry_ltp": r.entry_ltp, "current_ltp": cur,
                "unrealized_pnl": unreal,
                "pricing": "real NSE chain" if cur else "chain unavailable right now",
            })
        return {"open": out, "count": len(out), "mode": "PAPER"}
    finally:
        db.close()


def close_trade(trade_id: int) -> Dict[str, Any]:
    """Close a PAPER option position at the current real LTP."""
    from .db import SessionLocal, OptionsPaperTrade
    db = SessionLocal()
    try:
        r = db.query(OptionsPaperTrade).filter(
            OptionsPaperTrade.id == trade_id,
            OptionsPaperTrade.status == "OPEN").first()
        if r is None:
            return {"ok": False, "reason": f"No OPEN option trade #{trade_id}"}
        ch = _chain(r.underlying, r.expiry)
        cur = _find_ltp(ch, r.strike, r.opt_type) if ch.get("available") else None
        if cur is None:
            return {"ok": False,
                    "reason": "Current LTP unavailable — cannot close honestly. Retry when NSE responds."}
        r.exit_ltp = cur
        r.pnl = round((cur - r.entry_ltp) * r.qty, 2)
        r.status = "CLOSED"
        r.closed_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True, "id": r.id, "exit_ltp": cur, "pnl": r.pnl, "mode": "PAPER"}
    finally:
        db.close()
