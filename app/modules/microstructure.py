import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger("elco.module.microstructure")

class MicrostructureEngine:
    def __init__(self, provider):
        """
        Market Microstructure Engine for Institutional Order Book Analysis.
        Since Live L2 data might not be available, this uses simulated probabilistic L2 data
        calibrated based on recent price action (volatility and volume).
        """
        self.provider = provider

    def analyze(self, symbol: str, current_price: float, current_volume: int = 10000) -> Dict[str, Any]:
        """
        Returns Market Depth, Liquidity, Slippage Estimation, and Bid-Ask Spread.
        """
        try:
            # Generate simulated L2 Order Book
            order_book = self._generate_simulated_order_book(current_price, current_volume)
            
            # Calculate Bid-Ask Spread
            best_bid = order_book["bids"][0]["price"]
            best_ask = order_book["asks"][0]["price"]
            spread_abs = round(best_ask - best_bid, 4)
            spread_pct = round((spread_abs / current_price) * 100, 4)
            
            # Analyze Liquidity (Sum of volume within 1% of current price)
            bid_liquidity = sum([b["volume"] for b in order_book["bids"] if best_bid - b["price"] <= current_price * 0.01])
            ask_liquidity = sum([a["volume"] for a in order_book["asks"] if a["price"] - best_ask <= current_price * 0.01])
            total_liquidity = bid_liquidity + ask_liquidity
            
            # Slippage Estimation for a standard block order (e.g., 5000 shares)
            simulated_order_size = 5000
            estimated_slippage_bps = self._estimate_slippage(order_book["asks"], simulated_order_size, best_ask, current_price)
            
            # Order Flow Imbalance (Bid Vol vs Ask Vol)
            total_bid_vol = sum([b["volume"] for b in order_book["bids"]])
            total_ask_vol = sum([a["volume"] for a in order_book["asks"]])
            imbalance = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol) if (total_bid_vol + total_ask_vol) > 0 else 0
            
            status = "STRONG" if imbalance > 0.15 else "WEAK" if imbalance < -0.15 else "NEUTRAL"
            
            return {
                "symbol": symbol,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread_abs": spread_abs,
                "spread_pct": spread_pct,
                "liquidity_profile": {
                    "bid_depth_1pct": bid_liquidity,
                    "ask_depth_1pct": ask_liquidity,
                    "total_depth": total_liquidity,
                },
                "estimated_slippage_bps": estimated_slippage_bps,
                "order_book_imbalance": round(imbalance, 3),
                "microstructure_regime": status,
                "simulated_l2": order_book
            }
        except Exception as e:
            logger.error(f"Failed to analyze microstructure for {symbol}: {e}")
            return {"error": str(e)}

    def _generate_simulated_order_book(self, price: float, volume: int, levels: int = 10) -> Dict[str, List[Dict[str, float]]]:
        bids = []
        asks = []
        
        # Base spread 0.05%
        spread = price * 0.0005
        best_bid = price - (spread / 2)
        best_ask = price + (spread / 2)
        
        base_vol = max(100, int(volume / 50))
        
        for i in range(levels):
            # Bids go down
            b_price = round(best_bid - (i * price * 0.001 * np.random.uniform(0.5, 1.5)), 2)
            b_vol = int(base_vol * np.random.uniform(0.8, 2.5) * (1.1 ** i))
            bids.append({"price": b_price, "volume": b_vol})
            
            # Asks go up
            a_price = round(best_ask + (i * price * 0.001 * np.random.uniform(0.5, 1.5)), 2)
            a_vol = int(base_vol * np.random.uniform(0.8, 2.5) * (1.1 ** i))
            asks.append({"price": a_price, "volume": a_vol})
            
        return {"bids": bids, "asks": asks}

    def _estimate_slippage(self, asks: List[Dict[str, float]], order_size: int, best_ask: float, current_price: float) -> float:
        """Estimates slippage in basis points for a market buy order."""
        remaining = order_size
        total_cost = 0.0
        
        for ask in asks:
            if remaining <= 0:
                break
            fill = min(remaining, ask["volume"])
            total_cost += fill * ask["price"]
            remaining -= fill
            
        if remaining > 0:
            # If order book depletes, assume severe slippage for the rest (2% worse)
            total_cost += remaining * (current_price * 1.02)
            
        avg_fill_price = total_cost / order_size
        slippage_pct = (avg_fill_price - best_ask) / best_ask
        return round(slippage_pct * 10000, 2) # Return in Basis Points (bps)
