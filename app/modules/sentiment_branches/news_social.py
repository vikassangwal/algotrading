import logging
import yfinance as yf

logger = logging.getLogger("elco.module.sentiment.news")

class NewsSocialEngine:
    """
    Handles NLP for News, Social Media (Twitter/Reddit), and Macro Events.
    """
    def __init__(self, raw_data: dict, symbol: str = None):
        self.data = raw_data
        self.symbol = symbol

    def _fetch_yfinance_news_sentiment(self) -> float:
        if not self.symbol:
            return None
            
        try:
            ticker = yf.Ticker(self.symbol)
            news = ticker.news
            if not news:
                return None
            
            # Simple keyword-based sentiment approximation
            positive_words = {
                'surge', 'jump', 'beat', 'growth', 'up', 'high', 'profit', 'record', 'gain', 'buy', 'upgrade', 'bull',
                'buyback', 'dividend', 'merger', 'acquisition', 'approval', 'guidance', 'positive', 'win', 'contract'
            }
            negative_words = {
                'fall', 'drop', 'miss', 'decline', 'down', 'low', 'loss', 'crash', 'sell', 'downgrade', 'bear',
                'lawsuit', 'resignation', 'sanction', 'war', 'penalty', 'warning', 'negative', 'fraud', 'probe', 'reject'
            }
            
            # Macro / Geopolitical weight adjustments
            macro_keywords = {'rbi', 'fed', 'election', 'budget', 'gdp', 'inflation', 'pmi'}
            
            pos_score = 0
            neg_score = 0
            
            for article in news:
                title = article.get('title', '')
                text = f"{title}".lower()
                words = set(text.split())
                
                weight = 1
                if words.intersection(macro_keywords):
                    weight = 2 # Macro news holds more weight in Institutional trading
                
                if words.intersection(positive_words):
                    pos_score += weight
                if words.intersection(negative_words):
                    neg_score += weight
                    
            total_matches = pos_score + neg_score
            if total_matches == 0:
                return 0.0
                
            return (pos_score - neg_score) / total_matches
        except Exception as e:
            logger.error(f"Failed to fetch yfinance news for {self.symbol}: {e}")
            return None

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # 1. News Sentiment (Earnings, RBI, Global)
            news_polarity = self.data.get("news_polarity_score")
            
            # Fallback to fetching live news from yfinance if not provided in data
            if news_polarity is None:
                news_polarity = self._fetch_yfinance_news_sentiment()

            if news_polarity is not None:
                if news_polarity > 0.7:
                    score += 0.5
                    reasons.append(f"News Sentiment: Highly Positive news flow (score: {news_polarity:.2f}).")
                elif news_polarity < -0.7:
                    score -= 1.0  # Heavy penalty
                    reasons.append(f"HALT SIGNAL: Extremely Negative news / Macro event detected (score: {news_polarity:.2f}).")
                elif news_polarity > 0.1:
                    score += 0.1
                    reasons.append(f"News Sentiment: Mildly positive news flow (score: {news_polarity:.2f}).")
                elif news_polarity < -0.1:
                    score -= 0.1
                    reasons.append(f"News Sentiment: Mildly negative news flow (score: {news_polarity:.2f}).")
                else:
                    reasons.append(f"News Sentiment: Neutral news flow (score: {news_polarity:.2f}).")
            else:
                reasons.append("News Sentiment: No news data available.")

            # 2. Social Media Buzz (Retail Sentiment)
            social_sentiment = self.data.get("social_sentiment_score")
            social_volume = self.data.get("social_volume_spike")
            
            if social_sentiment is not None and social_volume is not None:
                if social_volume and social_sentiment > 0.7:
                    score -= 0.2 
                    reasons.append("Social Media: Retail Extreme FOMO detected (Contrarian Bearish).")
                elif social_volume and social_sentiment < -0.7:
                    score += 0.2 
                    reasons.append("Social Media: Retail Extreme Panic detected (Contrarian Bullish).")
                elif social_sentiment > 0.3:
                    score += 0.1
                    reasons.append("Social Media: Healthy positive retail sentiment.")
                elif social_sentiment < -0.3:
                    score -= 0.1
                    reasons.append("Social Media: General retail pessimism.")
            else:
                reasons.append("Social Media: No social sentiment data available.")

            # 3. Macro Event Risk
            event_risk_active = self.data.get("is_major_event_day")
            if event_risk_active is True:
                reasons.append("Macro Event: Major Event Day detected. Volatility expected.")

        except Exception as e:
            logger.error(f"Error in NewsSocialEngine: {e}")
            reasons.append("News/Social Engine: Error processing NLP sentiment.")

        return {
            "branch": "News & Social Sentiment (NLP)",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
