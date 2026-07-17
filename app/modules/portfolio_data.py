import random

class PortfolioDataEngine:
    def get_heatmap_data(self):
        """
        Generates realistic hierarchical portfolio data suitable for a Treemap/Heatmap.
        Grouped by Sector.
        """
        # Mock portfolio of top Indian Stocks for testing the UI
        portfolio_stocks = [
            {"symbol": "HDFCBANK", "sector": "Financial Services", "allocation": 150000, "chg": -1.2},
            {"symbol": "ICICIBANK", "sector": "Financial Services", "allocation": 120000, "chg": 0.5},
            {"symbol": "SBIN", "sector": "Financial Services", "allocation": 80000, "chg": 2.1},
            {"symbol": "KOTAKBANK", "sector": "Financial Services", "allocation": 60000, "chg": -0.4},
            
            {"symbol": "TCS", "sector": "Information Technology", "allocation": 140000, "chg": 1.8},
            {"symbol": "INFY", "sector": "Information Technology", "allocation": 110000, "chg": -0.9},
            {"symbol": "HCLTECH", "sector": "Information Technology", "allocation": 50000, "chg": 3.2},
            {"symbol": "WIPRO", "sector": "Information Technology", "allocation": 40000, "chg": 0.1},
            
            {"symbol": "RELIANCE", "sector": "Energy", "allocation": 180000, "chg": 2.5},
            {"symbol": "ONGC", "sector": "Energy", "allocation": 50000, "chg": -1.5},
            {"symbol": "NTPC", "sector": "Energy", "allocation": 40000, "chg": 0.8},
            
            {"symbol": "HUL", "sector": "Consumer Goods", "allocation": 70000, "chg": -0.2},
            {"symbol": "ITC", "sector": "Consumer Goods", "allocation": 90000, "chg": 1.1},
            {"symbol": "TITAN", "sector": "Consumer Goods", "allocation": 45000, "chg": -2.4},
            
            {"symbol": "L&T", "sector": "Construction", "allocation": 85000, "chg": 1.4},
            
            {"symbol": "MARUTI", "sector": "Automobile", "allocation": 60000, "chg": -1.8},
            {"symbol": "M&M", "sector": "Automobile", "allocation": 45000, "chg": 2.2},
            {"symbol": "TATAMOTORS", "sector": "Automobile", "allocation": 55000, "chg": 4.1},
        ]
        
        # Adding slight randomization so the heatmap looks alive on refresh
        for stock in portfolio_stocks:
            stock["chg"] += round(random.uniform(-0.5, 0.5), 2)
            
        # Group by sector
        grouped = {}
        for stock in portfolio_stocks:
            sec = stock["sector"]
            if sec not in grouped:
                grouped[sec] = []
            grouped[sec].append({
                "name": stock["symbol"],
                "size": stock["allocation"], # Used by recharts for block size
                "change": round(stock["chg"], 2),
                "sector": sec
            })
            
        # Format into Recharts Treemap expected hierarchy
        children = []
        for sec, items in grouped.items():
            children.append({
                "name": sec,
                "children": items
            })
            
        return {
            "name": "Portfolio",
            "children": children
        }
