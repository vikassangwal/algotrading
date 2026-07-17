"""Trading-type weight matrix + overall verdict.

The user's core ask: for EACH kind of trading (intraday, swing, options buying,
futures, pair trading, hedging, …) different analyses matter differently. This
file encodes "kis trading me kis analysis ko kitna mahatva" as a weight matrix,
then fuses the per-module signals into an overall Bullish/Bearish verdict for
each trading type.

Weights are 0..1 importance multipliers. A module absent from a type's map gets
DEFAULT_WEIGHT. The final score is a confidence-weighted, importance-weighted
average of module scores, so a module the type cares about moves the needle more.
"""
from __future__ import annotations

DEFAULT_WEIGHT = 0.3

# Every analysis module name the system can produce a signal from.
ALL_MODULES = [
    "technical", "fundamental", "quant", "sentiment", "macro", "sector",
    "industry", "company", "financial_statement", "ratio", "valuation",
    "risk_analysis", "portfolio_analysis", "derivatives", "order_flow",
    "volume", "smart_money", "behavioral", "intermarket", "alternative_data",
    "event_driven", "cycle", "esg", "credit", "options_flow", "news_risk",
]

# trading_type -> {module: importance weight 0..1}. Only the analyses that
# genuinely drive that style are listed; others fall back to DEFAULT_WEIGHT.
WEIGHT_MATRIX = {
    # Ultra-short: price action, order flow, volume, live sentiment dominate.
    "scalping": {
        "technical": 1.0, "volume": 0.9, "order_flow": 0.9, "smart_money": 0.7,
        "sentiment": 0.6, "derivatives": 0.5, "behavioral": 0.5,
        "fundamental": 0.0, "valuation": 0.0, "esg": 0.0, "credit": 0.0,
    },
    "intraday": {
        "technical": 0.9, "volume": 0.8, "order_flow": 0.8, "news_risk": 0.7,
        "sentiment": 0.7, "smart_money": 0.6, "derivatives": 0.6, "event_driven": 0.6,
        "fundamental": 0.1, "valuation": 0.1, "esg": 0.0, "credit": 0.1,
    },
    "swing": {
        "technical": 0.8, "quant": 0.6, "sector": 0.6, "smart_money": 0.6,
        "volume": 0.6, "sentiment": 0.5, "event_driven": 0.6, "cycle": 0.6,
        "fundamental": 0.5, "valuation": 0.4, "industry": 0.5,
    },
    "positional": {
        "fundamental": 0.8, "valuation": 0.7, "sector": 0.7, "industry": 0.7,
        "macro": 0.6, "quant": 0.5, "technical": 0.5, "cycle": 0.6,
        "company": 0.7, "financial_statement": 0.6, "credit": 0.5,
    },
    # Long side of options — direction + volatility + flow.
    "options_buying": {
        "technical": 0.8, "derivatives": 1.0, "order_flow": 0.8, "volume": 0.7,
        "sentiment": 0.7, "smart_money": 0.7, "risk_analysis": 0.7, "event_driven": 0.7,
        "fundamental": 0.0, "valuation": 0.0,
    },
    # Short side of options — theta/OI/max-pain, mean reversion, risk.
    "options_selling": {
        "derivatives": 1.0, "risk_analysis": 0.9, "order_flow": 0.7, "volume": 0.6,
        "smart_money": 0.6, "behavioral": 0.6, "technical": 0.5, "sentiment": 0.5,
        "fundamental": 0.0, "valuation": 0.0,
    },
    "futures": {
        "technical": 0.8, "derivatives": 0.9, "order_flow": 0.8, "smart_money": 0.7,
        "quant": 0.6, "intermarket": 0.6, "volume": 0.7, "risk_analysis": 0.6,
        "fundamental": 0.2, "valuation": 0.1,
    },
    "equity": {
        "fundamental": 0.8, "valuation": 0.7, "technical": 0.6, "company": 0.7,
        "financial_statement": 0.7, "sector": 0.6, "industry": 0.6, "quant": 0.5,
        "smart_money": 0.6, "credit": 0.5, "esg": 0.4, "cycle": 0.5,
    },
    "commodity": {
        "macro": 0.9, "intermarket": 0.9, "technical": 0.7, "sentiment": 0.6,
        "cycle": 0.7, "event_driven": 0.6, "quant": 0.5, "order_flow": 0.6,
        "fundamental": 0.1, "valuation": 0.0, "esg": 0.0,
    },
    "currency": {
        "macro": 1.0, "intermarket": 0.9, "technical": 0.6, "event_driven": 0.6,
        "quant": 0.6, "sentiment": 0.5, "cycle": 0.6,
        "fundamental": 0.0, "valuation": 0.0, "company": 0.0, "esg": 0.0,
    },
    "etf": {
        "sector": 0.8, "industry": 0.7, "macro": 0.7, "quant": 0.6,
        "technical": 0.6, "intermarket": 0.6, "portfolio_analysis": 0.7, "cycle": 0.6,
        "valuation": 0.4, "company": 0.2,
    },
    "portfolio_strategy": {
        "portfolio_analysis": 1.0, "risk_analysis": 0.8, "quant": 0.7, "macro": 0.6,
        "sector": 0.6, "intermarket": 0.6, "valuation": 0.5, "credit": 0.5, "cycle": 0.5,
    },
    "basket_strategy": {
        "portfolio_analysis": 0.9, "sector": 0.8, "industry": 0.7, "quant": 0.7,
        "smart_money": 0.6, "technical": 0.5, "macro": 0.5, "risk_analysis": 0.6,
    },
    "pair_trading": {
        "quant": 1.0, "intermarket": 0.8, "risk_analysis": 0.7, "technical": 0.6,
        "sector": 0.6, "volume": 0.5, "portfolio_analysis": 0.6,
        "fundamental": 0.2, "esg": 0.0,
    },
    "hedging": {
        "risk_analysis": 1.0, "derivatives": 0.9, "intermarket": 0.7, "portfolio_analysis": 0.8,
        "macro": 0.6, "quant": 0.6, "order_flow": 0.5, "volume": 0.4,
    },
}

