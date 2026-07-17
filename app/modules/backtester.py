import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, strategy, data):
        self.strategy = strategy
        self.data = data
        
    def walk_forward_optimization(self, train_window, test_window, step_size):
        logger.info(f"Starting Walk-Forward Optimization: Train={train_window}, Test={test_window}, Step={step_size}")
        
        total_len = len(self.data)
        results = []
        
        for start_idx in range(0, total_len - train_window - test_window + 1, step_size):
            train_start = start_idx
            train_end = start_idx + train_window
            test_start = train_end
            test_end = test_start + test_window
            
            train_data = self.data.iloc[train_start:train_end]
            test_data = self.data.iloc[test_start:test_end]
            
            metrics = {
                'window_start': test_data.index[0] if not test_data.empty else None,
                'window_end': test_data.index[-1] if not test_data.empty else None,
                'profit': 0.0,
                'sharpe_ratio': 0.0
            }
            
            try:
                if hasattr(self.strategy, 'train') and hasattr(self.strategy, 'test'):
                    self.strategy.train(train_data)
                    strategy_metrics = self.strategy.test(test_data)
                    if isinstance(strategy_metrics, dict):
                        metrics.update(strategy_metrics)
            except Exception as e:
                logger.error(f"Strategy evaluation failed: {e}")
                
            results.append(metrics)
            
        return results

    def monte_carlo_simulation(self, initial_capital, num_simulations=1000):
        logger.info(f"Running Monte Carlo Simulation with {num_simulations} iterations.")
        
        final_capitals = []
        
        # We need historical returns to bootstrap from, rather than random normal distribution.
        if 'returns' in self.data.columns:
            historical_returns = self.data['returns'].dropna().values
        elif 'close' in self.data.columns:
            historical_returns = self.data['close'].pct_change().dropna().values
        else:
            historical_returns = np.array([0.001]*252) # safe fallback
            
        if len(historical_returns) == 0:
            historical_returns = np.array([0.001]*252)
            
        for _ in range(num_simulations):
            # Bootstrap sampling from actual historical returns
            simulated_returns = np.random.choice(historical_returns, size=252, replace=True)
            simulated_equity_curve = initial_capital * np.cumprod(1 + simulated_returns)
            final_capitals.append(simulated_equity_curve[-1])
            
        stats = {
            'mean_final_capital': np.mean(final_capitals),
            'median_final_capital': np.median(final_capitals),
            '5th_percentile': np.percentile(final_capitals, 5),
            '95th_percentile': np.percentile(final_capitals, 95)
        }
        
        return stats
