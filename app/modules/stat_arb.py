import logging
import pandas as pd
import numpy as np
import statsmodels.api as sm
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.stat_arb")

class StatArbModule(AnalysisModule):
    name = "stat_arb"

    def analyze(self, symbol: str) -> ModuleSignal:
        # In a real pairs trading strategy, we would define specific pairs.
        # Here we do an Index-Arbitrage (Beta-Neutral) approach: 
        # We compare the asset against the benchmark (NIFTY).
        benchmark = "NIFTY"
        
        if symbol == benchmark:
            return ModuleSignal(self.name, 0.0, 0.0, ["Cannot pair trade benchmark against itself."])

        try:
            # Fetch 100 days of data for OLS calculation
            sym_candles = self.provider.get_candles(symbol, timeframe="1d", count=100)
            bench_candles = self.provider.get_candles(benchmark, timeframe="1d", count=100)
        except Exception as e:
            logger.error(f"Failed to fetch data for Stat Arb: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch market data."])

        if len(sym_candles) < 100 or len(bench_candles) < 100:
            return ModuleSignal(self.name, 0.0, 0.1, ["Insufficient data for OLS regression."])

        # Create pandas dataframes
        df_sym = pd.DataFrame([c.close for c in sym_candles], columns=['sym'])
        df_bench = pd.DataFrame([c.close for c in bench_candles], columns=['bench'])

        # Align lengths just in case
        min_len = min(len(df_sym), len(df_bench))
        df_sym = df_sym.tail(min_len).reset_index(drop=True)
        df_bench = df_bench.tail(min_len).reset_index(drop=True)

        y = df_sym['sym']
        x = df_bench['bench']

        # Add constant for OLS
        X = sm.add_constant(x)
        
        # Perform OLS regression to find the hedge ratio (Beta)
        model = sm.OLS(y, X)
        results = model.fit()
        beta = results.params['bench']

        # Calculate the spread: Spread = Asset - Beta * Benchmark
        spread = y - (beta * x)
        
        # Calculate Z-Score of the spread
        spread_mean = spread.mean()
        spread_std = spread.std()
        
        if spread_std == 0:
            return ModuleSignal(self.name, 0.0, 0.0, ["Spread standard deviation is zero."])

        current_spread = spread.iloc[-1]
        z_score = (current_spread - spread_mean) / spread_std

        reasons = [
            f"StatArb (Beta-Neutral vs {benchmark})",
            f"Calculated Hedge Ratio (Beta): {beta:.4f}",
            f"Current Spread Z-Score: {z_score:.2f}"
        ]

        score = 0.0
        confidence = 0.0

        # Mean Reversion Logic
        # If Z-score < -2.0, the asset is heavily undervalued compared to the index (BUY)
        # If Z-score > 2.0, the asset is heavily overvalued compared to the index (SELL)
        # If Z-score crosses 0, we exit, but since this module just provides signals, 
        # we scale the score based on the Z-score.
        
        zscore_high = 2.0
        zscore_low = 0.5 # Threshold to exit / neutral

        if z_score < -zscore_high:
            score = 1.0 # Strong Buy
            confidence = 0.8
            reasons.append("Z-Score < -2.0: Asset is severely undervalued relative to benchmark. Mean reversion expected.")
        elif z_score > zscore_high:
            score = -1.0 # Strong Sell
            confidence = 0.8
            reasons.append("Z-Score > 2.0: Asset is severely overvalued relative to benchmark. Mean reversion expected.")
        elif abs(z_score) < zscore_low:
            score = 0.0
            confidence = 0.5
            reasons.append("Z-Score near 0: Spread is at its historical mean. No edge.")
        else:
            # Linear scaling between 0.5 and 2.0
            # For z = -1.5, score will be positive
            score = - (z_score / zscore_high)
            confidence = abs(score) * 0.5
            reasons.append("Spread is diverging but has not reached critical threshold.")

        # Cap score
        score = max(-1.0, min(1.0, score))

        return ModuleSignal(
            module=self.name,
            score=score,
            confidence=confidence,
            reasons=reasons
        )