# Order shown in the UI.
TRADING_TYPES = list(WEIGHT_MATRIX.keys())


def _label(score: float) -> str:
    if score >= 0.5:
        return "Strong Bullish"
    if score >= 0.15:
        return "Bullish"
    if score <= -0.5:
        return "Strong Bearish"
    if score <= -0.15:
        return "Bearish"
    return "Neutral"


def verdict_for_type(trading_type: str, module_signals: dict) -> dict:
    """module_signals: {name: {"score":..., "confidence":...}}.

    Returns the overall verdict for one trading type + the top contributing
    analyses so the panel can show "kis analysis ne kya kaha".
    """
    weights = WEIGHT_MATRIX.get(trading_type, {})
    num = 0.0
    den = 0.0
    contributions = []
    for name, sig in module_signals.items():
        w = weights.get(name, DEFAULT_WEIGHT)
        if w <= 0:
            continue
        conf = sig.get("confidence", 0.0)
        score = sig.get("score", 0.0)
        eff = w * conf
        num += score * eff
        den += eff
        contributions.append({
            "analysis": name,
            "score": round(score, 3),
            "confidence": round(conf, 3),
            "weight": w,
            "impact": round(score * eff, 4),
        })

    overall = (num / den) if den > 0 else 0.0
    # Sort by absolute impact so the panel can highlight the drivers.
    contributions.sort(key=lambda c: abs(c["impact"]), reverse=True)

    # Directional probability: score/conviction -> UP/DOWN %.
    up = max(5.0, min(95.0, 50.0 + overall * 45.0))
    return {
        "trading_type": trading_type,
        "overall_score": round(overall, 4),
        "verdict": _label(overall),
        "bias": "BULLISH" if overall > 0.15 else ("BEARISH" if overall < -0.15 else "NEUTRAL"),
        "direction": {"up_pct": round(up, 1), "down_pct": round(100.0 - up, 1)},
        "top_drivers": contributions[:6],
    }


def verdicts_all_types(module_signals: dict) -> dict:
    """Overall Bullish/Bearish for EVERY trading type."""
    return {t: verdict_for_type(t, module_signals) for t in TRADING_TYPES}
