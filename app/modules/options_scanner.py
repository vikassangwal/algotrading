import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class OptionsScanner:
    """
    Scanner for Option Chains to identify:
    - High Implied Volatility (IV)
    - Put-Call Ratio (PCR) Divergences
    - Unusual Options Volume
    """
    
    def __init__(self, option_chain_df: pd.DataFrame):
        """
        Initialize the scanner with a DataFrame containing Option Chain data.
        
        Expected DataFrame columns (case-insensitive mapping recommended before passing):
        'symbol', 'strike', 'option_type' (CE/PE), 'expiry', 'iv', 'volume', 'oi', 'spot_price'
        """
        self.df = option_chain_df
        # Basic validation and normalization
        if not self.df.empty:
            self.df.columns = [str(col).lower() for col in self.df.columns]
            
    def scan_high_iv(self, iv_threshold: float = 50.0) -> pd.DataFrame:
        """
        Find options with Implied Volatility above the given threshold.
        """
        if 'iv' not in self.df.columns:
            logger.warning("Column 'iv' missing. Cannot scan for High IV.")
            return pd.DataFrame()
            
        high_iv = self.df[self.df['iv'] >= iv_threshold].copy()
        return high_iv.sort_values(by='iv', ascending=False)
        
    def calculate_pcr(self, group_by: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Calculate Put-Call Ratio for Volume and Open Interest (OI).
        """
        if group_by is None:
            group_by = ['symbol', 'expiry']
            
        req_cols = ['option_type', 'volume', 'oi']
        for col in req_cols:
            if col not in self.df.columns:
                logger.warning(f"Column '{col}' missing. Cannot calculate PCR.")
                return pd.DataFrame()
                
        # Filter for Put and Call data
        puts = self.df[self.df['option_type'].str.upper() == 'PE']
        calls = self.df[self.df['option_type'].str.upper() == 'CE']
        
        valid_groups = [g for g in group_by if g in self.df.columns]
        if not valid_groups:
            valid_groups = ['symbol'] if 'symbol' in self.df.columns else None
            
        if valid_groups:
            puts_grouped = puts.groupby(valid_groups)[['volume', 'oi']].sum()
            calls_grouped = calls.groupby(valid_groups)[['volume', 'oi']].sum()
        else:
            puts_grouped = puts[['volume', 'oi']].sum().to_frame().T
            calls_grouped = calls[['volume', 'oi']].sum().to_frame().T
            
        pcr = pd.DataFrame(index=puts_grouped.index)
        pcr['pcr_volume'] = puts_grouped['volume'] / calls_grouped['volume'].replace(0, np.nan)
        pcr['pcr_oi'] = puts_grouped['oi'] / calls_grouped['oi'].replace(0, np.nan)
        
        return pcr.reset_index() if valid_groups else pcr

    def scan_pcr_divergence(self, overbought_level: float = 1.6, oversold_level: float = 0.6) -> pd.DataFrame:
        """
        Identify extreme PCR levels which may indicate market divergences or reversals.
        - High PCR (> 1.6) typically indicates bearish sentiment (overbought puts).
        - Low PCR (< 0.6) typically indicates bullish sentiment (overbought calls).
        """
        pcr_df = self.calculate_pcr()
        if pcr_df.empty:
            return pcr_df
            
        divergence = pcr_df[
            (pcr_df['pcr_oi'] >= overbought_level) | 
            (pcr_df['pcr_oi'] <= oversold_level)
        ].copy()
        
        if not divergence.empty:
            divergence['signal'] = np.where(
                divergence['pcr_oi'] >= overbought_level, 
                'Overbought Puts (Potential Reversal / Bearish Bias)', 
                'Overbought Calls (Potential Reversal / Bullish Bias)'
            )
            
        return divergence

    def scan_unusual_volume(self, vol_oi_ratio_threshold: float = 3.0, min_volume: int = 500) -> pd.DataFrame:
        """
        Find options where trading volume is unusually high compared to the existing Open Interest.
        This often indicates smart money or large institutional positioning.
        """
        req_cols = ['volume', 'oi']
        for col in req_cols:
            if col not in self.df.columns:
                logger.warning(f"Column '{col}' missing. Cannot scan for Unusual Volume.")
                return pd.DataFrame()
                
        # Condition: Volume > Minimum Volume AND Volume > (OI * Threshold)
        unusual = self.df[
            (self.df['volume'] >= min_volume) & 
            (self.df['volume'] >= (self.df['oi'] * vol_oi_ratio_threshold))
        ].copy()
        
        if not unusual.empty:
            unusual['vol_oi_ratio'] = unusual['volume'] / unusual['oi'].replace(0, 1)
            unusual = unusual.sort_values(by='vol_oi_ratio', ascending=False)
            
        return unusual

    def run_full_scan(self) -> Dict[str, pd.DataFrame]:
        """
        Executes all scans and returns a dictionary of results.
        """
        return {
            'high_iv': self.scan_high_iv(),
            'pcr_divergence': self.scan_pcr_divergence(),
            'unusual_volume': self.scan_unusual_volume()
        }

if __name__ == "__main__":
    # Example usage:
    # dummy_data = pd.DataFrame({
    #     'symbol': ['AAPL', 'AAPL'], 
    #     'option_type': ['CE', 'PE'], 
    #     'volume': [10000, 2000], 
    #     'oi': [1000, 500],
    #     'iv': [25.5, 60.2]
    # })
    # scanner = OptionsScanner(dummy_data)
    # results = scanner.run_full_scan()
    # print(results)
    pass
