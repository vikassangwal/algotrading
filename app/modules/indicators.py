import pandas as pd
import numpy as np

def calculate_ema(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    """
    return data.ewm(span=period, adjust=False).mean()

def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    # Replace infinite values (when loss is 0) with 100
    rsi = rsi.replace([np.inf, -np.inf], 100)
    return rsi

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP).
    Requires 'high', 'low', 'close', and 'volume' columns in DataFrame.
    """
    if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
        raise ValueError("DataFrame must contain 'high', 'low', 'close', and 'volume' columns")
    
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

def calculate_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Calculate Supertrend indicator.
    Requires 'high', 'low', and 'close' columns in DataFrame.
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # ATR calculation
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    hl2 = (high + low) / 2
    
    # Basic upper and lower bands
    final_upperband = hl2 + (multiplier * atr)
    final_lowerband = hl2 - (multiplier * atr)
    
    supertrend = [True] * len(df)
    
    for i in range(1, len(df.index)):
        curr, prev = i, i-1
        
        # Upper band
        if close.iloc[prev] > final_upperband.iloc[prev]:
            final_upperband.iloc[curr] = min(final_upperband.iloc[curr], final_upperband.iloc[prev])
            
        # Lower band
        if close.iloc[prev] < final_lowerband.iloc[prev]:
            final_lowerband.iloc[curr] = max(final_lowerband.iloc[curr], final_lowerband.iloc[prev])
            
        # Trend
        if close.iloc[curr] <= final_upperband.iloc[curr]:
            supertrend[curr] = True
        else:
            supertrend[curr] = False
            
    # simplified return
    st_df = pd.DataFrame(index=df.index)
    st_df['Supertrend'] = np.where(supertrend, final_upperband, final_lowerband)
    st_df['Direction'] = np.where(supertrend, -1, 1) # -1 for downtrend, 1 for uptrend
    
    return st_df

def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    Calculate Bollinger Bands.
    """
    sma = data.rolling(window=period).mean()
    rolling_std = data.rolling(window=period).std()
    
    upper_band = sma + (rolling_std * std_dev)
    lower_band = sma - (rolling_std * std_dev)
    
    return pd.DataFrame({
        'Middle_Band': sma,
        'Upper_Band': upper_band,
        'Lower_Band': lower_band
    })

def calculate_ichimoku(df: pd.DataFrame, tenkan_period: int = 9, kijun_period: int = 26, senkou_period: int = 52, displacement: int = 26) -> pd.DataFrame:
    """
    Calculate Ichimoku Cloud.
    Requires 'high', 'low', and 'close' columns in DataFrame.
    """
    high = df['high']
    low = df['low']
    
    # Tenkan-sen (Conversion Line)
    tenkan_max = high.rolling(window=tenkan_period).max()
    tenkan_min = low.rolling(window=tenkan_period).min()
    tenkan_sen = (tenkan_max + tenkan_min) / 2
    
    # Kijun-sen (Base Line)
    kijun_max = high.rolling(window=kijun_period).max()
    kijun_min = low.rolling(window=kijun_period).min()
    kijun_sen = (kijun_max + kijun_min) / 2
    
    # Senkou Span A (Leading Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)
    
    # Senkou Span B (Leading Span B)
    senkou_max = high.rolling(window=senkou_period).max()
    senkou_min = low.rolling(window=senkou_period).min()
    senkou_span_b = ((senkou_max + senkou_min) / 2).shift(displacement)
    
    # Chikou Span (Lagging Span)
    chikou_span = df['close'].shift(-displacement)
    
    return pd.DataFrame({
        'Tenkan_Sen': tenkan_sen,
        'Kijun_Sen': kijun_sen,
        'Senkou_Span_A': senkou_span_a,
        'Senkou_Span_B': senkou_span_b,
        'Chikou_Span': chikou_span
    })

def calculate_stochastic_oscillator(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """
    Calculate Stochastic Oscillator (%K and %D).
    Requires 'high', 'low', and 'close' columns in DataFrame.
    """
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()

    # Guard against a flat window (high == low) which would divide by zero.
    denom = (high_max - low_min).replace(0, np.nan)
    k_percent = 100 * ((df['close'] - low_min) / denom)
    k_percent = k_percent.fillna(50.0)  # neutral when range is degenerate
    d_percent = k_percent.rolling(window=d_period).mean()
    
    return pd.DataFrame({
        '%K': k_percent,
        '%D': d_percent
    })

def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Money Flow Index (MFI).
    Requires 'high', 'low', 'close', and 'volume' columns in DataFrame.
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    raw_money_flow = typical_price * df['volume']
    
    positive_flow = np.where(typical_price > typical_price.shift(1), raw_money_flow, 0.0)
    negative_flow = np.where(typical_price < typical_price.shift(1), raw_money_flow, 0.0)
    
    pos_flow_series = pd.Series(positive_flow, index=df.index)
    neg_flow_series = pd.Series(negative_flow, index=df.index)
    
    pos_flow_sum = pos_flow_series.rolling(window=period).sum()
    neg_flow_sum = neg_flow_series.rolling(window=period).sum()
    
    # Avoid division by zero
    money_ratio = pos_flow_sum / neg_flow_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + money_ratio))
    mfi = mfi.fillna(100) # If neg_flow_sum is 0, MFI is 100
    
    return mfi

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV).
    Requires 'close' and 'volume' columns in DataFrame.
    """
    obv_change = np.where(df['close'] > df['close'].shift(1), df['volume'],
                 np.where(df['close'] < df['close'].shift(1), -df['volume'], 0))
    obv = pd.Series(obv_change, index=df.index).cumsum()
    return obv

def calculate_pivot_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate standard Pivot Points (Support and Resistance levels).
    Requires 'high', 'low', and 'close' columns in DataFrame.
    Calculations use the previous period's data.
    """
    prev_high = df['high'].shift(1)
    prev_low = df['low'].shift(1)
    prev_close = df['close'].shift(1)
    
    pivot = (prev_high + prev_low + prev_close) / 3
    r1 = (2 * pivot) - prev_low
    s1 = (2 * pivot) - prev_high
    r2 = pivot + (prev_high - prev_low)
    s2 = pivot - (prev_high - prev_low)
    r3 = prev_high + 2 * (pivot - prev_low)
    s3 = prev_low - 2 * (prev_high - pivot)
    
    return pd.DataFrame({
        'Pivot': pivot,
        'R1': r1,
        'S1': s1,
        'R2': r2,
        'S2': s2,
        'R3': r3,
        'S3': s3
    })

def calculate_fibonacci_retracements(df: pd.DataFrame, period: int = 100) -> pd.DataFrame:
    """
    Calculate Fibonacci Retracement levels over a rolling period.
    Requires 'high' and 'low' columns in DataFrame.
    """
    roll_max = df['high'].rolling(window=period).max()
    roll_min = df['low'].rolling(window=period).min()
    diff = roll_max - roll_min
    
    return pd.DataFrame({
        'Level_0': roll_max,
        'Level_23_6': roll_max - 0.236 * diff,
        'Level_38_2': roll_max - 0.382 * diff,
        'Level_50_0': roll_max - 0.5 * diff,
        'Level_61_8': roll_max - 0.618 * diff,
        'Level_78_6': roll_max - 0.786 * diff,
        'Level_100': roll_min
    })
