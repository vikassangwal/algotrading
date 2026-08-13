import logging
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from app.backtester import EventDrivenBacktester

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

print("Starting Real Data Backtest for last 2 years...")
bt = EventDrivenBacktester(symbols=["RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK"], data_source="real", years=2)
bt.run()
