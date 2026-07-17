from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger("elco.module.news_risk")
analyzer = SentimentIntensityAnalyzer()

class NewsRiskModule(AnalysisModule):
    name = "news_risk"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            news_items = self.provider.get_news(limit=10)
        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch news data."])

        if not news_items:
            return ModuleSignal(self.name, 0.0, 0.1, ["No recent news found."])

        # Aggregate NLP sentiment/severity scores
        # VADER compound score is from -1 (Extremely Negative) to +1 (Extremely Positive)
        total_compound = 0.0
        reasons = []
        
        for item in news_items:
            sentiment_dict = analyzer.polarity_scores(item.headline)
            compound = sentiment_dict['compound']
            total_compound += compound
            
            if compound <= -0.4:
                reasons.append(f"High Risk Alert (Score {compound}): {item.headline}")

        avg_compound = total_compound / len(news_items)
        
        # We need a score from -1 (Strong Sell / High Risk) to +1 (Strong Buy / Safe)
        # avg_compound is naturally between -1 and +1. We can just use it!
        score = avg_compound
        
        # Confidence increases with the extremeness of the news (absolute value of compound score)
        # Base confidence 0.3, plus scaled by abs(score)
        confidence = 0.3 + (abs(avg_compound) * 0.7)

        if avg_compound > 0.05:
            reasons.append(f"Overall news sentiment is positive (Compound: {avg_compound:.2f})")
        elif avg_compound < -0.05:
            reasons.append(f"Elevated market risk detected (Compound: {avg_compound:.2f})")
        else:
            reasons.append(f"Overall news sentiment is neutral (Compound: {avg_compound:.2f})")

        return ModuleSignal(
            module=self.name,
            score=score,
            confidence=confidence,
            reasons=reasons
        )
