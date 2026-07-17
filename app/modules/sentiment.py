import logging
from .base import AnalysisModule, ModuleSignal

# Import the Sentiment sub-engines
from .sentiment_branches.news_social import NewsSocialEngine
from .sentiment_branches.market_breadth import MarketBreadthEngine
from .sentiment_branches.behavioral_quant import BehavioralQuantEngine
from .sentiment_branches.institutional_darkpool import InstitutionalDarkpoolEngine

logger = logging.getLogger("elco.module.sentiment.master")

class SentimentModule(AnalysisModule):
    name = "sentiment"

    def analyze(self, symbol: str) -> ModuleSignal:
        reasons = []
        
        try:
            # We still attempt to get raw_data, but expect branches to handle missing data or do their own fetching
            raw_data = self.provider.get_sentiment_data(symbol) if hasattr(self.provider, 'get_sentiment_data') else {}
        except Exception as e:
            logger.error(f"Failed to fetch initial sentiment data for {symbol}: {e}")
            raw_data = {}
        
        reasons.append("--- MASTER SENTIMENT ENGINE INITIALIZED ---")

        total_score = 0.0
        
        # ==========================================
        # ENGINE 1: News & Social NLP
        # ==========================================
        news_engine = NewsSocialEngine(raw_data, symbol)
        news_res = news_engine.analyze()
        total_score += news_res['score']
        reasons.extend(news_res['reasons'])

        # ==========================================
        # ENGINE 2: Behavioral & Sentiment Quant
        # ==========================================
        behav_engine = BehavioralQuantEngine(raw_data)
        behav_res = behav_engine.analyze()
        total_score += behav_res['score']
        reasons.extend(behav_res['reasons'])

        # ==========================================
        # ENGINE 3: Institutional Dark Pool Activity
        # ==========================================
        dp_engine = InstitutionalDarkpoolEngine(raw_data)
        dp_res = dp_engine.analyze()
        total_score += dp_res['score']
        reasons.extend(dp_res['reasons'])

        # ==========================================
        # ENGINE 4: Market Breadth & Positioning
        # ==========================================
        breadth_engine = MarketBreadthEngine(raw_data)
        breadth_res = breadth_engine.analyze()
        total_score += breadth_res['score']
        reasons.extend(breadth_res['reasons'])

        # ==========================================
        # MASTER SENTIMENT AGGREGATION
        # ==========================================
        final_score = total_score / 4.0
        
        # Confidence logic based on agreement across engines
        engine_scores = [news_res['score'], breadth_res['score'], behav_res['score'], dp_res['score']]
        bulls = sum(1 for s in engine_scores if s > 0.05)
        bears = sum(1 for s in engine_scores if s < -0.05)
        
        if bulls >= 3 or bears >= 3:
            confidence = 0.85
            reasons.insert(1, "STRONG SENTIMENT CONFLUENCE: Multiple data sources align.")
        else:
            confidence = 0.40
            reasons.insert(1, "MIXED SENTIMENT: Alternative data sources are diverging or neutral.")

        if final_score > 0.4:
            reasons.insert(0, f"OVERALL SENTIMENT: EXTREME FOMO / RISK-ON (Score: +{final_score:.2f})")
        elif final_score < -0.4:
            reasons.insert(0, f"OVERALL SENTIMENT: PANIC / RISK-OFF (Score: {final_score:.2f})")
        else:
            reasons.insert(0, f"OVERALL SENTIMENT: UNCERTAIN / NEUTRAL (Score: {final_score:.2f})")

        return ModuleSignal(
            module=self.name,
            score=round(final_score, 2),
            confidence=round(confidence, 2),
            reasons=reasons
        )
