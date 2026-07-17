import logging
import pandas as pd
import numpy as np
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from ..data.provider import DataProvider
from .base import AnalysisModule, ModuleSignal

logger = logging.getLogger("elco.module.forecasting")

class ForecastingModule(AnalysisModule):
    name = "forecasting"

    def analyze(self, symbol: str) -> ModuleSignal:
        try:
            # Fetch 150 days of data to train the model and test
            candles = self.provider.get_candles(symbol, timeframe="1d", count=150)
        except Exception as e:
            logger.error(f"Failed to fetch data for Forecasting: {e}")
            return ModuleSignal(self.name, 0.0, 0.0, ["Failed to fetch market data."])

        if len(candles) < 50:
            return ModuleSignal(self.name, 0.0, 0.1, ["Insufficient data to train QDA model."])

        # Create pandas dataframe
        df = pd.DataFrame([c.close for c in candles], columns=['close'])
        
        # Calculate daily returns
        df['returns'] = df['close'].pct_change() * 100.0
        
        # Create Lagged Returns as features (Lag1, Lag2)
        df['Lag1'] = df['returns'].shift(1)
        df['Lag2'] = df['returns'].shift(2)
        
        # Create Direction as target variable (1 for Up, -1 for Down)
        df['Direction'] = np.where(df['returns'] > 0, 1, -1)
        
        # Drop NaN values due to shift
        df = df.dropna()
        
        if len(df) < 10:
            return ModuleSignal(self.name, 0.0, 0.1, ["Insufficient data after dropping NaNs."])

        # Train the model using the past data up to the penultimate day
        train_data = df.iloc[:-1]
        
        X_train = train_data[['Lag1', 'Lag2']]
        y_train = train_data['Direction']
        
        # We need both classes to train QDA.
        if len(y_train.unique()) < 2:
            return ModuleSignal(self.name, 0.0, 0.1, ["Not enough class variance to train QDA."])

        # Initialize and fit the QDA model
        model = QuadraticDiscriminantAnalysis()
        model.fit(X_train, y_train)
        
        # Now predict for the current day using the latest known lags
        # The 'current' day for which we want to predict the next direction
        # means we use today's return as Lag1 and yesterday's return as Lag2
        latest_lag1 = df['returns'].iloc[-1]
        latest_lag2 = df['Lag1'].iloc[-1]
        
        X_test = pd.DataFrame([[latest_lag1, latest_lag2]], columns=['Lag1', 'Lag2'])
        
        prediction = model.predict(X_test)[0]
        probabilities = model.predict_proba(X_test)[0]
        
        # probabilities array has shape [P(class=-1), P(class=1)]
        # We find the probability of the predicted class
        max_prob = max(probabilities)
        
        reasons = [
            f"Machine Learning Forecasting (QDA Model)",
            f"Features: Lag1 = {latest_lag1:.2f}%, Lag2 = {latest_lag2:.2f}%",
            f"Model Prediction: {'UP (+1)' if prediction == 1 else 'DOWN (-1)'}",
            f"Probability: {max_prob * 100:.1f}%"
        ]

        score = 0.0
        confidence = max_prob # Baseline confidence
        
        if prediction == 1:
            score = 1.0 # Buy
            reasons.append("QDA Classifier predicts an UPWARD movement.")
        else:
            score = -1.0 # Sell
            reasons.append("QDA Classifier predicts a DOWNWARD movement.")

        return ModuleSignal(
            module=self.name,
            score=score,
            confidence=confidence,
            reasons=reasons
        )
