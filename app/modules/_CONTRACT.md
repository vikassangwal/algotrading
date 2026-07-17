# ELCO Analysis Module — Shared Contract (READ BEFORE CODING)

Every analysis module you build MUST follow this exact contract so it plugs
into the engine without breaking anything. Consistency > cleverness.

## 1. File & class

- One module per file in `app/modules/<name>.py`.
- Subclass `AnalysisModule` from `app/modules/base.py`.
- Set a unique lowercase `name` (used as the config key and dict key).

```python
import logging
import pandas as pd
import numpy as np
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.<name>")

class <Name>Module(AnalysisModule):
    name = "<name>"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            # ... real computation from self.provider ...
            return ModuleSignal(self.name, score, confidence, reasons)
        except Exception as e:
            logger.error(f"{self.name} failed on {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, [f"{self.name}: data unavailable"])
```

## 2. Return contract — `ModuleSignal(module, score, confidence, reasons)`

- `score`: float in **[-1.0, +1.0]**. -1 = strong bearish/sell, +1 = strong bullish/buy, 0 = neutral. (Auto-clamped, but stay in range.)
- `confidence`: float in **[0.0, 1.0]** — how much the module trusts its own read. Low data quality → low confidence, NOT a fake score.
- `reasons`: list[str], 2-6 short human-readable bullet strings explaining the read (shown in the panel breakdown). Include the key numbers.

## 3. HARD RULES

1. **NO `np.random` / `random` anywhere.** Signals must be derived from real data. If data is missing, return `score=0.0, confidence` low — never fabricate.
2. **Never raise out of `analyze()`** — always wrap in try/except and return a neutral low-confidence signal on failure. A crashing module must not take down the panel.
3. **Only read data via `self.provider`** — the interface methods below. Do not call yfinance/network directly.
4. **Be fast** — no sleeps, no heavy loops over full history when a vectorized pandas/numpy op works. Cache nothing in globals.
5. **Deterministic** — same input → same output.

## 4. Available provider methods (READ-ONLY)

```
self.provider.get_quote(symbol) -> Quote(symbol, ltp, change_pct, volume, ts)
self.provider.get_candles(symbol, timeframe, count) -> [Candle(ts,open,high,low,close,volume)]   # timeframe: '1m'|'5m'|'15m'|'1d'
self.provider.get_option_chain(symbol) -> OptionChain(symbol, spot, expiry, rows=[OptionChainRow(strike,call_oi,put_oi,call_oi_change,put_oi_change,call_iv,put_iv)])
self.provider.get_news(limit) -> [NewsItem(headline, source, ts, symbols)]
self.provider.get_fundamentals(symbol) -> dict   # pe_ratio, pb_ratio, roe, net_income, total_debt, revenue, eps_growth_yoy, altman_z_score, piotroski_f_score, promoter_pledge_pct, fii_holding_change_qoy, ...
self.provider.get_macro_data() -> dict           # gdp_growth_pct, cpi_inflation_pct, us_10y_yield, india_10y_yield, central_bank_stance, pmi_mfg, brent_crude_usd, usd_inr, business_cycle_phase, ...
self.provider.get_intermarket_data() -> dict     # us_10y_yield, dxy_trend, crude_trend, gold_trend, risk_regime, vix_level, ...
self.provider.get_sector_data(sector) -> dict    # theme_momentum, sector_alpha_1m, sector_rs_vs_nifty, sector_current_pe, sector_historical_pe, fii_sector_net_flow, ...
self.provider.get_derivatives_data(symbol) -> dict  # pcr_ratio, futures_oi_change, rollover_pct, max_pain, call_writing_strength, put_writing_strength, fii_index_futures_bias, dealer_gex, ...
self.provider.get_sentiment_data(symbol) -> dict # news_polarity_score, social_buzz_score, fear_greed_index, dark_pool_buy_volume, advance_decline_ratio, cot_commercial_net_short, ...
self.provider.get_quant_data(symbol) -> dict     # price_z_score, rsi_14, macd_hist, arima_forecast_pct, hmm_market_regime, xgboost_win_probability, var_95_pct, momentum_factor_score, value_factor_score, quality_factor_score, ...
self.provider.get_portfolio_data() -> dict       # max_sector_weight_limit, current_sector_exposure, current_portfolio_beta, avg_correlation, cash_reserves, ...
```

Indicators available in `app/modules/indicators.py`: `calculate_ema, calculate_rsi, calculate_vwap, calculate_supertrend, calculate_bollinger_bands, calculate_ichimoku, calculate_stochastic_oscillator, calculate_mfi, calculate_obv, calculate_pivot_points, calculate_fibonacci_retracements`.

To turn candles into a DataFrame (lowercase columns):
```python
candles = self.provider.get_candles(symbol, "1d", 250)
df = pd.DataFrame([{"open":c.open,"high":c.high,"low":c.low,"close":c.close,"volume":c.volume} for c in candles])
```

## 5. Do NOT touch

- Do not edit `base.py`, `engine.py`, `config.py`, `main.py`, `provider.py`, or any other module. Only create your assigned new file(s). Integration is done centrally.
- Do not add new pip dependencies.
