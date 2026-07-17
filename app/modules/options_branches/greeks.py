import math
import logging

logger = logging.getLogger("elco.module.options.greeks")

class OptionsGreeksEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def _norm_cdf(self, x: float) -> float:
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def _norm_pdf(self, x: float) -> float:
        return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)

    def calculate_greeks(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call'):
        if T <= 0 or sigma <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
            
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        gamma = self._norm_pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * self._norm_pdf(d1) * math.sqrt(T) / 100

        if option_type == 'call':
            delta = self._norm_cdf(d1)
            theta = (- (S * sigma * self._norm_pdf(d1)) / (2 * math.sqrt(T)) 
                     - r * K * math.exp(-r * T) * self._norm_cdf(d2)) / 365
        else:
            delta = self._norm_cdf(d1) - 1.0
            theta = (- (S * sigma * self._norm_pdf(d1)) / (2 * math.sqrt(T)) 
                     + r * K * math.exp(-r * T) * self._norm_cdf(-d2)) / 365

        return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            current_price = self.data.get("spot_price")
            strike = self.data.get("atm_strike")
            dte = self.data.get("days_to_expiry")
            r = self.data.get("risk_free_rate")
            iv = self.data.get("atm_iv")
            
            if all(v is not None for v in [current_price, strike, dte, r, iv]):
                greeks = self.calculate_greeks(current_price, strike, dte / 365.0, r, iv, 'call')
            
            total_gamma = self.data.get("total_market_gamma")
            if total_gamma is not None:
                if total_gamma < -5000000:
                    score += 0.3
                    reasons.append(f"Greeks (Gamma): Severe Negative Dealer Gamma detected. High risk of a GAMMA SQUEEZE (explosive volatility).")
                elif total_gamma > 5000000:
                    score -= 0.1
                    reasons.append(f"Greeks (Gamma): Positive Dealer Gamma. Market makers are suppressing volatility (Sideways expected).")

            iv_percentile = self.data.get("iv_percentile")
            if iv_percentile is not None:
                if iv_percentile > 0.90:
                    score -= 0.2
                    reasons.append("Greeks (Vega/IV): IV Percentile > 90%. High probability of an IV Crush. Option selling favorable.")
                elif iv_percentile < 0.10:
                    score += 0.1
                    reasons.append("Greeks (Vega/IV): IV Percentile < 10%. Options are very cheap. Long premium strategies favored.")

            net_delta = self.data.get("net_institutional_delta")
            if net_delta is not None:
                if net_delta > 100000:
                    score += 0.2
                    reasons.append("Greeks (Delta): Institutions have massive positive Net Delta (Bullish Bias).")
                elif net_delta < -100000:
                    score -= 0.2
                    reasons.append("Greeks (Delta): Institutions have massive negative Net Delta (Bearish Bias).")

        except Exception as e:
            logger.error(f"Error in OptionsGreeksEngine: {e}")
            reasons.append("Options Greeks Engine: Error calculating mathematical Greeks.")

        return {
            "branch": "Options Greeks & IV Analysis",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
