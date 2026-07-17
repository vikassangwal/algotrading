import datetime
from collections import defaultdict
from typing import List, Dict, Any, Union

class InstitutionalReporting:
    """
    A reporting engine for institutional trading that calculates 
    daily, weekly, and yearly P&L summaries, and generates tax reports.
    """
    
    def __init__(self):
        pass

    def _parse_date(self, date_val: Union[str, datetime.datetime, datetime.date]) -> datetime.datetime:
        """Helper method to parse date into a datetime object."""
        if isinstance(date_val, datetime.datetime):
            return date_val
        elif isinstance(date_val, datetime.date):
            return datetime.datetime.combine(date_val, datetime.datetime.min.time())
        elif isinstance(date_val, str):
            # Assume YYYY-MM-DD or similar ISO prefix
            try:
                return datetime.datetime.strptime(date_val[:10], "%Y-%m-%d")
            except ValueError:
                pass
        return None

    def calculate_daily_pnl(self, trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate daily P&L from a list of trades.
        Expects trades to have a 'date' and 'pnl' key.
        """
        daily_pnl = defaultdict(float)
        for trade in trades:
            date_obj = self._parse_date(trade.get('date'))
            if not date_obj:
                continue
                
            date_str = date_obj.strftime("%Y-%m-%d")
            daily_pnl[date_str] += trade.get('pnl', 0.0)
            
        return dict(daily_pnl)

    def calculate_weekly_pnl(self, trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate weekly P&L from a list of trades.
        Returns keys in the format 'YYYY-Www'.
        """
        weekly_pnl = defaultdict(float)
        for trade in trades:
            date_obj = self._parse_date(trade.get('date'))
            if not date_obj:
                continue
                
            year, week, _ = date_obj.isocalendar()
            week_str = f"{year}-W{week:02d}"
            weekly_pnl[week_str] += trade.get('pnl', 0.0)
            
        return dict(weekly_pnl)

    def calculate_yearly_pnl(self, trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate yearly P&L from a list of trades.
        """
        yearly_pnl = defaultdict(float)
        for trade in trades:
            date_obj = self._parse_date(trade.get('date'))
            if not date_obj:
                continue
                
            year_str = str(date_obj.year)
            yearly_pnl[year_str] += trade.get('pnl', 0.0)
            
        return dict(yearly_pnl)

    def generate_tax_report(self, trades: List[Dict[str, Any]], year: int = None) -> Dict[str, Any]:
        """
        Generate a structured Tax Report dictionary.
        Can optionally filter by a specific year.
        Trades can optionally have an 'is_long_term' boolean to separate STCG/LTCG.
        """
        tax_report = {
            'total_realized_pnl': 0.0,
            'short_term_capital_gains': 0.0,
            'long_term_capital_gains': 0.0,
            'total_trades': 0,
            'profitable_trades': 0,
            'loss_making_trades': 0,
        }
        
        for trade in trades:
            date_obj = self._parse_date(trade.get('date'))
            if not date_obj:
                continue
                
            if year is not None and date_obj.year != year:
                continue

            pnl = float(trade.get('pnl', 0.0))
            is_long_term = bool(trade.get('is_long_term', False))
            
            tax_report['total_realized_pnl'] += pnl
            tax_report['total_trades'] += 1
            
            if pnl > 0:
                tax_report['profitable_trades'] += 1
                if is_long_term:
                    tax_report['long_term_capital_gains'] += pnl
                else:
                    tax_report['short_term_capital_gains'] += pnl
            elif pnl < 0:
                tax_report['loss_making_trades'] += 1
                # Losses are also categorized into ST/LT to net against gains appropriately
                if is_long_term:
                    tax_report['long_term_capital_gains'] += pnl
                else:
                    tax_report['short_term_capital_gains'] += pnl
                    
        return tax_report
