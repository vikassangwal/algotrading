"""Portfolio heatmap — REAL data only.

Old version: hardcoded allocations + random jitter "so the heatmap looks
alive". Deleted. Now:

  * If there are OPEN POSITIONS: the heatmap shows the actual portfolio —
    real allocation (qty × entry) and the real % move since entry.
  * Otherwise: a MARKET heatmap of liquid NIFTY-50 names with today's REAL
    % change (one batched yfinance download), labeled as market view.
Symbols whose data can't be fetched are omitted, never invented.
"""
import logging
from typing import Dict, List

logger = logging.getLogger("elco.portfolio_data")

_SECTOR = {
    "HDFCBANK": "Financials", "ICICIBANK": "Financials", "SBIN": "Financials",
    "KOTAKBANK": "Financials", "AXISBANK": "Financials", "BAJFINANCE": "Financials",
    "INDUSINDBK": "Financials", "SBILIFE": "Financials", "HDFCLIFE": "Financials",
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT",
    "RELIANCE": "Energy", "ONGC": "Energy", "NTPC": "Energy", "POWERGRID": "Energy",
    "COALINDIA": "Energy", "BPCL": "Energy", "ADANIENT": "Energy",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG",
    "TATACONSUM": "FMCG", "TITAN": "Consumer", "ASIANPAINT": "Consumer",
    "LT": "Industrials", "ULTRACEMCO": "Industrials", "GRASIM": "Industrials",
    "ADANIPORTS": "Industrials", "JSWSTEEL": "Metals", "TATASTEEL": "Metals",
    "HINDALCO": "Metals", "MARUTI": "Auto", "M&M": "Auto", "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto", "BAJAJ-AUTO": "Auto", "TATAMOTORS": "Auto",
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma",
    "DIVISLAB": "Pharma", "APOLLOHOSP": "Pharma", "BHARTIARTL": "Telecom",
}


class PortfolioDataEngine:
    def __init__(self, execution_engine=None):
        self.execution_engine = execution_engine

    def get_heatmap_data(self) -> Dict:
        # 1. Real portfolio view when positions exist.
        if self.execution_engine and self.execution_engine.open_positions:
            return self._positions_heatmap()
        # 2. Otherwise a real market view.
        return self._market_heatmap()

    def _positions_heatmap(self) -> Dict:
        rows = []
        for sym, t in self.execution_engine.open_positions.items():
            try:
                ltp = self.execution_engine.provider.get_quote(sym).ltp
                chg = round(100.0 * (ltp - t.entry_price) / t.entry_price, 2)
                if t.action != "BUY":
                    chg = -chg
            except Exception:
                chg = 0.0
            rows.append({"symbol": sym, "alloc": round(t.qty * t.entry_price, 0),
                         "chg": chg})
        return self._to_treemap(rows, title="Open Positions (real P&L %)")

    def _market_heatmap(self) -> Dict:
        try:
            import pandas as pd
            import yfinance as yf
            syms = list(_SECTOR.keys())
            raw = yf.download([f"{s}.NS" for s in syms], period="5d", interval="1d",
                              progress=False, auto_adjust=True, group_by="ticker",
                              threads=True)
            rows = []
            for s in syms:
                try:
                    df = raw[f"{s}.NS"] if isinstance(raw.columns, pd.MultiIndex) else raw
                    close = df["Close"].dropna()
                    if len(close) < 2:
                        continue
                    chg = round(100.0 * (float(close.iloc[-1]) / float(close.iloc[-2]) - 1), 2)
                    # Size by real traded value so big names read bigger.
                    vol = float(df["Volume"].dropna().iloc[-1])
                    rows.append({"symbol": s, "alloc": round(float(close.iloc[-1]) * vol / 1e7, 1),
                                 "chg": chg})
                except Exception:
                    continue
            return self._to_treemap(rows, title="Market heatmap (today's real % change)")
        except Exception as e:
            logger.warning(f"Market heatmap failed: {e}")
            return {"name": "Portfolio", "children": [],
                    "error": f"heatmap data unavailable: {e}"}

    @staticmethod
    def _to_treemap(rows: List[Dict], title: str) -> Dict:
        grouped: Dict[str, List[Dict]] = {}
        for r in rows:
            sec = _SECTOR.get(r["symbol"], "Other")
            grouped.setdefault(sec, []).append({
                "name": r["symbol"], "size": r["alloc"],
                "change": r["chg"], "sector": sec,
            })
        return {
            "name": "Portfolio",
            "title": title,
            "children": [{"name": sec, "children": items}
                         for sec, items in grouped.items()],
        }
