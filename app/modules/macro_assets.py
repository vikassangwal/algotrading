"""Multi-asset macro watch — real data, ANALYSIS ONLY.

Gold, silver, crude, USDINR, Bitcoin, Ethereum vs NIFTY: price, momentum,
trend state and 90-day correlation with NIFTY. These move Indian equities
(crude up + INR weak = importers bleed; gold up = risk-off).

Execution for these assets is deliberately absent: MCX/CDS/crypto are
different exchanges, brokers and regulatory regimes — pretending to trade
them here would be fake. Watch, correlate, and let it inform equity bias.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("elco.macro")

ASSETS = {
    "GOLD": ("GC=F", "Gold futures (COMEX, USD)"),
    "SILVER": ("SI=F", "Silver futures (COMEX, USD)"),
    "CRUDE": ("CL=F", "WTI crude futures (USD)"),
    "USDINR": ("USDINR=X", "USD/INR"),
    "BITCOIN": ("BTC-USD", "Bitcoin (USD)"),
    "ETHEREUM": ("ETH-USD", "Ethereum (USD)"),
    "NIFTY": ("^NSEI", "NIFTY 50"),
}


def _trend(close: pd.Series) -> str:
    e20 = close.ewm(span=20).mean().iloc[-1]
    e50 = close.ewm(span=50).mean().iloc[-1]
    px = close.iloc[-1]
    if px > e20 > e50:
        return "UPTREND"
    if px < e20 < e50:
        return "DOWNTREND"
    return "MIXED"


def macro_watch() -> Dict[str, Any]:
    """Real multi-asset snapshot + NIFTY correlations."""
    import yfinance as yf
    try:
        raw = yf.download([t for t, _ in ASSETS.values()], period="1y",
                          interval="1d", progress=False, auto_adjust=True,
                          group_by="ticker", threads=True)
    except Exception as e:
        return {"error": f"macro download failed: {e}", "assets": {}}

    closes: Dict[str, pd.Series] = {}
    out: Dict[str, Any] = {}
    for name, (ticker, desc) in ASSETS.items():
        try:
            df = raw[ticker] if isinstance(raw.columns, pd.MultiIndex) else raw
            c = df["Close"].dropna()
            if len(c) < 60:
                out[name] = {"available": False, "reason": "insufficient data"}
                continue
            closes[name] = c
            out[name] = {
                "available": True,
                "description": desc,
                "price": round(float(c.iloc[-1]), 2),
                "change_1d_pct": round(100 * (float(c.iloc[-1]) / float(c.iloc[-2]) - 1), 2),
                "change_1m_pct": round(100 * (float(c.iloc[-1]) / float(c.iloc[-22]) - 1), 2) if len(c) > 22 else None,
                "trend": _trend(c),
            }
        except Exception as e:
            out[name] = {"available": False, "reason": str(e)[:60]}

    # 90-day correlation with NIFTY.
    if "NIFTY" in closes:
        nifty_ret = closes["NIFTY"].pct_change().dropna().tail(90)
        for name, c in closes.items():
            if name == "NIFTY" or not out[name].get("available"):
                continue
            r = c.pct_change().dropna().tail(90)
            joined = pd.concat([nifty_ret, r], axis=1, join="inner").dropna()
            if len(joined) > 30:
                out[name]["corr_nifty_90d"] = round(float(joined.iloc[:, 0].corr(joined.iloc[:, 1])), 2)

    return {
        "assets": out,
        "note": (
            "ANALYSIS ONLY — no execution for commodities/currency/crypto "
            "(different exchanges and regulation; faking it would be dishonest). "
            "Use as macro context for equity bias."
        ),
    }
