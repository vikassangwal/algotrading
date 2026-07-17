import pandas as pd
import numpy as np

class UniversalScanner:
    def __init__(self, data: pd.DataFrame):
        """
        Initialize the UniversalScanner with a pandas DataFrame.
        Expected columns include 'Open', 'High', 'Low', 'Close', 'Volume'.
        """
        self.data = data.copy()
        
    def _get_sym_col(self):
        """Helper to find the symbol column if present."""
        if 'symbol' in self.data.columns: return 'symbol'
        if 'Symbol' in self.data.columns: return 'Symbol'
        return None

    def scan_volume_breakouts(self, volume_multiplier: float = 2.0, window: int = 20) -> pd.DataFrame:
        """
        Scan for volume breakouts.
        A breakout is identified when the current volume exceeds the 
        average volume of the past 'window' periods by 'volume_multiplier'.
        """
        if 'Volume' not in self.data.columns:
            raise ValueError("DataFrame must contain a 'Volume' column.")
            
        sym_col = self._get_sym_col()
        
        if sym_col:
            # Group by symbol to ensure rolling window doesn't bleed across symbols
            avg_volume = self.data.groupby(sym_col)['Volume'].transform(lambda x: x.rolling(window=window).mean().shift(1))
        else:
            avg_volume = self.data['Volume'].rolling(window=window).mean().shift(1)
            
        breakout_condition = self.data['Volume'] > (avg_volume * volume_multiplier)
        
        return self.data[breakout_condition].copy()

    def scan_gap_ups_downs(self, threshold_pct: float = 0.5) -> pd.DataFrame:
        """
        Scan for Gap Ups and Gap Downs.
        A gap up is identified if the Open is greater than the previous High by at least 'threshold_pct'.
        A gap down is identified if the Open is lower than the previous Low by at least 'threshold_pct'.
        """
        required_cols = ['Open', 'High', 'Low']
        if not all(col in self.data.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain {required_cols} columns.")
            
        sym_col = self._get_sym_col()
        
        if sym_col:
            prev_high = self.data.groupby(sym_col)['High'].shift(1)
            prev_low = self.data.groupby(sym_col)['Low'].shift(1)
        else:
            prev_high = self.data['High'].shift(1)
            prev_low = self.data['Low'].shift(1)
        
        gap_up_condition = self.data['Open'] > prev_high * (1 + threshold_pct / 100.0)
        gap_down_condition = self.data['Open'] < prev_low * (1 - threshold_pct / 100.0)
        
        df_result = self.data.copy()
        df_result['Gap_Up'] = gap_up_condition
        df_result['Gap_Down'] = gap_down_condition
        
        return df_result[gap_up_condition | gap_down_condition]

    def scan_momentum_shifts(self, window: int = 14) -> pd.DataFrame:
        """
        Scan for Momentum shifts using Rate of Change (ROC).
        A bullish momentum shift occurs when ROC crosses above zero.
        A bearish momentum shift occurs when ROC crosses below zero.
        """
        if 'Close' not in self.data.columns:
            raise ValueError("DataFrame must contain a 'Close' column.")
            
        df_result = self.data.copy()
        sym_col = self._get_sym_col()
        
        if sym_col:
            # Group by symbol to calculate pct_change correctly without bleeding
            df_result['ROC'] = df_result.groupby(sym_col)['Close'].pct_change(periods=window) * 100
            prev_roc = df_result.groupby(sym_col)['ROC'].shift(1)
        else:
            df_result['ROC'] = df_result['Close'].pct_change(periods=window) * 100
            prev_roc = df_result['ROC'].shift(1)
        
        bullish_shift = (prev_roc < 0) & (df_result['ROC'] > 0)
        bearish_shift = (prev_roc > 0) & (df_result['ROC'] < 0)
        
        df_result['Bullish_Shift'] = bullish_shift
        df_result['Bearish_Shift'] = bearish_shift
        
        return df_result[bullish_shift | bearish_shift]
