"""Confluence trade-setup engine — EVERY analysis votes, one honest setup.

Pulls the full analysis (indicators, market structure/SMC, regime,
institutional flows, deployed validated strategies, fused 4-pillar signal)
and scores each dimension as a FACTOR with a direction and weight:

    factor                        weight   why
    ------------------------------------------------------------------
    deployed validated strategy      3     only thing with tested stats
    market structure trend           2     HH/HL vs LH/LL backbone
    BOS / CHOCH                      2     fresh structural evidence
    indicator consensus              2     9-11 textbook readings tally
    fused 4-pillar signal            2     multi-module engine
    premium/discount zone            1     where in the range price is
    fresh liquidity sweep            1     stop-hunt reversal evidence
    FII/DII flows (market-wide)      1     institutional tailwind
    delivery % vs 40%                1     conviction behind moves
    ADX trend strength               1     is there even a trend to ride

The setup direction needs a clear margin of bull vs bear points AND a
minimum total — otherwise the verdict is NO_TRADE with the reason shown.
Entry/SL/target use the SAME mandatory R3 math execution enforces, with the
target capped at the nearest strong opposing S/R zone when one is closer.

This module never places orders. The /execute endpoint routes through
RiskManager sizing + ExecutionEngine (rules R1-R7) like every other trade.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("elco.confluence")

MIN_SCORE_MARGIN = 3      # bull vs bear point gap required
MIN_TOTAL_POINTS = 6      # thin evidence = no setup, even if one-sided
DELIVERY_CONVICTION = 40.0  # % delivery above this = conviction factor


def _factor(name: str, direction: str, weight: int, detail: str) -> Dict[str, Any]:
    return {"name": name, "direction": direction, "weight": weight, "detail": detail}


def build_trade_setup(symbol: str, provider, engine) -> Dict[str, Any]:
    """Score every analysis dimension into one honest setup verdict."""
    from .full_analysis import full_analysis

    fa = full_analysis(symbol, provider, engine)
    if "error" in fa:
        return {"symbol": symbol.upper(), "verdict": "NO_TRADE", "reason": fa["error"]}

    factors: List[Dict[str, Any]] = []

    # 1. Deployed validated strategies (weight 3 — the only tested edge).
    fired = [d for d in fa.get("deployed_strategies", [])
             if d.get("signal") in ("BUY", "SELL")]
    for d in fired:
        direction = "BULL" if d["signal"] == "BUY" else "BEAR"
        gate = "" if d.get("regime_ok") else " (BLOCKED by regime gate)"
        factors.append(_factor(
            f"validated strategy: {d['name']}",
            direction if d.get("regime_ok") else "NEUTRAL", 3,
            f"out-of-sample validated strategy fired {d['signal']}{gate}",
        ))

    # 2. Market structure trend (weight 2).
    smc = fa.get("smc", {})
    ms = smc.get("market_structure", {})
    trend = ms.get("trend")
    if trend in ("BULLISH", "BEARISH"):
        factors.append(_factor(
            "market structure", "BULL" if trend == "BULLISH" else "BEAR", 2,
            f"{trend} structure {ms.get('recent_labels')}",
        ))

    # 3. BOS / CHOCH (weight 2) — fresh structural break beats stale trend.
    bos, choch = ms.get("bos"), ms.get("choch")
    if choch:
        factors.append(_factor(
            "change of character", "BULL" if choch["direction"] == "BULLISH" else "BEAR", 2,
            choch["meaning"],
        ))
    elif bos:
        factors.append(_factor(
            "break of structure", "BULL" if bos["direction"] == "BULLISH" else "BEAR", 2,
            bos["meaning"],
        ))

    # 4. Indicator consensus (weight 2).
    cons = fa.get("indicator_consensus", {})
    if cons.get("lean") in ("BULLISH", "BEARISH"):
        factors.append(_factor(
            "indicator consensus", "BULL" if cons["lean"] == "BULLISH" else "BEAR", 2,
            f"{cons.get('bullish')} bullish vs {cons.get('bearish')} bearish readings",
        ))

    # 5. Fused 4-pillar signal (weight 2).
    fused = fa.get("fused_signal", {})
    if fused.get("action") in ("BUY", "SELL"):
        factors.append(_factor(
            "fused signal", "BULL" if fused["action"] == "BUY" else "BEAR", 2,
            f"score {fused.get('score')} confidence {fused.get('confidence')}",
        ))

    # 6. Premium / discount (weight 1).
    pdz = smc.get("premium_discount", {})
    zone = str(pdz.get("zone", ""))
    if zone.startswith("DISCOUNT"):
        factors.append(_factor("premium/discount", "BULL", 1,
                               f"price in discount ({pdz.get('position')}) — buy-favored zone"))
    elif zone.startswith("PREMIUM"):
        factors.append(_factor("premium/discount", "BEAR", 1,
                               f"price in premium ({pdz.get('position')}) — sell-favored zone"))

    # 7. Fresh liquidity sweep (weight 1) — only bars_ago == 0 counts.
    for s in smc.get("liquidity_sweeps", []):
        if s.get("bars_ago") == 0:
            direction = "BULL" if s["kind"] == "SELL_SIDE_SWEEP" else "BEAR"
            factors.append(_factor("liquidity sweep", direction, 1, s["meaning"]))
            break

    # 8. FII/DII (weight 1, market-wide context).
    inst = fa.get("institutional", {})
    fd = inst.get("fii_dii") or {}
    fii, dii = fd.get("fii_net"), fd.get("dii_net")
    if fii is not None and dii is not None:
        net = float(fii) + float(dii)
        if abs(net) > 500:  # crores; ignore noise
            factors.append(_factor(
                "FII/DII flows", "BULL" if net > 0 else "BEAR", 1,
                f"combined net {'buying' if net > 0 else 'selling'} ₹{abs(net):.0f} cr ({fd.get('date')})",
            ))

    # 9. Delivery conviction (weight 1) — high delivery = real hands, and it
    # amplifies whichever way TODAY's candle went.
    dl = inst.get("delivery") or {}
    dp = dl.get("delivery_percentage")
    chg = (fa.get("quote") or {}).get("change_pct")
    if dp is not None and chg is not None and dp >= DELIVERY_CONVICTION and abs(chg) > 0.1:
        factors.append(_factor(
            "delivery conviction", "BULL" if chg > 0 else "BEAR", 1,
            f"{dp}% delivery behind a {chg:+}% day — positions being carried home",
        ))

    # 10. ADX (weight 1) — supports whichever structural direction exists.
    adx = smc.get("adx", {})
    if adx.get("adx") is not None and adx["adx"] >= 25 and trend in ("BULLISH", "BEARISH"):
        factors.append(_factor(
            "ADX trend strength", "BULL" if trend == "BULLISH" else "BEAR", 1,
            f"ADX {adx['adx']} — trend strong enough to trade",
        ))

    # ---- Tally --------------------------------------------------------------
    bull = sum(f["weight"] for f in factors if f["direction"] == "BULL")
    bear = sum(f["weight"] for f in factors if f["direction"] == "BEAR")
    total = bull + bear
    margin = abs(bull - bear)

    if total < MIN_TOTAL_POINTS:
        verdict, reason = "NO_TRADE", (
            f"Too little evidence ({total} points total, need {MIN_TOTAL_POINTS}). "
            "Most days are no-trade days — that is the system working."
        )
    elif margin < MIN_SCORE_MARGIN:
        verdict, reason = "NO_TRADE", (
            f"Analyses conflict (bull {bull} vs bear {bear}, margin {margin} < "
            f"{MIN_SCORE_MARGIN}). Conflicting evidence = stay out."
        )
    else:
        verdict = "BUY" if bull > bear else "SELL"
        reason = f"Confluence {('bull ' + str(bull) + ' vs bear ' + str(bear))} with margin {margin}."

    setup: Dict[str, Any] = {
        "symbol": fa["symbol"],
        "verdict": verdict,
        "reason": reason,
        "confluence": {"bull_points": bull, "bear_points": bear, "margin": margin,
                       "factors": factors},
        "quote": fa.get("quote"),
        "regime": (fa.get("regime") or {}).get("regime"),
    }

    # Trade plan only when there IS a trade — R3 math + S/R-aware target cap.
    if verdict in ("BUY", "SELL"):
        plan = dict((fa.get("trade_plan") or {}).get("if_buy" if verdict == "BUY" else "if_sell") or {})
        price = (fa.get("quote") or {}).get("price")
        zones = smc.get("support_resistance", [])
        if plan and price:
            opposing = [z for z in zones if z["touches"] >= 3 and (
                (verdict == "BUY" and z["kind"] == "RESISTANCE") or
                (verdict == "SELL" and z["kind"] == "SUPPORT"))]
            if opposing:
                nearest = opposing[0]["level"]
                if verdict == "BUY" and nearest < plan.get("target", nearest + 1):
                    plan["target_capped_at_resistance"] = nearest
                elif verdict == "SELL" and nearest > plan.get("target", nearest - 1):
                    plan["target_capped_at_support"] = nearest
        setup["trade_plan"] = {
            "entry_ref": price,
            **plan,
            "atr_14": (fa.get("trade_plan") or {}).get("atr_14"),
            "note": "SL/target from mandatory R3 math; execution enforces the same.",
        }

    setup["disclaimer"] = (
        "A scored summary of real analyses, not advice. NO_TRADE is the most "
        "common and most protective outcome."
    )
    return setup
