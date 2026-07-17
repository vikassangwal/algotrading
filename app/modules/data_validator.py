"""
Data Validation Engine for Financial Data
Provides tools for cleaning and verifying Pandas OHLC or tick data.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class DataValidationEngine:
    def __init__(self, spike_threshold: float = 0.05):
        """
        Initialize the DataValidationEngine.
        
        :param spike_threshold: The percentage threshold to define an unrealistic price spike.
                                Default is 0.05 (5%).
        """
        self.spike_threshold = spike_threshold

    def filter_bad_ticks(self, df: pd.DataFrame, price_col: str = 'close') -> pd.DataFrame:
        """
        Filter out unrealistic price spikes (Bad Ticks).
        
        :param df: Input DataFrame with price data.
        :param price_col: The column containing price data (default 'close').
        :return: Cleaned DataFrame.
        """
        if df.empty or price_col not in df.columns:
            return df.copy()

        df_clean = df.copy()
        
        # We calculate the absolute percentage change compared to the previous tick/row
        pct_change = df_clean[price_col].pct_change().abs()
        
        # A spike is when the change exceeds our threshold
        is_spike = pct_change > self.spike_threshold
        
        if is_spike.any():
            num_spikes = is_spike.sum()
            logger.warning(f"Filtering {num_spikes} bad ticks based on threshold {self.spike_threshold}")
            df_clean = df_clean[~is_spike]
            
        return df_clean

    def check_duplicates(self, df: pd.DataFrame, datetime_col: str = None) -> pd.DataFrame:
        """
        Check for and remove duplicate rows based on datetime column or index.
        
        :param df: Input DataFrame.
        :param datetime_col: The name of the datetime column. If None, uses the DataFrame index.
        :return: DataFrame without duplicates.
        """
        if df.empty:
            return df.copy()
            
        df_clean = df.copy()
        
        if datetime_col is not None and datetime_col in df_clean.columns:
            duplicates = df_clean.duplicated(subset=[datetime_col], keep='first')
        else:
            duplicates = df_clean.index.duplicated(keep='first')
            
        if duplicates.any():
            num_dupes = duplicates.sum()
            logger.warning(f"Removed {num_dupes} duplicate timestamps.")
            df_clean = df_clean[~duplicates]
            
        return df_clean

    def validate_missing_timestamps(self, df: pd.DataFrame, datetime_col: str = None, freq: str = '1min') -> list:
        """
        Validates missing timestamps by comparing actual timestamps against an expected frequency.
        
        :param df: Input DataFrame.
        :param datetime_col: The name of the datetime column. If None, uses the DataFrame index.
        :param freq: Expected frequency (e.g., '1min', '1H', '1D').
        :return: A list of missing pandas Timestamps.
        """
        if df.empty:
            return []
            
        if datetime_col is not None and datetime_col in df.columns:
            timestamps = pd.to_datetime(df[datetime_col])
        else:
            timestamps = pd.to_datetime(df.index)
            
        if not isinstance(timestamps, pd.DatetimeIndex):
            timestamps = pd.DatetimeIndex(timestamps)
            
        timestamps = timestamps.dropna().sort_values()
        
        if len(timestamps) < 2:
            return []
            
        expected_range = pd.date_range(start=timestamps.min(), end=timestamps.max(), freq=freq)
        missing_timestamps = expected_range.difference(timestamps)
        
        if len(missing_timestamps) > 0:
            logger.warning(f"Found {len(missing_timestamps)} missing timestamps for frequency {freq}.")
            
        return missing_timestamps.tolist()

    def process_data(self, df: pd.DataFrame, price_col: str = 'close', datetime_col: str = None, freq: str = '1min') -> pd.DataFrame:
        """
        Runs the complete validation suite: removes duplicates, filters bad ticks, and logs missing timestamps.
        
        :param df: Input DataFrame.
        :param price_col: Column for price spike checks.
        :param datetime_col: Datetime column.
        :param freq: Expected frequency for missing timestamps.
        :return: Processed DataFrame.
        """
        logger.info("Starting Data Validation Engine")
        
        df = self.check_duplicates(df, datetime_col=datetime_col)
        df = self.filter_bad_ticks(df, price_col=price_col)
        self.validate_missing_timestamps(df, datetime_col=datetime_col, freq=freq)
        
        logger.info("Data Validation complete")
        return df
