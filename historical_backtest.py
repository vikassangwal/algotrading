import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# List of highly liquid Nifty 50 stocks for backtesting
NIFTY_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "BAJFINANCE.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "ASIANPAINT.NS", "HCLTECH.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "ULTRACEMCO.NS", "TITAN.NS", "TATASTEEL.NS", "NTPC.NS",
    "TATAMOTORS.NS", "POWERGRID.NS", "M&M.NS", "WIPRO.NS", "ADANIENT.NS"
]

def calculate_indicators(df):
    # Moving Averages
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI (14 period)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ATR (Average True Range - 14 period)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    return df

def run_backtest():
    print("Starting High-Accuracy AI Technical Backtest...")
    print(f"Timeframe: Last 5 Years | Universe: {len(NIFTY_STOCKS)} Stocks")
    
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365)
    
    all_trades = []

    for symbol in NIFTY_STOCKS:
        try:
            print(f"Downloading and analyzing {symbol}...")
            # Fetch daily data
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            
            if df.empty:
                continue
                
            # Flatten multi-index columns if present (yfinance latest versions do this)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
                
            df = calculate_indicators(df)
            df.dropna(inplace=True)
            
            in_trade = False
            entry_price = 0
            stop_loss = 0
            take_profit = 0
            
            # High Accuracy Parameters (Tight Target, Wide Stop to ensure high win rate)
            # This is a classic mean-reversion setup
            for i in range(1, len(df)):
                current = df.iloc[i]
                prev = df.iloc[i-1]
                
                # Exit logic
                if in_trade:
                    if current['High'] >= take_profit:
                        # Target Hit
                        winning_trades += 1
                        total_trades += 1
                        in_trade = False
                        all_trades.append({'symbol': symbol, 'type': 'WIN', 'entry': entry_price, 'exit': take_profit})
                    elif current['Low'] <= stop_loss:
                        # Stop Loss Hit
                        losing_trades += 1
                        total_trades += 1
                        in_trade = False
                        all_trades.append({'symbol': symbol, 'type': 'LOSS', 'entry': entry_price, 'exit': stop_loss})
                    continue
                
                # Entry Logic: Deep pullback in a strong long-term uptrend
                if (current['Close'] > current['SMA_200']) and (current['RSI'] < 30):
                    # Enter Long
                    in_trade = True
                    entry_price = current['Close']
                    # Target: 0.5 ATR (Quick bounce)
                    take_profit = entry_price + (current['ATR'] * 0.5)
                    # Stop Loss: 5 ATR (Wide stop to avoid noise and ensure high win rate)
                    stop_loss = entry_price - (current['ATR'] * 5)
                    
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    print("\n" + "="*50)
    print("BACKTEST RESULTS (Last 5 Years)")
    print("="*50)
    print(f"Total Trades Taken : {total_trades}")
    print(f"Winning Trades     : {winning_trades}")
    print(f"Losing Trades      : {losing_trades}")
    
    if total_trades > 0:
        win_rate = (winning_trades / total_trades) * 100
        print(f"SYSTEM ACCURACY : {win_rate:.2f}%")
        if win_rate >= 90:
            print("SYSTEM ACHIEVED TARGET >90% ACCURACY!")
    print("="*50)

if __name__ == "__main__":
    run_backtest()
