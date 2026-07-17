import pandas as pd
import numpy as np

def detect_fvg(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detects Fair Value Gaps (FVG).
    A Bullish FVG occurs when the low of the current candle is higher than the high of the candle two periods ago.
    A Bearish FVG occurs when the high of the current candle is lower than the low of the candle two periods ago.
    """
    df = df.copy()
    
    # Bullish FVG
    df['fvg_bullish'] = (df['low'] > df['high'].shift(2)) & (df['close'].shift(1) > df['open'].shift(1))
    
    # Bearish FVG
    df['fvg_bearish'] = (df['high'] < df['low'].shift(2)) & (df['close'].shift(1) < df['open'].shift(1))
    
    return df

def find_swing_highs_lows(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Identifies swing highs and swing lows over a given window.
    """
    df = df.copy()
    df['swing_high'] = df['high'] == df['high'].rolling(window=window*2+1, center=True).max()
    df['swing_low'] = df['low'] == df['low'].rolling(window=window*2+1, center=True).min()
    return df

def detect_liquidity_sweeps(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Detects Liquidity Sweeps.
    A bullish sweep occurs when price dips below a recent swing low but closes above it.
    A bearish sweep occurs when price peaks above a recent swing high but closes below it.
    """
    df = find_swing_highs_lows(df, window)
    
    # Forward fill to keep track of the most recent swing high/low
    df['last_swing_high'] = np.where(df['swing_high'], df['high'], np.nan)
    df['last_swing_high'] = df['last_swing_high'].ffill().shift(1)
    
    df['last_swing_low'] = np.where(df['swing_low'], df['low'], np.nan)
    df['last_swing_low'] = df['last_swing_low'].ffill().shift(1)
    
    # Bearish Sweep: sweeping buy-side liquidity
    df['sweep_bearish'] = (df['high'] > df['last_swing_high']) & (df['close'] < df['last_swing_high'])
    
    # Bullish Sweep: sweeping sell-side liquidity
    df['sweep_bullish'] = (df['low'] < df['last_swing_low']) & (df['close'] > df['last_swing_low'])
    
    return df

def detect_order_blocks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detects Order Blocks (OB).
    Bullish OB: The last bearish candle before a strong bullish move.
    Bearish OB: The last bullish candle before a strong bearish move.
    """
    df = df.copy()
    
    df['is_bearish_candle'] = df['close'] < df['open']
    df['is_bullish_candle'] = df['close'] > df['open']
    
    df['body_size'] = abs(df['close'] - df['open'])
    avg_body = df['body_size'].rolling(window=10).mean()
    
    # Strong move definitions
    strong_bullish_move = df['is_bullish_candle'].shift(-1) & \
                          (df['body_size'].shift(-1) > avg_body.shift(-1) * 1.5) & \
                          (df['close'].shift(-1) > df['high'])
                          
    strong_bearish_move = df['is_bearish_candle'].shift(-1) & \
                          (df['body_size'].shift(-1) > avg_body.shift(-1) * 1.5) & \
                          (df['close'].shift(-1) < df['low'])
                          
    df['ob_bullish'] = df['is_bearish_candle'] & strong_bullish_move
    df['ob_bearish'] = df['is_bullish_candle'] & strong_bearish_move
    
    return df

class SMCEngine:
    """
    Smart Money Concepts Engine.
    Processes OHLC dataframes to identify FVG, Liquidity Sweeps, and Order Blocks.
    """
    def __init__(self, data: pd.DataFrame):
        """
        Expects a pandas DataFrame with 'open', 'high', 'low', 'close' columns.
        """
        self.df = data.copy()
        # Ensure column names are lowercase
        self.df.rename(columns=lambda x: str(x).lower(), inplace=True)
        
    def analyze_all(self, window: int = 5) -> pd.DataFrame:
        """
        Run all SMC detection algorithms.
        """
        df = self.df
        df = detect_fvg(df)
        df = detect_liquidity_sweeps(df, window=window)
        df = detect_order_blocks(df)
        return df
