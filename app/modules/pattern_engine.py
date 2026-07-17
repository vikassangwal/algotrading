import pandas as pd
import numpy as np

class PatternEngine:
    def __init__(self, df: pd.DataFrame, order: int = 5):
        """
        Initialize with a dataframe containing High, Low, Close prices.
        Accepts either capitalized ('High') or lowercase ('high') columns.
        order: Number of points on each side to use for local maxima/minima detection.
        """
        # Normalize to capitalized OHLCV so the rest of the engine works
        # regardless of whether the caller passed lowercase columns.
        rename = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("open", "high", "low", "close", "volume"):
                rename[col] = cl.capitalize()
        self.df = df.rename(columns=rename) if rename else df
        self.order = order
        self.peak_ilocs = []
        self.trough_ilocs = []
        self._find_extrema()

    def _find_extrema(self):
        """Find local maxima and minima without external dependencies like scipy."""
        if 'High' not in self.df.columns or 'Low' not in self.df.columns:
            raise ValueError("DataFrame must contain 'High' and 'Low' columns")

        # Create rolling maximum and minimum
        # A point is a local maximum if it is equal to the rolling max in a window of size 2*order+1
        # centered at the point.
        window = 2 * self.order + 1
        
        rolling_max = self.df['High'].rolling(window=window, center=True).max()
        rolling_min = self.df['Low'].rolling(window=window, center=True).min()
        
        # Find indices where the High is equal to the rolling maximum
        is_peak = (self.df['High'] == rolling_max) & (self.df['High'].notna())
        self.peaks = self.df.index[is_peak].tolist()
        
        # Find indices where the Low is equal to the rolling minimum
        is_trough = (self.df['Low'] == rolling_min) & (self.df['Low'].notna())
        self.troughs = self.df.index[is_trough].tolist()
        
        # Store integer positions as well for easier slicing
        self.peak_ilocs = [self.df.index.get_loc(idx) for idx in self.peaks]
        self.trough_ilocs = [self.df.index.get_loc(idx) for idx in self.troughs]

    def is_head_and_shoulders(self, tolerance: float = 0.02) -> bool:
        """
        Detects a regular Head and Shoulders pattern in the recent peaks.
        """
        if len(self.peak_ilocs) < 3:
            return False

        # Look at the last 3 peaks
        p1, p2, p3 = self.peak_ilocs[-3:]
        h1 = self.df['High'].iloc[p1]
        h2 = self.df['High'].iloc[p2]
        h3 = self.df['High'].iloc[p3]

        # Condition 1: Head is higher than both shoulders
        head_is_highest = h2 > h1 and h2 > h3

        # Condition 2: Shoulders are at roughly the same level
        avg_shoulder = (h1 + h3) / 2
        shoulders_level = abs(h1 - h3) / avg_shoulder <= tolerance

        # We also need 2 troughs between the peaks for the neckline
        troughs_between = [t for t in self.trough_ilocs if p1 < t < p3]
        if len(troughs_between) >= 2:
            t1, t2 = troughs_between[-2:]
            l1 = self.df['Low'].iloc[t1]
            l2 = self.df['Low'].iloc[t2]
            
            # Condition 3: Neckline is relatively horizontal
            avg_neckline = (l1 + l2) / 2
            neckline_level = abs(l1 - l2) / avg_neckline <= tolerance
            
            return head_is_highest and shoulders_level and neckline_level

        return False

    def is_inverse_head_and_shoulders(self, tolerance: float = 0.02) -> bool:
        """
        Detects an Inverse Head and Shoulders pattern in the recent troughs.
        """
        if len(self.trough_ilocs) < 3:
            return False

        # Look at the last 3 troughs
        t1, t2, t3 = self.trough_ilocs[-3:]
        l1 = self.df['Low'].iloc[t1]
        l2 = self.df['Low'].iloc[t2]
        l3 = self.df['Low'].iloc[t3]

        # Condition 1: Head is lower than both shoulders
        head_is_lowest = l2 < l1 and l2 < l3

        # Condition 2: Shoulders are at roughly the same level
        avg_shoulder = (l1 + l3) / 2
        shoulders_level = abs(l1 - l3) / avg_shoulder <= tolerance

        return head_is_lowest and shoulders_level

    def is_double_top(self, tolerance: float = 0.015) -> bool:
        """
        Detects a Double Top pattern in the recent peaks.
        """
        if len(self.peak_ilocs) < 2:
            return False
            
        p1, p2 = self.peak_ilocs[-2:]
        h1 = self.df['High'].iloc[p1]
        h2 = self.df['High'].iloc[p2]
        
        # Condition 1: Peaks are at roughly the same level
        avg_peak = (h1 + h2) / 2
        peaks_level = abs(h1 - h2) / avg_peak <= tolerance
        
        # Condition 2: There is a significant trough between them
        troughs_between = [t for t in self.trough_ilocs if p1 < t < p2]
        if len(troughs_between) > 0:
            t_mid = troughs_between[0]
            l_mid = self.df['Low'].iloc[t_mid]
            
            # Drop should be significant (e.g., at least 2% below the peaks)
            significant_drop = l_mid < avg_peak * (1 - 0.02)
            
            return peaks_level and significant_drop
            
        return False

    def is_double_bottom(self, tolerance: float = 0.015) -> bool:
        """
        Detects a Double Bottom pattern in the recent troughs.
        """
        if len(self.trough_ilocs) < 2:
            return False
            
        t1, t2 = self.trough_ilocs[-2:]
        l1 = self.df['Low'].iloc[t1]
        l2 = self.df['Low'].iloc[t2]
        
        # Condition 1: Troughs are at roughly the same level
        avg_trough = (l1 + l2) / 2
        troughs_level = abs(l1 - l2) / avg_trough <= tolerance
        
        # Condition 2: There is a significant peak between them
        peaks_between = [p for p in self.peak_ilocs if t1 < p < t2]
        if len(peaks_between) > 0:
            p_mid = peaks_between[0]
            h_mid = self.df['High'].iloc[p_mid]
            
            # Rise should be significant (e.g., at least 2% above the troughs)
            significant_rise = h_mid > avg_trough * (1 + 0.02)
            
            return troughs_level and significant_rise
            
        return False

    def is_triangle(self, min_points: int = 3) -> str:
        """
        Detects triangle patterns (Ascending, Descending, Symmetrical).
        Returns the name of the pattern or None.
        """
        if len(self.peak_ilocs) < min_points or len(self.trough_ilocs) < min_points:
            return None
            
        # Get recent peaks and troughs
        recent_peaks = self.peak_ilocs[-min_points:]
        recent_troughs = self.trough_ilocs[-min_points:]
        
        peak_prices = self.df['High'].iloc[recent_peaks].values
        trough_prices = self.df['Low'].iloc[recent_troughs].values
        
        # Calculate slopes of the lines connecting peaks and connecting troughs
        x_peaks = np.arange(len(peak_prices))
        x_troughs = np.arange(len(trough_prices))
        
        peak_slope, _ = np.polyfit(x_peaks, peak_prices, 1)
        trough_slope, _ = np.polyfit(x_troughs, trough_prices, 1)
        
        # Normalize slopes
        try:
            avg_price = np.mean(self.df['Close'].iloc[-min_points * self.order * 2:])
            if avg_price == 0:
                avg_price = 1
        except Exception:
            avg_price = 1
            
        norm_peak_slope = peak_slope / avg_price
        norm_trough_slope = trough_slope / avg_price
        
        slope_tolerance = 0.005 # Almost flat
        
        # Symmetrical Triangle: Lower highs and higher lows
        if norm_peak_slope < -slope_tolerance and norm_trough_slope > slope_tolerance:
            return "Symmetrical Triangle"
            
        # Ascending Triangle: Flat highs and higher lows
        if abs(norm_peak_slope) <= slope_tolerance and norm_trough_slope > slope_tolerance:
            return "Ascending Triangle"
            
        # Descending Triangle: Lower highs and flat lows
        if norm_peak_slope < -slope_tolerance and abs(norm_trough_slope) <= slope_tolerance:
            return "Descending Triangle"
            
        return None

    def is_wedge_or_flag(self, min_points: int = 3) -> str:
        """
        Detects Wedges (Rising/Falling) and Flags/Pennants.
        """
        if len(self.peak_ilocs) < min_points or len(self.trough_ilocs) < min_points:
            return None
            
        recent_peaks = self.peak_ilocs[-min_points:]
        recent_troughs = self.trough_ilocs[-min_points:]
        
        peak_prices = self.df['High'].iloc[recent_peaks].values
        trough_prices = self.df['Low'].iloc[recent_troughs].values
        
        x_peaks = np.arange(len(peak_prices))
        x_troughs = np.arange(len(trough_prices))
        
        peak_slope, _ = np.polyfit(x_peaks, peak_prices, 1)
        trough_slope, _ = np.polyfit(x_troughs, trough_prices, 1)
        
        try:
            avg_price = np.mean(self.df['Close'].iloc[-min_points * self.order * 2:])
            if avg_price == 0: avg_price = 1
        except Exception:
            avg_price = 1
            
        norm_peak_slope = peak_slope / avg_price
        norm_trough_slope = trough_slope / avg_price
        
        # Rising Wedge: Both slopes positive, but trough slope steeper than peak slope
        if norm_peak_slope > 0.002 and norm_trough_slope > 0.002 and norm_trough_slope > norm_peak_slope:
            return "Rising Wedge (Bearish Reversal)"
            
        # Falling Wedge: Both slopes negative, but peak slope steeper than trough slope
        if norm_peak_slope < -0.002 and norm_trough_slope < -0.002 and norm_peak_slope < norm_trough_slope:
            return "Falling Wedge (Bullish Reversal)"
            
        # Bear Flag / Bull Flag Proxy: Parallel channels
        if abs(norm_peak_slope - norm_trough_slope) < 0.002:
            if norm_peak_slope > 0.002:
                return "Bear Flag (Bearish Continuation)"
            elif norm_peak_slope < -0.002:
                return "Bull Flag (Bullish Continuation)"
                
        return None

    def analyze(self):
        """
        Run all pattern detections and return a list of found patterns.
        """
        patterns = []
        if self.is_head_and_shoulders():
            patterns.append("Head and Shoulders")
        if self.is_inverse_head_and_shoulders():
            patterns.append("Inverse Head and Shoulders")
        if self.is_double_top():
            patterns.append("Double Top")
        if self.is_double_bottom():
            patterns.append("Double Bottom")
            
        triangle = self.is_triangle()
        if triangle:
            patterns.append(triangle)
            
        wedge_flag = self.is_wedge_or_flag()
        if wedge_flag:
            patterns.append(wedge_flag)
            
        return patterns
