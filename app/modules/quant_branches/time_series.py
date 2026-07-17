import logging

logger = logging.getLogger("elco.module.quant.time_series")

class TimeSeriesEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            price_z_score = self.data.get("price_z_score")
            if price_z_score is not None:
                if price_z_score > 3.0:
                    score -= 0.3
                    reasons.append(f"Time Series: Price Z-Score is {price_z_score:.2f} (> 3 Std Dev). Extreme Mean Reversion (Bearish) expected.")
                elif price_z_score < -3.0:
                    score += 0.3
                    reasons.append(f"Time Series: Price Z-Score is {price_z_score:.2f} (< -3 Std Dev). Extreme Mean Reversion (Bullish) expected.")
                else:
                    reasons.append(f"Time Series: Price Z-Score is {price_z_score:.2f} (Within normal distribution bands).")

            arima_forecast_pct = self.data.get("arima_forecast_pct")
            if arima_forecast_pct is not None:
                if arima_forecast_pct > 0.01:
                    score += 0.15
                    reasons.append(f"Time Series (ARIMA): Auto-Regressive model forecasts an upward trajectory (+{arima_forecast_pct*100:.2f}%).")
                elif arima_forecast_pct < -0.01:
                    score -= 0.15
                    reasons.append(f"Time Series (ARIMA): Auto-Regressive model forecasts a downward trajectory ({arima_forecast_pct*100:.2f}%).")

            garch_vol_forecast = self.data.get("garch_vol_forecast")
            historical_vol = self.data.get("historical_vol")
            if garch_vol_forecast is not None and historical_vol is not None:
                if garch_vol_forecast > historical_vol * 1.5:
                    reasons.append("Time Series (GARCH): Volatility clustering detected. Expect massive price swings soon (Tail Risk).")
                    
            # 4. Skewness and Kurtosis (Return Distribution)
            df = self.data.get("df")
            if df is not None and len(df) > 50:
                returns = df['close'].pct_change().dropna()
                skewness = returns.skew()
                kurtosis = returns.kurtosis()
                
                if skewness < -1.0:
                    score -= 0.15
                    reasons.append(f"Statistics: High Negative Skewness ({skewness:.2f}). Severe tail risk (Crash probability).")
                elif skewness > 1.0:
                    score += 0.1
                    reasons.append(f"Statistics: Positive Skewness ({skewness:.2f}). Fat right tail (Breakout probability).")
                else:
                    reasons.append(f"Statistics: Normal Skewness ({skewness:.2f}).")
                    
                if kurtosis > 3.0:
                    reasons.append(f"Statistics: High Kurtosis ({kurtosis:.2f}). Leptokurtic distribution (Extreme moves are likely).")
                else:
                    reasons.append(f"Statistics: Normal Kurtosis ({kurtosis:.2f}).")
                    
                # 5. Monte Carlo Simulation Proxy
                import numpy as np
                mean_ret = returns.mean()
                std_ret = returns.std()
                # Simulate 100 paths for 30 days
                simulated_paths = np.random.normal(mean_ret, std_ret, (30, 100))
                cumulative_returns = np.exp(np.sum(simulated_paths, axis=0))
                prob_positive = np.sum(cumulative_returns > 1.0) / 100.0
                
                if prob_positive > 0.70:
                    score += 0.2
                    reasons.append(f"Monte Carlo: 100 Path Simulation shows {prob_positive*100:.1f}% probability of POSITIVE returns next month.")
                elif prob_positive < 0.30:
                    score -= 0.2
                    reasons.append(f"Monte Carlo: 100 Path Simulation shows {prob_positive*100:.1f}% probability of NEGATIVE returns next month.")
                else:
                    reasons.append(f"Monte Carlo: 100 Path Simulation shows NEUTRAL {prob_positive*100:.1f}% probability of positive returns.")

                # 6. Probability Models (Binomial & Poisson)
                from scipy.stats import binom, poisson
                
                # Binomial: Probability of >50% up days in next 20 days (assuming historical win rate)
                win_rate = (returns > 0).mean()
                prob_up_days = binom.sf(10, 20, win_rate) # probability of >10 wins out of 20
                if prob_up_days > 0.6:
                    reasons.append(f"Probability (Binomial): High likelihood ({prob_up_days*100:.1f}%) of more UP days than DOWN days next month.")
                elif prob_up_days < 0.4:
                    reasons.append(f"Probability (Binomial): High likelihood of more DOWN days than UP days next month.")
                    
                # Poisson: Expected large jumps (e.g. >2% moves)
                large_jump_rate = (returns.abs() > 0.02).sum() / (len(returns) / 252) # annualized jumps
                expected_jumps_month = max(0.1, large_jump_rate / 12)
                prob_jump = poisson.sf(0, expected_jumps_month) # prob of at least 1 jump
                reasons.append(f"Probability (Poisson): {prob_jump*100:.1f}% probability of a 2%+ volatility event in the next month.")

                # 7. Linear Regression (OLS) for Trend Beta
                x = np.arange(len(df))
                y = df['close'].values
                slope, intercept = np.polyfit(x, y, 1)
                beta_normalized = slope / y.mean() * 100 # percentage growth per day
                
                if beta_normalized > 0.1:
                    score += 0.15
                    reasons.append(f"Regression (OLS): Strong UPWARD linear trend (Beta = +{beta_normalized:.2f}%/day).")
                elif beta_normalized < -0.1:
                    score -= 0.15
                    reasons.append(f"Regression (OLS): Strong DOWNWARD linear trend (Beta = {beta_normalized:.2f}%/day).")

        except ImportError:
            reasons.append("Time Series Engine: Missing scipy/numpy for advanced probability models.")
        except Exception as e:
            logger.error(f"Error in TimeSeriesEngine: {e}")
            reasons.append("Time Series Engine: Error calculating stats.")

        return {
            "branch": "Time Series & Forecasting",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
