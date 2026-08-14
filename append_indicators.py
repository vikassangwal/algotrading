import pandas as pd
import numpy as np

def append_to_file():
    code = """
def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    '''Calculate MACD, MACD Signal, and MACD Histogram.'''
    fast_ema = data.ewm(span=fast_period, adjust=False).mean()
    slow_ema = data.ewm(span=slow_period, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    hist = macd - signal
    return pd.DataFrame({'MACD': macd, 'Signal': signal, 'Histogram': hist})

def calculate_adx(df, period=14):
    '''Calculate Average Directional Index (ADX). Requires high, low, close.'''
    high, low, close = df['high'], df['low'], df['close']
    plus_dm = high.diff()
    minus_dm = (-low.diff())
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Check if +DM > -DM or not
    plus_dm_true = np.where(plus_dm > minus_dm, plus_dm, 0.0)
    minus_dm_true = np.where(minus_dm > plus_dm, minus_dm, 0.0)
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (pd.Series(plus_dm_true).ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm_true).ewm(alpha=1/period, adjust=False).mean() / atr)
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return pd.DataFrame({'+DI': plus_di, '-DI': minus_di, 'ADX': adx})
"""
    with open("app/modules/indicators.py", "a", encoding="utf-8") as f:
        f.write(code)

if __name__ == "__main__":
    append_to_file()
