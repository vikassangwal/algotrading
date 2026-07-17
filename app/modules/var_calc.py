import numpy as np
import pandas as pd
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)

class VaRCalculator:
    """
    Real-time Value at Risk (VaR) calculator.
    """
    
    def __init__(self, confidence_level=0.95, method='historical'):
        """
        :param confidence_level: Confidence level for VaR (e.g., 0.95 or 0.99)
        :param method: 'historical' or 'parametric'
        """
        self.confidence_level = confidence_level
        self.method = method

    def calculate_var(self, returns_series, portfolio_value=1.0):
        """
        Calculates VaR given a series of returns.
        
        :param returns_series: List or pandas/numpy array of historical returns.
        :param portfolio_value: Current value of the portfolio.
        :return: Estimated Value at Risk amount.
        """
        if len(returns_series) == 0:
            logger.warning("Empty returns series. Cannot calculate VaR.")
            return 0.0
            
        returns = np.array(returns_series)
        
        if self.method == 'historical':
            return self._historical_var(returns, portfolio_value)
        elif self.method == 'parametric':
            return self._parametric_var(returns, portfolio_value)
        else:
            raise ValueError(f"Unknown VaR method: {self.method}. Use 'historical' or 'parametric'.")

    def _historical_var(self, returns, portfolio_value):
        """Historical simulation VaR."""
        percentile = (1 - self.confidence_level) * 100
        var_pct = np.percentile(returns, percentile)
        return np.abs(var_pct * portfolio_value)

    def _parametric_var(self, returns, portfolio_value):
        """Variance-Covariance (Parametric) VaR assuming normal distribution."""
        mean = np.mean(returns)
        std_dev = np.std(returns)
        
        # Z-score for the given confidence level
        z_score = norm.ppf(1 - self.confidence_level)
        
        var_pct = mean + z_score * std_dev
        return np.abs(var_pct * portfolio_value)

    def calculate_cvar(self, returns_series, portfolio_value=1.0):
        """
        Calculates Conditional Value at Risk (Expected Shortfall).
        """
        if len(returns_series) == 0:
            return 0.0
            
        returns = np.array(returns_series)
        
        # Calculate raw VaR percentage (negative return)
        percentile = (1 - self.confidence_level) * 100
        var_pct = np.percentile(returns, percentile)
        
        # Elements worse than VaR
        worse_returns = returns[returns <= var_pct]
        
        if len(worse_returns) == 0:
            return np.abs(var_pct * portfolio_value)
            
        cvar_pct = np.mean(worse_returns)
        return np.abs(cvar_pct * portfolio_value)
