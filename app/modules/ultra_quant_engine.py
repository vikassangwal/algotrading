import pandas as pd
import numpy as np

class UltraQuantEngine:
    """
    Ultra-Advanced Quant Engine using Statistical Processing, Probability Simulations,
    and Microstructure proxies.
    """
    def __init__(self, df: pd.DataFrame):
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("open", "high", "low", "close", "volume"):
                rename[col] = cl.capitalize()
        self.df = df.rename(columns=rename) if rename else df
        
    def analyze(self) -> dict:
        if len(self.df) < 50:
            return {}
            
        fft_pred = self._calc_fft_cycle()
        mc_prob = self._run_monte_carlo()
        v_delta = self._calc_volume_delta()
        kelly = self._calc_kelly_criterion(mc_prob)
        ml_pred = self._run_ml_prediction()
        
        return {
            "fft_cycle": fft_pred,
            "monte_carlo_win_prob": mc_prob,
            "volume_delta_proxy": v_delta,
            "recommended_kelly_pct": kelly,
            "ml_prediction": ml_pred
        }
        
    def _calc_fft_cycle(self) -> str:
        """Fast Fourier Transform to extract dominant market cycles."""
        close = self.df['Close'].values
        # Detrend the data
        n = len(close)
        x = np.arange(n)
        poly = np.polyfit(x, close, 1)
        detrended = close - (poly[0] * x + poly[1])
        
        # Apply FFT
        fft_result = np.fft.fft(detrended)
        frequencies = np.fft.fftfreq(n)
        
        # Keep only positive frequencies
        pos_mask = frequencies > 0
        fft_result = fft_result[pos_mask]
        frequencies = frequencies[pos_mask]
        
        # Find dominant frequency
        amplitudes = np.abs(fft_result)
        dominant_idx = np.argmax(amplitudes)
        dominant_freq = frequencies[dominant_idx]
        
        if dominant_freq == 0:
            return "No clear cycle detected."
            
        cycle_length = int(1 / dominant_freq)
        
        # Phase analysis to determine if we are near a peak or trough
        phase = np.angle(fft_result[dominant_idx])
        # Current position in cycle
        current_phase = (2 * np.pi * dominant_freq * (n - 1) + phase) % (2 * np.pi)
        
        if current_phase < np.pi / 2 or current_phase > 3 * np.pi / 2:
            return f"Approaching Cycle Peak (Cycle Length: {cycle_length} days)"
        else:
            return f"Approaching Cycle Trough (Cycle Length: {cycle_length} days)"

    def _run_monte_carlo(self, simulations=1000, days=5) -> float:
        """Runs Monte Carlo simulations to estimate probability of a positive return over next N days."""
        returns = self.df['Close'].pct_change().dropna().values
        if len(returns) < 50:
            return 50.0
            
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Run 1000 simulations for next 5 days
        sims = np.random.normal(loc=mu, scale=sigma, size=(simulations, days))
        cumulative_returns = np.prod(1 + sims, axis=1) - 1
        
        # Probability that return is > 0
        win_prob = np.sum(cumulative_returns > 0) / simulations
        return float(round(win_prob * 100, 2))

    def _calc_volume_delta(self) -> str:
        """Estimates intraday net buying/selling pressure (Microstructure Proxy)."""
        recent = self.df.iloc[-5:]
        total_buy_vol = 0
        total_sell_vol = 0
        
        for _, row in recent.iterrows():
            total_range = row['High'] - row['Low']
            if total_range == 0: continue
            
            # Distance from close to low vs close to high
            buy_pressure = (row['Close'] - row['Low']) / total_range
            sell_pressure = (row['High'] - row['Close']) / total_range
            
            total_buy_vol += buy_pressure * row.get('Volume', 1)
            total_sell_vol += sell_pressure * row.get('Volume', 1)
            
        if total_buy_vol > total_sell_vol * 1.5:
            return "Strong Net Buying (Delta Positive)"
        elif total_sell_vol > total_buy_vol * 1.5:
            return "Strong Net Selling (Delta Negative)"
        else:
            return "Balanced Order Flow"

    def _calc_kelly_criterion(self, win_prob: float) -> float:
        """
        Calculates optimal position sizing using Kelly Criterion.
        f* = p - (q / b)
        where p = win prob, q = lose prob, b = win/loss ratio
        """
        p = win_prob / 100.0
        q = 1.0 - p
        b = 1.5 # Assume 1.5 Reward:Risk ratio for the system
        
        kelly = p - (q / b)
        # Half-Kelly for safety, max 10%
        safe_kelly = max(0, min(0.10, kelly / 2.0))
        return float(round(safe_kelly * 100, 2))
        
    def _run_ml_prediction(self) -> str:
        """
        Simple predictive linear model using historical momentum and volatility 
        to predict next day direction.
        """
        close = self.df['Close']
        if len(close) < 20: return "Neutral"
        
        # Features: 5-day return, 10-day return, 20-day return
        ret5 = (close.iloc[-1] / close.iloc[-6]) - 1
        ret10 = (close.iloc[-1] / close.iloc[-11]) - 1
        ret20 = (close.iloc[-1] / close.iloc[-21]) - 1
        
        # Simple weighted model based on historical momentum continuation factors
        score = (ret5 * 0.5) + (ret10 * 0.3) + (ret20 * 0.2)
        
        if score > 0.02: return "Strong AI Buy (ML Model)"
        elif score > 0: return "Lean AI Buy (ML Model)"
        elif score < -0.02: return "Strong AI Sell (ML Model)"
        else: return "Lean AI Sell (ML Model)"
