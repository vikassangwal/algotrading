"""Deterministic-ish mock market simulator for development and paper trading.

Uses a seeded random walk per symbol so tests are reproducible.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from .provider import (
    Candle, DataProvider, Fundamentals, NewsItem, OptionChain, OptionChainRow, Quote,
)

_BASE_PRICES = {
    "NIFTY": 24500.0,
    "BANKNIFTY": 52000.0,
    "SENSEX": 80500.0,
    "RELIANCE": 2950.0,
    "TCS": 3900.0,
    "HDFCBANK": 1650.0,
    "INFY": 1580.0,
}

_TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1d": 60 * 24}

_HEADLINE_POOL = [
    ("RBI keeps repo rate unchanged, stance neutral", 20),
    ("FII selling continues for third straight session", 45),
    ("Q1 earnings beat estimates across IT majors", 15),
    ("Global markets slide on US inflation surprise", 60),
    ("SEBI tightens F&O margin norms", 40),
    ("Rupee hits record low against dollar", 55),
    ("Banking stocks rally on credit growth data", 10),
    ("Geopolitical tensions escalate; crude spikes 4%", 70),
]


class MockProvider(DataProvider):
    def __init__(self, seed: int = 42):
        self._seed = seed

    def _rng(self, *keys) -> random.Random:
        return random.Random((self._seed, *keys))

    def _base(self, symbol: str) -> float:
        return _BASE_PRICES.get(symbol.upper(), 1000.0 + (hash(symbol.upper()) % 3000))

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        rng = self._rng(symbol.upper(), timeframe)
        minutes = _TF_MINUTES.get(timeframe, 5)
        price = self._base(symbol)
        now = datetime.now(timezone.utc)
        candles: list[Candle] = []
        # gentle sinusoidal drift + noise so indicators have structure
        for i in range(count):
            drift = math.sin(i / 17) * 0.0015
            ret = rng.gauss(drift, 0.004)
            o = price
            c = price * (1 + ret)
            hi = max(o, c) * (1 + abs(rng.gauss(0, 0.0015)))
            lo = min(o, c) * (1 - abs(rng.gauss(0, 0.0015)))
            candles.append(Candle(
                ts=now - timedelta(minutes=minutes * (count - i)),
                open=round(o, 2), high=round(hi, 2), low=round(lo, 2), close=round(c, 2),
                volume=int(abs(rng.gauss(500_000, 150_000))),
            ))
            price = c
        return candles

    def get_quote(self, symbol: str) -> Quote:
        last = self.get_candles(symbol, "1m", 2)[-1]
        prev = self._base(symbol)
        return Quote(
            symbol=symbol.upper(), ltp=last.close,
            change_pct=round((last.close - prev) / prev * 100, 2),
            volume=last.volume, ts=datetime.now(timezone.utc),
        )

    def get_option_chain(self, symbol: str) -> OptionChain:
        rng = self._rng(symbol.upper(), "oc")
        spot = self.get_quote(symbol).ltp
        step = 50 if spot < 30000 else 100
        atm = round(spot / step) * step
        rows = []
        for k in range(-5, 6):
            strike = atm + k * step
            dist = abs(k)
            rows.append(OptionChainRow(
                strike=strike,
                call_oi=int(rng.gauss(1_500_000, 300_000) * (1 + max(0, k) * 0.3) / (1 + dist * 0.1)),
                put_oi=int(rng.gauss(1_500_000, 300_000) * (1 + max(0, -k) * 0.3) / (1 + dist * 0.1)),
                call_oi_change=int(rng.gauss(0, 120_000)),
                put_oi_change=int(rng.gauss(0, 120_000)),
                call_iv=round(max(rng.gauss(14 + dist, 1.5), 5), 2),
                put_iv=round(max(rng.gauss(15 + dist, 1.5), 5), 2),
            ))
        return OptionChain(symbol=symbol.upper(), spot=spot, expiry="weekly", rows=rows)

    def get_news(self, limit: int = 20) -> list[NewsItem]:
        rng = self._rng("news", datetime.now(timezone.utc).strftime("%Y%m%d%H"))
        picks = rng.sample(_HEADLINE_POOL, k=min(limit, len(_HEADLINE_POOL)))
        now = datetime.now(timezone.utc)
        return [
            NewsItem(headline=h, source="mock-wire", ts=now - timedelta(minutes=i * 7))
            for i, (h, _sev) in enumerate(picks)
        ]

    def get_fundamentals(self, symbol: str) -> dict:
        return {
            "net_income": 1200, "shareholder_equity": 6000, "ebit": 1500, "capital_employed": 5500,
            "total_debt": 2000, "current_assets": 3000, "current_liabilities": 1800,
            "eps_growth_yoy": 0.18, "operating_cash_flow": 1400, "capex": 400, "operating_income": 1600, "revenue": 7000,
            "pe_ratio": 12.5, "pb_ratio": 1.8, "ev_ebitda": 7.5,
            "eps": 45, "bvps": 250, "dcf_fair_value": 1100,
            "altman_z_score": 3.8, "piotroski_f_score": 8, "beneish_m_score": -2.8, "auditor_qualified_opinion": False,
            "fii_holding_change_qoy": 0.03, "dii_holding_change_qoy": 0.02, "promoter_pledge_pct": 0.05,
            "macro_interest_rate": 6.5, "sector_growth_rate": 0.10, "revenue_growth_yoy": 0.18,
            "alt_data_web_traffic_growth": 0.20
        }

    def get_macro_data(self) -> dict:
        return {
            "gdp_growth_pct": 7.2, "cpi_inflation_pct": 4.5, "unemployment_rate": 6.8,
            "us_10y_yield": 4.1, "india_10y_yield": 7.05, "india_2y_yield": 6.9,
            "rbi_policy_bias": "Dovish", "fiscal_deficit_to_gdp": 5.8,
            "pmi_manufacturing": 56.5, "pmi_services": 59.0, "iip_growth": 5.2, "credit_growth": 15.0,
            "brent_crude_usd": 75.0, "usd_inr": 83.2, "gold_trend_up": True, "dxy_index": 103.5,
            "systemic_risk_level": "Low",
            "business_cycle_phase": "Expansion", "asset_sector": "Banking"
        }

    def get_intermarket_data(self) -> dict:
        return {
            "us_10y_yield": 4.1, "corporate_hy_spread": 3.5, "yield_curve_status": "Normal",
            "dxy_trend": "Falling", "inr_trend": "Appreciating",
            "crude_trend": "Falling", "gold_trend": "Rising", "copper_trend": "Rising",
            "risk_regime": "Risk-On", "smallcap_vs_largecap": 1.2, "vix_level": 13.5,
            "eq_yield_corr": -0.7, "usd_em_corr": -0.8
        }

    def get_sector_data(self, sector_name: str) -> dict:
        return {
            "theme_momentum": "High", "government_policy_support": "Positive", "entry_barriers": "High",
            "sector_alpha_1m": 0.045, "sector_rs_vs_nifty": 1.12, "stocks_above_200dma_pct": 85.0,
            "sector_current_pe": 18.0, "sector_historical_pe": 15.5,
            "sector_roe": 14.5, "sector_eps_growth_yoy": 0.18,
            "fii_sector_net_flow": "Buying", "dii_sector_net_flow": "Buying", "sector_beta": 1.15
        }

    def get_derivatives_data(self, symbol: str) -> dict:
        # Keys named to match every consumer (derivatives_branches/*, order_flow,
        # institutional_positioning). Mock/demo values — replace with a real F&O
        # feed (Dhan/NSE) when available.
        return {
            # Futures / rollover (futures_rollover.py)
            "futures_price_change_pct": 0.012,
            "futures_oi_change_pct": 0.055,
            "futures_rollover_pct": 0.82,
            "historical_rollover_avg_pct": 0.75,
            "cost_of_carry_trend": "positive",
            # Options chain / max pain / PCR (options_chain.py)
            "put_call_ratio": 1.1,
            "max_pain_strike": 2900,
            "spot_price": 2950,
            # Volatility / greeks (volatility_greeks.py)
            "atm_call_iv": 14.5,
            "atm_put_iv": 15.2,
            "iv_rank": 45.0,
            "gamma_exposure": -150000,
            # Institutional positioning (institutional_positioning.py, order_flow.py)
            "fii_index_futures_long_ratio": 0.62,
            "fii_index_futures_bias": "Bullish",
            "client_options_bias": "Bearish",
            "fii_options_bias": "Bullish",
            "call_writing_strength": 300000,
            "put_writing_strength": 500000,
            "dealer_gex": -150000,
        }

    def get_sentiment_data(self, symbol: str) -> dict:
        return {
            "news_polarity_score": 0.6, "news_volume_spike": 1.5, "is_major_event_day": False,
            "social_buzz_score": 0.8, "retail_fomo_flag": True, "fear_greed_index": 85,
            "dark_pool_buy_volume": 5000000, "dark_pool_sell_volume": 1200000, "institutional_block_ratio": 2.5,
            "advance_decline_ratio": 1.5, "new_highs_vs_lows": 4.0, "vix_term_structure": "Contango",
            "dealer_gex": -150000, "cot_commercial_net_short": True
        }

    def get_quant_data(self, symbol: str) -> dict:
        return {
            "price_z_score": 1.2, "rsi_14": 65, "macd_hist": 2.5,
            "arima_forecast_pct": 0.025, "garch_vol_forecast": 0.018,
            "hmm_market_regime": "Trending Up", "xgboost_win_probability": 0.75, "lstm_price_target": 2980,
            "var_95_pct": -0.04, "cvar_95_pct": -0.06, "momentum_factor_score": 0.85, "value_factor_score": 0.40, "quality_factor_score": 0.90,
            "pair_spread_z_score": -2.8, "bid_ask_imbalance": 0.25, "tick_trade_flow": 1500000
        }

    def get_portfolio_data(self) -> dict:
        return {
            "max_sector_weight_limit": 0.25, "max_stock_weight_limit": 0.10, "current_sector_exposure": 0.18,
            "current_portfolio_beta": 1.15, "current_dominant_factor": "Momentum", "avg_correlation": 0.45,
            "unrealized_short_term_losses": 45000, "cash_reserves": 500000
        }

# severity lookup used by the news_risk module (mock NLP)
HEADLINE_SEVERITY = dict(_HEADLINE_POOL)
