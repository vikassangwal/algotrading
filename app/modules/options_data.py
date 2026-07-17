import yfinance as yf
from typing import Dict, List, Any
import datetime
import logging

logger = logging.getLogger("elco.options_data")

class OptionsDataEngine:
    """
    Engine to fetch live/historical Options Chain data.
    Uses yfinance as the data source.
    """
    
    def get_expirations(self, symbol: str) -> List[str]:
        """
        Fetch available expiration dates for a symbol.
        """
        try:
            # Map Indian indices for yfinance if needed, e.g., NIFTY -> ^NSEI
            if symbol.upper() == "NIFTY":
                symbol = "^NSEI"
            elif symbol.upper() == "BANKNIFTY":
                symbol = "^NSEBANK"
            elif not symbol.endswith(".NS") and not symbol.startswith("^"):
                # Default assume US symbol if no .NS for Indian testing
                pass
                
            ticker = yf.Ticker(symbol)
            exps = ticker.options
            
            if not exps:
                # Fallback to simulated expirations if yf has no data
                return self._generate_simulated_expirations()
            return list(exps)
        except Exception as e:
            logger.warning(f"Failed to fetch expirations for {symbol}: {e}")
            return self._generate_simulated_expirations()

    def get_option_chain(self, symbol: str, date: str) -> Dict[str, Any]:
        """
        Fetch the full option chain (Calls and Puts) for a specific expiration date.
        """
        try:
            original_symbol = symbol
            if symbol.upper() == "NIFTY":
                symbol = "^NSEI"
            elif symbol.upper() == "BANKNIFTY":
                symbol = "^NSEBANK"
                
            ticker = yf.Ticker(symbol)
            chain = ticker.option_chain(date)
            
            calls = chain.calls.to_dict(orient='records')
            puts = chain.puts.to_dict(orient='records')
            
            # Format to a standard UI structure
            formatted_calls = []
            formatted_puts = []
            strikes = set()
            
            for c in calls:
                strikes.add(c['strike'])
                formatted_calls.append({
                    "strike": c['strike'],
                    "ltp": c.get('lastPrice', 0),
                    "volume": c.get('volume', 0) or 0,
                    "oi": c.get('openInterest', 0) or 0,
                    "iv": c.get('impliedVolatility', 0) or 0,
                })
                
            for p in puts:
                strikes.add(p['strike'])
                formatted_puts.append({
                    "strike": p['strike'],
                    "ltp": p.get('lastPrice', 0),
                    "volume": p.get('volume', 0) or 0,
                    "oi": p.get('openInterest', 0) or 0,
                    "iv": p.get('impliedVolatility', 0) or 0,
                })
                
            # If empty (yfinance limitation for Indian stocks), fallback to synthetic
            if not formatted_calls and not formatted_puts:
                 return self._generate_simulated_chain(original_symbol, date)

            max_pain = 0
            if formatted_calls and formatted_puts:
                max_pain = self._calculate_max_pain(formatted_calls, formatted_puts, strikes)

            return {
                "symbol": original_symbol,
                "expirationDate": date,
                "underlyingPrice": ticker.fast_info.last_price,
                "calls": self._enrich_with_greeks(formatted_calls, "call", ticker.fast_info.last_price),
                "puts": self._enrich_with_greeks(formatted_puts, "put", ticker.fast_info.last_price),
                "strikes": sorted(list(strikes)),
                "max_pain": max_pain
            }
        except Exception as e:
            logger.warning(f"Failed to fetch option chain for {symbol} on {date}: {e}")
            return self._generate_simulated_chain(symbol, date)

    def _generate_simulated_expirations(self) -> List[str]:
        """Simulate next 4 weekly expirations."""
        today = datetime.date.today()
        # Find next Thursday (typical Indian expiry)
        days_ahead = 3 - today.weekday()
        if days_ahead <= 0: # Target next week if we've passed Thursday
            days_ahead += 7
        next_expiry = today + datetime.timedelta(days_ahead)
        
        exps = []
        for i in range(4):
            exps.append((next_expiry + datetime.timedelta(weeks=i)).strftime('%Y-%m-%d'))
        return exps

    def _generate_simulated_chain(self, symbol: str, date: str) -> Dict[str, Any]:
        """Simulate realistic option chain data centered around a fake price."""
        underlying = 23500.0 if symbol.upper() == "NIFTY" else 50000.0 if symbol.upper() == "BANKNIFTY" else 150.0
        
        strikes = []
        calls = []
        puts = []
        
        # Generate 10 strikes above and below ATM
        step = 100 if underlying > 10000 else 5
        atm_strike = round(underlying / step) * step
        
        import random
        random.seed(symbol + date) # deterministic mock
        
        for i in range(-10, 11):
            strike = atm_strike + (i * step)
            strikes.append(strike)
            
            # Synthetic Call Pricing
            c_ltp = max(0.5, (atm_strike - strike) * 0.5 + random.uniform(10, 50)) if i <= 0 else max(0.5, random.uniform(5, 40) - (i*2))
            calls.append({
                "strike": strike,
                "ltp": round(c_ltp, 2),
                "volume": random.randint(100, 50000),
                "oi": random.randint(1000, 200000),
                "iv": round(random.uniform(0.12, 0.25), 4)
            })
            
            # Synthetic Put Pricing
            p_ltp = max(0.5, (strike - atm_strike) * 0.5 + random.uniform(10, 50)) if i >= 0 else max(0.5, random.uniform(5, 40) + (i*2))
            puts.append({
                "strike": strike,
                "ltp": round(p_ltp, 2),
                "volume": random.randint(100, 50000),
                "oi": random.randint(1000, 200000),
                "iv": round(random.uniform(0.12, 0.25), 4)
            })
            
        max_pain = 0
        if calls and puts:
            max_pain = self._calculate_max_pain(calls, puts, strikes)
            
        return {
            "symbol": symbol,
            "expirationDate": date,
            "underlyingPrice": underlying,
            "calls": self._enrich_with_greeks(calls, "call", underlying),
            "puts": self._enrich_with_greeks(puts, "put", underlying),
            "strikes": strikes,
            "max_pain": max_pain
        }

    def _enrich_with_greeks(self, options_list: List[Dict], opt_type: str, underlying: float) -> List[Dict]:
        """Approximates Greeks if they are missing."""
        import math
        enriched = []
        for opt in options_list:
            opt = opt.copy()
            strike = opt.get("strike", underlying)
            
            # Very basic Black-Scholes ATM approximation for simulation
            # Normally requires time to expiry and risk-free rate
            diff_pct = (strike - underlying) / underlying
            
            if opt_type == "call":
                # Call Delta approaches 1 deep ITM, 0 deep OTM, 0.5 ATM
                delta = 0.5 - (diff_pct * 10)
                delta = max(0.0, min(1.0, delta))
            else:
                # Put Delta approaches -1 deep ITM, 0 deep OTM, -0.5 ATM
                delta = -0.5 - (diff_pct * 10) 
                delta = max(-1.0, min(0.0, delta))
                
            # Gamma is highest ATM
            gamma = 0.05 * math.exp(-(diff_pct * 10)**2)
            
            # Theta decays, highest ATM
            theta = -0.05 * math.exp(-(diff_pct * 5)**2)
            
            # Vega highest ATM
            vega = 0.20 * math.exp(-(diff_pct * 8)**2)
            
            opt["delta"] = opt.get("delta") or round(delta, 3)
            opt["gamma"] = opt.get("gamma") or round(gamma, 4)
            opt["theta"] = opt.get("theta") or round(theta, 3)
            opt["vega"] = opt.get("vega") or round(vega, 3)
            enriched.append(opt)
        return enriched

    def _calculate_max_pain(self, calls: List[Dict], puts: List[Dict], strikes: List[float]) -> float:
        """Calculates the strike price where option buyers lose the most money."""
        min_pain = float('inf')
        max_pain_strike = strikes[len(strikes)//2] if strikes else 0
        
        for strike in strikes:
            total_pain = 0
            
            # Call buyers pain (Value at expiry)
            for c in calls:
                if c["strike"] < strike:
                    total_pain += (strike - c["strike"]) * c.get("oi", 0)
                    
            # Put buyers pain
            for p in puts:
                if p["strike"] > strike:
                    total_pain += (p["strike"] - strike) * p.get("oi", 0)
                    
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = strike
                
        return float(max_pain_strike)
