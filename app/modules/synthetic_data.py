import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

def generate_random_walk_data(
    start_date: str = '2023-01-01',
    end_date: str = '2023-12-31',
    freq: str = '1D',
    initial_price: float = 100.0,
    volatility: float = 0.02,
    drift: float = 0.001
) -> pd.DataFrame:
    """
    Generates synthetic OHLCV financial data using a random walk with drift (Geometric Brownian Motion).
    Useful for testing trend-following or generic strategies.
    
    Args:
        start_date: Start date for the data.
        end_date: End date for the data.
        freq: Frequency of the data (e.g., '1D', '1H', '1min').
        initial_price: Starting price.
        volatility: Daily standard deviation of returns.
        drift: Daily expected return.
        
    Returns:
        pd.DataFrame containing OHLCV data.
    """
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    n = len(dates)
    
    # Generate random returns
    returns = np.random.normal(loc=drift, scale=volatility, size=n)
    
    # Calculate closing prices using Geometric Brownian Motion
    close_prices = initial_price * np.exp(np.cumsum(returns))
    
    # Generate High, Low, Open based on Close with some added noise
    high_prices = close_prices * (1 + np.abs(np.random.normal(0, volatility/2, n)))
    low_prices = close_prices * (1 - np.abs(np.random.normal(0, volatility/2, n)))
    open_prices = close_prices * (1 + np.random.normal(0, volatility/3, n))
    
    # Ensure High is highest and Low is lowest
    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
    low_prices = np.minimum(low_prices, np.minimum(open_prices, close_prices))
    
    # Generate realistic-looking Volume (log-normal distribution)
    volume = np.random.lognormal(mean=10, sigma=1, size=n).astype(int)
    
    df = pd.DataFrame({
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volume
    }, index=dates)
    
    df.index.name = 'Date'
    return df

def generate_mean_reverting_data(
    start_date: str = '2023-01-01',
    end_date: str = '2023-12-31',
    freq: str = '1D',
    initial_price: float = 100.0,
    mean_price: float = 100.0,
    reversion_speed: float = 0.1,
    volatility: float = 0.02
) -> pd.DataFrame:
    """
    Generates synthetic OHLCV data using an Ornstein-Uhlenbeck (mean-reverting) process.
    Useful for testing mean-reversion strategies.
    
    Args:
        start_date: Start date for the data.
        end_date: End date for the data.
        freq: Frequency of the data.
        initial_price: Starting price.
        mean_price: The long-term mean price the series reverts to.
        reversion_speed: How quickly the price reverts to the mean (0 to 1).
        volatility: Standard deviation of the noise.
        
    Returns:
        pd.DataFrame containing OHLCV data.
    """
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    n = len(dates)
    
    prices = np.zeros(n)
    prices[0] = initial_price
    
    for i in range(1, n):
        # dX_t = theta * (mu - X_t) * dt + sigma * dW_t (Ornstein-Uhlenbeck process step)
        dt = 1 # Assuming uniform discrete steps
        dw = np.random.normal(0, 1)
        dp = reversion_speed * (mean_price - prices[i-1]) * dt + volatility * prices[i-1] * dw
        prices[i] = prices[i-1] + dp
        
        # Ensure price doesn't drop below zero
        if prices[i] <= 0:
            prices[i] = 0.01 
            
    close_prices = prices
    
    # Generate High, Low, Open relative to Close
    high_prices = close_prices * (1 + np.abs(np.random.normal(0, volatility/2, n)))
    low_prices = close_prices * (1 - np.abs(np.random.normal(0, volatility/2, n)))
    open_prices = close_prices * (1 + np.random.normal(0, volatility/3, n))
    
    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
    low_prices = np.minimum(low_prices, np.minimum(open_prices, close_prices))
    
    volume = np.random.lognormal(mean=10, sigma=1, size=n).astype(int)
    
    df = pd.DataFrame({
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volume
    }, index=dates)
    
    df.index.name = 'Date'
    return df

def generate_sinusoidal_data(
    start_date: str = '2023-01-01',
    end_date: str = '2023-12-31',
    freq: str = '1H',
    initial_price: float = 100.0,
    amplitude: float = 10.0,
    period_length: int = 24,
    noise_level: float = 1.0
) -> pd.DataFrame:
    """
    Generates synthetic OHLCV data with strong seasonality (sinusoidal pattern).
    Useful for testing strategies that exploit cyclical patterns (e.g., intraday seasonality).
    
    Args:
        start_date: Start date for the data.
        end_date: End date for the data.
        freq: Frequency of the data (e.g., '1H').
        initial_price: Baseline starting price.
        amplitude: The peak deviation of the sine wave from the baseline.
        period_length: Number of data points to complete one full cycle.
        noise_level: Amount of random noise added to the signal.
        
    Returns:
        pd.DataFrame containing OHLCV data.
    """
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    n = len(dates)
    
    t = np.arange(n)
    # Sine wave signal
    base_signal = initial_price + amplitude * np.sin(2 * np.pi * t / period_length)
    # Add noise
    noise = np.random.normal(0, noise_level, n)
    
    close_prices = base_signal + noise
    
    # Ensure no negative prices
    close_prices = np.maximum(close_prices, 0.01)
    
    # Generate Open, High, Low
    high_prices = close_prices + np.abs(np.random.normal(0, noise_level/2, n))
    low_prices = close_prices - np.abs(np.random.normal(0, noise_level/2, n))
    open_prices = close_prices + np.random.normal(0, noise_level/3, n)
    
    # Ensure OHLC bounds
    low_prices = np.maximum(low_prices, 0.01)
    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
    low_prices = np.minimum(low_prices, np.minimum(open_prices, close_prices))
    
    volume = np.random.lognormal(mean=10, sigma=1, size=n).astype(int)
    
    df = pd.DataFrame({
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volume
    }, index=dates)
    
    df.index.name = 'Date'
    return df

if __name__ == "__main__":
    # Example usage
    print("Generating Random Walk Data...")
    rw_df = generate_random_walk_data(start_date="2023-01-01", end_date="2023-01-10")
    print(rw_df.head())
    
    print("\\nGenerating Mean Reverting Data...")
    mr_df = generate_mean_reverting_data(start_date="2023-01-01", end_date="2023-01-10")
    print(mr_df.head())
    
    print("\\nGenerating Seasonal/Sinusoidal Data...")
    seasonal_df = generate_sinusoidal_data(start_date="2023-01-01", end_date="2023-01-03", freq='1H', period_length=24)
    print(seasonal_df.head())
