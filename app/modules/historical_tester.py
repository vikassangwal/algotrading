import pandas as pd
import numpy as np
import concurrent.futures
from typing import Callable, Dict, List, Any

class VectorBacktester:
    def __init__(self, data: pd.DataFrame, signal_func: Callable, params_list: List[Dict[str, Any]]):
        self.data = data
        self.signal_func = signal_func
        self.params_list = params_list
        self.results = []

    def run_single_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        df = self.data.copy()
        try:
            df['signal'] = self.signal_func(df, **params)
        except Exception as e:
            return {'params': params, 'error': str(e)}
        
        df['position'] = df['signal'].shift(1).fillna(0)
        
        if 'close' in df.columns:
            df['returns'] = df['close'].pct_change()
        else:
            price_col = df.columns[0]
            df['returns'] = df[price_col].pct_change()
            
        df['strategy_returns'] = df['position'] * df['returns']
        df['cum_returns'] = (1 + df['strategy_returns']).cumprod()
        
        total_return = df['cum_returns'].iloc[-1] - 1 if len(df) > 0 else 0
        annualized_return = (1 + total_return) ** (252 / len(df)) - 1 if len(df) > 0 else 0
        
        daily_vol = df['strategy_returns'].std()
        sharpe_ratio = (df['strategy_returns'].mean() / daily_vol * np.sqrt(252)) if daily_vol > 0 else 0
        
        roll_max = df['cum_returns'].cummax()
        drawdown = df['cum_returns'] / roll_max - 1.0
        max_drawdown = drawdown.min()
        
        return {
            'params': params,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown
        }

    def run_parallel_backtests(self, max_workers: int = None) -> pd.DataFrame:
        results = []
        # Changed from ProcessPoolExecutor to ThreadPoolExecutor to prevent laptop freezing/crashing
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.run_single_backtest, params) for params in self.params_list]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    print(f"Backtest failed with exception: {e}")
                    
        self.results = results
        results_df = pd.DataFrame(self.results)
        return results_df

def sample_moving_average_crossover(df: pd.DataFrame, short_window: int, long_window: int) -> pd.Series:
    short_mavg = df['close'].rolling(window=short_window, min_periods=1).mean()
    long_mavg = df['close'].rolling(window=long_window, min_periods=1).mean()
    
    signals = pd.Series(0, index=df.index)
    signals[short_mavg > long_mavg] = 1
    signals[short_mavg < long_mavg] = -1
    return signals

if __name__ == "__main__":
    dates = pd.date_range("2020-01-01", periods=1000)
    data = pd.DataFrame({
        'close': np.random.normal(0, 1, 1000).cumsum() + 100
    }, index=dates)
    
    params_list = [{'short_window': sw, 'long_window': lw} 
                   for sw in range(5, 50, 5) 
                   for lw in range(50, 200, 10) if sw < lw]
                   
    print(f"Generated {len(params_list)} parameter combinations for backtesting.")
    
    tester = VectorBacktester(data, sample_moving_average_crossover, params_list)
    results_df = tester.run_parallel_backtests(max_workers=None) 
    
    print("\nTop 5 Results sorted by Sharpe Ratio:")
    if 'error' not in results_df.columns:
        print(results_df.sort_values(by='sharpe_ratio', ascending=False).head())
    else:
        print(results_df)
