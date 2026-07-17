import concurrent.futures
import yfinance as yf
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Core Nifty 50 Symbols (reduced for speed in initial tests, can be expanded to full 50)
NIFTY_50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS", "KOTAKBANK.NS",
    "HINDUNILVR.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "ASIANPAINT.NS"
]

# Universal Symbols covering multiple asset classes
UNIVERSAL_SYMBOLS = [
    # Equities
    "RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "TATAMOTORS.NS",
    # Commodities (MCX proxies via global futures)
    "GC=F", "SI=F", "CL=F", "NG=F", 
    # Currencies (USDINR, EURINR, GBPINR)
    "INR=X", "EURINR=X", "GBPINR=X"
]

class LiveScreener:
    def __init__(self, brain_instance):
        self.brain = brain_instance

    def _scan_single_stock(self, symbol: str) -> Dict[str, Any]:
        """Scans a single stock by fetching its current price and running the Master Brain."""
        try:
            logger.info(f"Screener processing: {symbol}")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            
            if hist.empty:
                logger.warning(f"No price data found for {symbol}")
                return {"symbol": symbol, "error": "No price data"}
                
            current_price = float(hist['Close'].iloc[-1])
            
            # Run the 15-step institutional workflow
            result = self.brain.execute_institutional_workflow(
                symbol=symbol,
                current_price=current_price,
                sector="General", # We could map sectors dynamically later
                factor="Momentum"
            )
            
            # Extract JSON_DATA if present in technical contributions
            composite_json = None
            if "technical" in result.get("contributions", {}):
                tech_reasons = result["contributions"]["technical"].get("reasons", [])
                for r in tech_reasons:
                    if r.startswith("JSON_DATA:"):
                        import json
                        try:
                            composite_json = json.loads(r.split("JSON_DATA:", 1)[1])
                        except:
                            pass
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "decision": result.get("decision", "HOLD"),
                "analytical_score": result.get("analytical_score", 0.0),
                "contributions": result.get("contributions", {}),
                "ai_composite": composite_json
            }
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}

    def run_nifty50_scan(self, max_workers: int = 10) -> List[Dict[str, Any]]:
        """Runs the Master Brain across Nifty 50 stocks concurrently."""
        results = []
        
        # We use ThreadPoolExecutor for I/O bound concurrency (yfinance + API calls)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map the function across all symbols
            future_to_symbol = {executor.submit(self._scan_single_stock, sym): sym for sym in NIFTY_50_SYMBOLS}
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                sym = future_to_symbol[future]
                try:
                    data = future.result()
                    if "error" not in data:
                        results.append(data)
                except Exception as e:
                    logger.error(f"Screener future failed for {sym}: {e}")
                    
        # Sort results by highest analytical score first
        results.sort(key=lambda x: x.get("analytical_score", 0), reverse=True)
        
        return results

    def run_universal_scan(self, max_workers: int = 15) -> List[Dict[str, Any]]:
        """Runs the Master Brain across Equities, Commodities, and Currencies concurrently."""
        results = []
        
        # We use ThreadPoolExecutor for I/O bound concurrency (yfinance + API calls)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {executor.submit(self._scan_single_stock, sym): sym for sym in UNIVERSAL_SYMBOLS}
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                sym = future_to_symbol[future]
                try:
                    data = future.result()
                    if "error" not in data:
                        # Add segment info for UI filtering
                        if "=F" in sym:
                            data["segment"] = "COMMODITY"
                        elif "=X" in sym:
                            data["segment"] = "CURRENCY"
                        else:
                            data["segment"] = "EQUITY"
                        
                        results.append(data)
                except Exception as e:
                    logger.error(f"Screener future failed for {sym}: {e}")
                    
        # Sort results by absolute analytical score (highest confidence first, whether BUY or SELL)
        results.sort(key=lambda x: abs(x.get("analytical_score", 0)), reverse=True)
        
        return results
