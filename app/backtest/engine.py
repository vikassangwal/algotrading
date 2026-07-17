import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class HistoricalBacktester:
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital

    def _calculate_sma(self, data, window):
        return data['Close'].rolling(window=window).mean()
        
    def _calculate_rsi(self, data, window=14):
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, data, fast=12, slow=26, signal=9):
        exp1 = data['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = data['Close'].ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line

    def run_backtest(self, symbol: str, years: int = 5):
        """Runs a vectorized backtest simulating the AI logic over the historical period."""
        logger.info(f"Running {years}-year backtest for {symbol}")
        
        # 1. Fetch Historical Data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        try:
            ticker = yf.Ticker(symbol)
            # Need to get data slightly before start_date to calculate indicators
            fetch_start = start_date - timedelta(days=200)
            df = ticker.history(start=fetch_start, end=end_date)
            
            if df.empty:
                return {"status": "error", "message": "No data found for symbol"}
                
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

        # 2. Compute AI Signals (Simulated Vectorized Elco Brain)
        df['SMA_50'] = self._calculate_sma(df, 50)
        df['SMA_200'] = self._calculate_sma(df, 200)
        df['RSI'] = self._calculate_rsi(df, 14)
        df['MACD'], df['MACD_Signal'] = self._calculate_macd(df)
        
        # Trim the initial padding used for indicator warmup
        df = df[df.index >= pd.to_datetime(start_date).tz_localize(df.index.tz)]
        
        if df.empty:
            return {"status": "error", "message": "Not enough data after trimming warmup period"}

        # Generate Signals:
        # 1 = Buy, 0 = Hold, -1 = Sell
        # Rule: Buy when MACD > Signal AND Price > SMA_200 AND RSI < 70
        # Sell when MACD < Signal OR RSI > 80 OR Price < SMA_200
        
        signals = np.zeros(len(df))
        position = 0 # 0 = flat, 1 = long
        
        buy_prices = []
        sell_prices = []
        
        for i in range(1, len(df)):
            prev_macd = df['MACD'].iloc[i-1]
            prev_signal = df['MACD_Signal'].iloc[i-1]
            curr_macd = df['MACD'].iloc[i]
            curr_signal = df['MACD_Signal'].iloc[i]
            
            price = df['Close'].iloc[i]
            sma200 = df['SMA_200'].iloc[i]
            rsi = df['RSI'].iloc[i]
            
            # Entry Logic
            if position == 0:
                if (prev_macd < prev_signal and curr_macd > curr_signal) and price > sma200 and rsi < 70:
                    signals[i] = 1
                    position = 1
                    buy_prices.append(price)
            
            # Exit Logic
            elif position == 1:
                if (prev_macd > prev_signal and curr_macd < curr_signal) or rsi > 80 or price < sma200:
                    signals[i] = -1
                    position = 0
                    sell_prices.append(price)
                    
        df['Signal'] = signals
        df['Position'] = df['Signal'].cumsum().clip(0, 1) # Ensure position is only 0 or 1
        
        # Shift position by 1 day to calculate returns (we trade at the next day's open or close)
        # Assuming we trade at the close of the signal day
        df['Strategy_Returns'] = df['Position'].shift(1) * df['Close'].pct_change()
        df['Strategy_Returns'] = df['Strategy_Returns'].fillna(0)
        
        # Calculate Equity Curve
        df['Equity'] = self.initial_capital * (1 + df['Strategy_Returns']).cumprod()
        
        # 3. Calculate Performance Metrics
        total_return = (df['Equity'].iloc[-1] / self.initial_capital) - 1
        annualized_return = (1 + total_return) ** (252 / len(df)) - 1
        
        daily_volatility = df['Strategy_Returns'].std()
        sharpe_ratio = (df['Strategy_Returns'].mean() / daily_volatility) * np.sqrt(252) if daily_volatility > 0 else 0
        
        roll_max = df['Equity'].cummax()
        drawdown = df['Equity'] / roll_max - 1.0
        max_drawdown = drawdown.min()
        
        # Calculate Win Rate
        trades = []
        if len(buy_prices) > 0:
            # Match buys and sells
            for i in range(min(len(buy_prices), len(sell_prices))):
                trade_return = (sell_prices[i] - buy_prices[i]) / buy_prices[i]
                trades.append(trade_return)
                
            # If currently holding
            if len(buy_prices) > len(sell_prices):
                current_price = df['Close'].iloc[-1]
                trade_return = (current_price - buy_prices[-1]) / buy_prices[-1]
                trades.append(trade_return)
                
        winning_trades = [t for t in trades if t > 0]
        win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0
        
        # Format Equity Curve for UI
        equity_curve = []
        for index, row in df.iterrows():
            equity_curve.append({
                "date": index.strftime('%Y-%m-%d'),
                "value": round(row['Equity'], 2)
            })

        return {
            "status": "success",
            "metrics": {
                "total_return": round(total_return * 100, 2),
                "annualized_cagr": round(annualized_return * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "max_drawdown": round(max_drawdown * 100, 2),
                "win_rate": round(win_rate * 100, 2),
                "total_trades": len(trades),
                "final_capital": round(df['Equity'].iloc[-1], 2)
            },
            "equity_curve": equity_curve
        }
