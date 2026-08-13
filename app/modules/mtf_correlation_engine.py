import pandas as pd
import numpy as np

class MTFCorrelationEngine:
    """
    Multiple Time Frame (MTF) Alignment and Cross-Asset Correlation Engine.
    """
    def __init__(self, df_1d: pd.DataFrame, df_15m: pd.DataFrame = None, df_benchmark: pd.DataFrame = None):
        self.df_1d = self._normalize_columns(df_1d)
        self.df_15m = self._normalize_columns(df_15m) if df_15m is not None and not df_15m.empty else None
        self.df_bench = self._normalize_columns(df_benchmark) if df_benchmark is not None and not df_benchmark.empty else None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("open", "high", "low", "close", "volume"):
                rename[col] = cl.capitalize()
        return df.rename(columns=rename) if rename else df

    def analyze(self) -> dict:
        mtf_signal = self._calc_mtf_alignment()
        corr_signal, rs_signal = self._calc_correlation_and_rs()
        
        return {
            "mtf_alignment": mtf_signal,
            "correlation_vs_benchmark": corr_signal,
            "relative_strength": rs_signal
        }
        
    def _calc_trend(self, df: pd.DataFrame) -> int:
        """Returns 1 for Bullish, -1 for Bearish, 0 for Neutral."""
        if df is None or len(df) < 20:
            return 0
        close = df['Close']
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        last = close.iloc[-1]
        
        if last > ema20 and ema20 > ema50:
            return 1
        elif last < ema20 and ema20 < ema50:
            return -1
        return 0

    def _calc_mtf_alignment(self) -> str:
        """Compares Daily trend with 15-Minute trend."""
        if self.df_1d is None or self.df_15m is None:
            return "MTF Data Unavailable"
            
        trend_1d = self._calc_trend(self.df_1d)
        trend_15m = self._calc_trend(self.df_15m)
        
        if trend_1d == 1 and trend_15m == 1:
            return "Strong Bullish (1D & 15m Aligned)"
        elif trend_1d == 1 and trend_15m == -1:
            return "Bullish Pullback (15m dip in 1D Uptrend - Buy on Dip)"
        elif trend_1d == -1 and trend_15m == -1:
            return "Strong Bearish (1D & 15m Aligned)"
        elif trend_1d == -1 and trend_15m == 1:
            return "Bearish Relief Rally (15m bounce in 1D Downtrend - Sell on Rise)"
        elif trend_1d == 0:
            return "Daily Trend is Sideways/Neutral"
            
        return "Mixed MTF Signals"

    def _calc_correlation_and_rs(self) -> tuple:
        """
        Calculates Pearson Correlation and Relative Strength vs Benchmark.
        Aligns the dataframes by length to prevent index errors.
        """
        if self.df_1d is None or self.df_bench is None or len(self.df_1d) < 20 or len(self.df_bench) < 20:
            return "Benchmark Data Unavailable", "Benchmark Data Unavailable"
            
        # Get minimum length
        min_len = min(len(self.df_1d), len(self.df_bench))
        
        target_close = self.df_1d['Close'].iloc[-min_len:].values
        bench_close = self.df_bench['Close'].iloc[-min_len:].values
        
        # Calculate Correlation over last 20 days
        target_20 = target_close[-20:]
        bench_20 = bench_close[-20:]
        
        # Pearson Correlation
        correlation = np.corrcoef(target_20, bench_20)[0, 1]
        corr_str = f"{correlation:.2f}"
        
        if correlation > 0.7:
            corr_signal = f"Highly Correlated with Market ({corr_str})"
        elif correlation < -0.3:
            corr_signal = f"Inverse Correlation to Market ({corr_str})"
        else:
            corr_signal = f"Low Correlation to Market ({corr_str})"
            
        # Calculate Relative Strength
        target_return = (target_close[-1] / target_close[-20]) - 1
        bench_return = (bench_close[-1] / bench_close[-20]) - 1
        
        alpha = target_return - bench_return
        
        if alpha > 0.05: # 5% outperformance
            rs_signal = "High Relative Strength (Outperforming Benchmark)"
        elif alpha < -0.05:
            rs_signal = "Low Relative Strength (Underperforming Benchmark)"
        else:
            rs_signal = "Neutral Relative Strength (Moving with Benchmark)"
            
        return corr_signal, rs_signal
