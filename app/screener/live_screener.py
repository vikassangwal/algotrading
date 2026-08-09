import concurrent.futures
import yfinance as yf
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Full 50 Nifty 50 Bluechip Constituents
NIFTY_50_SYMBOLS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS", "BHARTIARTL.NS", "ITC.NS",
    "SBIN.NS", "LT.NS", "KOTAKBANK.NS", "AXISBANK.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "M&M.NS", "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS", "NESTLEIND.NS", "WIPRO.NS", "JSWSTEEL.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "TECHM.NS", "ONGC.NS", "COALINDIA.NS", "BAJAJFINSV.NS", "HINDALCO.NS", "GRASIM.NS",
    "DRREDDY.NS", "CIPLA.NS", "EICHERMOT.NS", "BRITANNIA.NS", "DIVISLAB.NS", "HEROMOTOCO.NS",
    "APOLLOHOSP.NS", "BAJAJ-AUTO.NS", "TATACONSUM.NS", "INDUSINDBK.NS", "SBILIFE.NS", "HDFCLIFE.NS",
    "SHRIRAMFIN.NS", "BPCL.NS"
]

# Comprehensive Institutional Multi-Asset Universe (Largecaps, Midcaps, Smallcaps, MCX Commodities & FX)
UNIVERSAL_SYMBOLS = [
    # Nifty 50 Core
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS", "BHARTIARTL.NS", "ITC.NS",
    "SBIN.NS", "LT.NS", "KOTAKBANK.NS", "AXISBANK.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "M&M.NS", "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    # High-Growth Midcaps, Smallcaps & PSUs
    "SUZLON.NS", "IREDA.NS", "JIOFIN.NS", "PAYTM.NS", "TATAPOWER.NS", "TATAELXSI.NS", "TATACHEM.NS",
    "TATATECH.NS", "TATACOMM.NS", "TATAINVEST.NS", "RVNL.NS", "IRFC.NS", "RAILTEL.NS", "NHPC.NS",
    "HAL.NS", "BEL.NS", "CDSL.NS", "ANGELONE.NS", "POLICYBZR.NS", "MCX.NS", "KALYANKJIL.NS",
    "BHEL.NS", "DLF.NS", "GODREJPROP.NS", "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS", "TRENT.NS",
    "VBL.NS", "CHOLAFIN.NS", "PFC.NS", "RECLTD.NS", "IOC.NS", "GAIL.NS", "SAIL.NS", "NMDC.NS",
    "VEDL.NS", "AMBUJACEM.NS", "ACC.NS", "INDIGO.NS", "IRCTC.NS", "YESBANK.NS", "IDFCFIRSTB.NS",
    "FEDERALBNK.NS", "AUBANK.NS", "BANKBARODA.NS", "CANBK.NS", "PNB.NS", "DIXON.NS", "POLYCAB.NS",
    "HAVELLS.NS", "PIDILITIND.NS", "COLPAL.NS", "DABUR.NS", "MARICO.NS", "LUPIN.NS", "ZYDUSLIFE.NS",
    "AUROPHARMA.NS", "BIOCON.NS", "MAXHEALTH.NS", "NAUKRI.NS", "NYKAA.NS", "DELHIVERY.NS",
    # Commodities (MCX Proxies)
    "GC=F", "SI=F", "CL=F", "NG=F", "HG=F",
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
