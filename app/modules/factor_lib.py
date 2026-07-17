import pandas as pd
import numpy as np

class MomentumFactors:
    """
    Library of Momentum Factors.
    """
    @staticmethod
    def calculate_price_momentum(prices: pd.Series, periods: int = 252) -> pd.Series:
        """
        Calculate simple price momentum over a given number of periods.
        """
        return prices.pct_change(periods)

    @staticmethod
    def calculate_moving_average_crossover(prices: pd.Series, short_window: int = 50, long_window: int = 200) -> pd.Series:
        """
        Calculate Moving Average crossover signal (Short MA / Long MA - 1).
        """
        short_ma = prices.rolling(window=short_window).mean()
        long_ma = prices.rolling(window=long_window).mean()
        return (short_ma / long_ma) - 1

class ValueFactors:
    """
    Library of Value Factors.
    """
    @staticmethod
    def calculate_book_to_market(book_value: pd.Series, market_cap: pd.Series) -> pd.Series:
        """
        Calculate Book to Market ratio.
        """
        return book_value / market_cap

    @staticmethod
    def calculate_earnings_yield(earnings_per_share: pd.Series, price: pd.Series) -> pd.Series:
        """
        Calculate Earnings Yield (EPS / Price).
        """
        return earnings_per_share / price
        
    @staticmethod
    def calculate_dividend_yield(dividends_per_share: pd.Series, price: pd.Series) -> pd.Series:
        """
        Calculate Dividend Yield.
        """
        return dividends_per_share / price

class QualityFactors:
    """
    Library of Quality Factors.
    """
    @staticmethod
    def calculate_return_on_equity(net_income: pd.Series, shareholder_equity: pd.Series) -> pd.Series:
        """
        Calculate Return on Equity (ROE).
        """
        return net_income / shareholder_equity

    @staticmethod
    def calculate_debt_to_equity(total_debt: pd.Series, shareholder_equity: pd.Series) -> pd.Series:
        """
        Calculate Debt to Equity ratio. Lower is generally better for quality.
        """
        return total_debt / shareholder_equity

    @staticmethod
    def calculate_gross_profitability(gross_profit: pd.Series, total_assets: pd.Series) -> pd.Series:
        """
        Calculate Gross Profitability (Gross Profit / Total Assets).
        """
        return gross_profit / total_assets
