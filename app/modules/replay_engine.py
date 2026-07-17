import random
import datetime

class ReplayEngine:
    """
    Engine to fetch or simulate high-frequency intraday data 
    overlaid with executed trades for the Replay Dashboard.
    """
    
    def get_replay_data(self, symbol: str, date: str):
        """
        Returns a timeline of prices and any trades executed at those times.
        In a real app, this would fetch 1-min data from yfinance and 
        merge it with the DB ledger. For testing, we simulate realistic 1-min ticks.
        """
        
        # Start at 9:15 AM
        try:
            start_time = datetime.datetime.strptime(f"{date} 09:15:00", "%Y-%m-%d %H:%M:%S")
        except:
            start_time = datetime.datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
            
        base_price = 23500.0 if symbol.upper() == "NIFTY" else 1500.0
        current_price = base_price
        
        timeline = []
        trades = []
        
        # Generate 375 minutes of data (9:15 AM to 3:30 PM)
        for i in range(375):
            tick_time = start_time + datetime.timedelta(minutes=i)
            # Random walk
            change = random.normalvariate(0, base_price * 0.0005) 
            current_price += change
            current_price = round(current_price, 2)
            
            data_point = {
                "time": tick_time.strftime("%H:%M"),
                "full_time": tick_time.isoformat(),
                "price": current_price,
                "action": None,
                "qty": 0
            }
            
            # Simulate a few random trades during the day (about 5 trades total)
            if random.random() < 0.015 and len(trades) < 6:
                action = "BUY" if random.random() > 0.5 else "SELL"
                qty = random.randint(10, 100)
                data_point["action"] = action
                data_point["qty"] = qty
                
                trades.append({
                    "id": f"TRD-{len(trades)+100}",
                    "time": data_point["time"],
                    "action": action,
                    "price": current_price,
                    "qty": qty
                })
                
            timeline.append(data_point)
            
        return {
            "symbol": symbol,
            "date": date,
            "timeline": timeline,
            "trades": trades
        }
