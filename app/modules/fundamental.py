import logging
import yfinance as yf
from .base import AnalysisModule, ModuleSignal

from .fundamental_branches.financials import FinancialEngine
from .fundamental_branches.valuation import ValuationEngine
from .fundamental_branches.forensic_quant import ForensicQuantEngine
from .fundamental_branches.macro_industry import MacroIndustryEngine

logger = logging.getLogger("elco.module.fundamental.master")

class FundamentalModule(AnalysisModule):
    name = "fundamental"

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []
        
        try:
            raw_data = self.provider.get_fundamentals(symbol) if hasattr(self.provider, 'get_fundamentals') else {}
            current_price = self.provider.get_quote(symbol).ltp
            
            # Fetch real fundamental data using yfinance
            try:
                yf_ticker = yf.Ticker(symbol)
                yf_info = yf_ticker.info
                
                if yf_info:
                    raw_data["returnOnEquity"] = yf_info.get("returnOnEquity")
                    raw_data["returnOnAssets"] = yf_info.get("returnOnAssets")
                    raw_data["debtToEquity"] = yf_info.get("debtToEquity")
                    raw_data["currentRatio"] = yf_info.get("currentRatio")
                    raw_data["earningsGrowth"] = yf_info.get("earningsGrowth")
                    raw_data["revenueGrowth"] = yf_info.get("revenueGrowth")
                    raw_data["freeCashflow"] = yf_info.get("freeCashflow")
                    raw_data["operatingMargins"] = yf_info.get("operatingMargins")
                    
                    raw_data["trailingPE"] = yf_info.get("trailingPE")
                    raw_data["forwardPE"] = yf_info.get("forwardPE")
                    raw_data["priceToBook"] = yf_info.get("priceToBook")
                    raw_data["enterpriseToEbitda"] = yf_info.get("enterpriseToEbitda")
                    raw_data["trailingEps"] = yf_info.get("trailingEps")
                    raw_data["bookValue"] = yf_info.get("bookValue")
                    
                    raw_data["heldPercentInstitutions"] = yf_info.get("heldPercentInstitutions")
                    raw_data["heldPercentInsiders"] = yf_info.get("heldPercentInsiders")
                    
                    # New Institutional Metrics
                    raw_data["dividendYield"] = yf_info.get("dividendYield")
                    raw_data["marketCap"] = yf_info.get("marketCap")
                    raw_data["enterpriseValue"] = yf_info.get("enterpriseValue")
                    raw_data["grossMargins"] = yf_info.get("grossMargins")
                    raw_data["profitMargins"] = yf_info.get("profitMargins")
                    raw_data["ebitdaMargins"] = yf_info.get("ebitdaMargins")
                    raw_data["quickRatio"] = yf_info.get("quickRatio")
                    raw_data["operatingCashflow"] = yf_info.get("operatingCashflow")
                    raw_data["enterpriseToRevenue"] = yf_info.get("enterpriseToRevenue")
                    raw_data["priceToSalesTrailing12Months"] = yf_info.get("priceToSalesTrailing12Months")
                    raw_data["payoutRatio"] = yf_info.get("payoutRatio")
                    raw_data["totalAssets"] = yf_info.get("totalAssets") # for ROIC proxy
            except Exception as e:
                logger.warning(f"Failed to fetch yfinance data for {symbol}: {e}")
                
        except Exception as e:
            logger.error(f"Failed to fetch quote/fundamental data for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch fundamental data."])

        reasons.append("--- MASTER 15-PILLAR FUNDAMENTAL ENGINE INITIALIZED ---")

        total_score = 0.0
        
        fin_engine = FinancialEngine(raw_data)
        fin_res = fin_engine.analyze()
        total_score += fin_res['score']
        reasons.extend(fin_res['reasons'])

        val_engine = ValuationEngine(raw_data, current_price)
        val_res = val_engine.analyze()
        total_score += val_res['score']
        reasons.extend(val_res['reasons'])

        for_engine = ForensicQuantEngine(raw_data)
        for_res = for_engine.analyze()
        total_score += for_res['score']
        reasons.extend(for_res['reasons'])

        mac_engine = MacroIndustryEngine(raw_data)
        mac_res = mac_engine.analyze()
        total_score += mac_res['score']
        reasons.extend(mac_res['reasons'])

        final_score = total_score / 4.0
        
        engine_scores = [fin_res['score'], val_res['score'], for_res['score'], mac_res['score']]
        bulls = sum(1 for s in engine_scores if s > 0)
        bears = sum(1 for s in engine_scores if s < 0)
        
        if bulls == 4 or bears == 4:
            confidence = 0.95
            reasons.insert(1, "PERFECT FUNDAMENTAL CONFLUENCE: All 4 Institutional Models agree.")
        elif bulls >= 3 or bears >= 3:
            confidence = 0.75
            reasons.insert(1, "STRONG FUNDAMENTAL CONFLUENCE: 3 out of 4 Models agree.")
        elif bulls == 0 and bears == 0 and final_score == 0:
            confidence = 0.0
            reasons.insert(1, "NO FUNDAMENTALS: Insufficient data to score.")
        else:
            confidence = 0.40
            reasons.insert(1, "MIXED FUNDAMENTALS: Models are giving conflicting signals or have partial data.")

        if final_score > 0.4:
            reasons.insert(0, f"FUNDAMENTAL RATING: STRONG BUY / HIGH QUALITY (Score: +{final_score:.2f})")
        elif final_score < -0.4:
            reasons.insert(0, f"FUNDAMENTAL RATING: STRONG SELL / JUNK QUALITY (Score: {final_score:.2f})")
        else:
            reasons.insert(0, f"FUNDAMENTAL RATING: NEUTRAL / AVERAGE (Score: {final_score:.2f})")

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
