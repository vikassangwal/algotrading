import logging
import yfinance as yf
from .base import AnalysisModule, ModuleSignal

# Import the Sector sub-engines
from .sector_branches.industry_structure import IndustryStructureEngine
from .sector_branches.relative_strength import RelativeStrengthEngine
from .sector_branches.sector_fundamental import SectorFundamentalEngine
from .sector_branches.flow_risk import SectorFlowRiskEngine

logger = logging.getLogger("elco.module.sector.master")

class SectorModule(AnalysisModule):
    name = "sector"

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []
        
        try:
            # We assume sector_name logic is handled upstream or passed through.
            # Fetch real sector data using yfinance (cached 15m)
            raw_data = {}
            try:
                from ..yf_cache import get_cached_yf_info
                yf_info = get_cached_yf_info(symbol)
                if yf_info:
                    raw_data["sector"] = yf_info.get("sector")
                    raw_data["industry"] = yf_info.get("industry")
            except Exception as e:
                logger.warning(f"Failed to fetch yfinance sector info for {symbol}: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch sector data for {symbol}: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch sector data."])
        
        reasons.append("--- MASTER 10-LEVEL SECTOR & THEMATIC ENGINE INITIALIZED ---")

        total_score = 0.0
        
        # ==========================================
        # ENGINE 1: Industry Structure
        # ==========================================
        structure_engine = IndustryStructureEngine(raw_data)
        structure_res = structure_engine.analyze()
        total_score += structure_res['score']
        reasons.extend(structure_res['reasons'])

        # ==========================================
        # ENGINE 2: Relative Strength
        # ==========================================
        relative_engine = RelativeStrengthEngine(raw_data)
        relative_res = relative_engine.analyze()
        total_score += relative_res['score']
        reasons.extend(relative_res['reasons'])

        # ==========================================
        # ENGINE 3: Sector Fundamentals
        # ==========================================
        fund_engine = SectorFundamentalEngine(raw_data)
        fund_res = fund_engine.analyze()
        total_score += fund_res['score']
        reasons.extend(fund_res['reasons'])

        # ==========================================
        # ENGINE 4: Flows & Risk
        # ==========================================
        flow_engine = SectorFlowRiskEngine(raw_data)
        flow_res = flow_engine.analyze()
        total_score += flow_res['score']
        reasons.extend(flow_res['reasons'])

        # ==========================================
        # MASTER SECTOR AGGREGATION
        # ==========================================
        final_score = total_score / 4.0
        
        # Confidence based on Alpha and Flows
        engine_scores = [structure_res['score'], relative_res['score'], fund_res['score'], flow_res['score']]
        bulls = sum(1 for s in engine_scores if s > 0.1)
        bears = sum(1 for s in engine_scores if s < -0.1)
        
        if bulls >= 3:
            confidence = 0.90
            reasons.insert(1, "SECTOR CONFLUENCE: Sector is enjoying massive Tailwinds (Alpha, Flows, and Themes align).")
        elif bears >= 3:
            confidence = 0.90
            reasons.insert(1, "SECTOR DIVERGENCE: Sector is facing severe Headwinds. Avoid entirely.")
        else:
            confidence = 0.50
            reasons.insert(1, "SECTOR MIXED: Sector is in consolidation or transition.")

        if final_score > 0.4:
            reasons.insert(0, f"SECTOR OUTLOOK: STRONG OUTPERFORMER (Score: +{final_score:.2f})")
        elif final_score < -0.4:
            reasons.insert(0, f"SECTOR OUTLOOK: STRONG UNDERPERFORMER (Score: {final_score:.2f})")
        else:
            reasons.insert(0, f"SECTOR OUTLOOK: MARKET PERFORM (Score: {final_score:.2f})")

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
