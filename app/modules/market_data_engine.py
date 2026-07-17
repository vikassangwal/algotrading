import asyncio
import json
import random
from datetime import datetime
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MarketDataEngine")

class SimulatedMarketDataEngine:
    """
    A simulated WebSocket engine for streaming live ticks and generating OHLC data.
    Uses numpy vectorization for high performance with multiple symbols.
    """
    def __init__(self, symbols=None, update_interval=1.0):
        self.symbols = symbols or [f"TICKER_{i}" for i in range(1, 501)]
        self.num_symbols = len(self.symbols)
        self.update_interval = update_interval
        
        # Initialize prices and OHLC data as numpy arrays for fast vectorization
        self.current_prices = np.round(np.random.uniform(100, 500, self.num_symbols), 2)
        
        self.open = self.current_prices.copy()
        self.high = self.current_prices.copy()
        self.low = self.current_prices.copy()
        self.close = self.current_prices.copy()
        self.volume = np.zeros(self.num_symbols, dtype=int)
        
        self.clients = set()

    def _generate_ticks_bulk(self):
        """Generates random price ticks for all symbols using vectorization."""
        # Random walk: max 0.5% change per tick
        changes = self.current_prices * np.random.uniform(-0.005, 0.005, self.num_symbols)
        new_prices = np.round(self.current_prices + changes, 2)
        self.current_prices = new_prices
        
        # Update OHLC data with the new price
        self.high = np.maximum(self.high, new_prices)
        self.low = np.minimum(self.low, new_prices)
        self.close = new_prices
        self.volume += np.random.randint(10, 500, self.num_symbols)
        
        timestamp = datetime.utcnow().isoformat()
        
        return [
            {
                "type": "tick",
                "symbol": self.symbols[i],
                "price": float(new_prices[i]),
                "timestamp": timestamp
            }
            for i in range(self.num_symbols)
        ]

    def _generate_ohlc_bulk(self):
        """Generates the current OHLC snapshots for all symbols using vectorization."""
        timestamp = datetime.utcnow().isoformat()
        return [
            {
                "type": "ohlc",
                "symbol": self.symbols[i],
                "open": float(self.open[i]),
                "high": float(self.high[i]),
                "low": float(self.low[i]),
                "close": float(self.close[i]),
                "volume": int(self.volume[i]),
                "timestamp": timestamp
            }
            for i in range(self.num_symbols)
        ]

    def _reset_ohlc(self):
        """Resets the OHLC data (e.g. for a new time period)."""
        self.open = self.current_prices.copy()
        self.high = self.current_prices.copy()
        self.low = self.current_prices.copy()
        self.close = self.current_prices.copy()
        self.volume = np.zeros(self.num_symbols, dtype=int)

    async def _stream_data(self, websocket):
        """Streams live ticks and OHLC data to a connected client."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        try:
            ticks_count = 0
            while True:
                ticks = self._generate_ticks_bulk()
                send_ohlc = (ticks_count % 5 == 0)
                
                if send_ohlc:
                    ohlc_list = self._generate_ohlc_bulk()
                
                # Send generated messages. 
                # Sending individually but yielding to the event loop to avoid blocking.
                for i, tick in enumerate(ticks):
                    await websocket.send(json.dumps(tick))
                    if i % 100 == 0:
                        await asyncio.sleep(0)
                    
                if send_ohlc:
                    for i, ohlc in enumerate(ohlc_list):
                        await websocket.send(json.dumps(ohlc))
                        if i % 100 == 0:
                            await asyncio.sleep(0)
                        
                ticks_count += 1
                
                # Reset OHLC periodically to simulate time buckets (e.g., every 60 ticks)
                if ticks_count % 60 == 0:
                    self._reset_ohlc()

                await asyncio.sleep(self.update_interval)
        except Exception as e:
            logger.info(f"Client disconnected or connection error: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client removed. Total clients: {len(self.clients)}")

    async def handle_connection(self, websocket, path="/"):
        """WebSocket connection handler."""
        await self._stream_data(websocket)

    async def start_server(self, host="localhost", port=8765):
        """Starts the WebSocket server."""
        try:
            import websockets
            server = await websockets.serve(self.handle_connection, host, port)
            logger.info(f"Simulated Market Data WebSocket server started on ws://{host}:{port}")
            await server.wait_closed()
        except ImportError:
            logger.error("The 'websockets' library is not installed. Please install it using 'pip install websockets'.")
        except Exception as e:
            logger.error(f"Failed to start server: {e}")

if __name__ == "__main__":
    # Example usage:
    # Run the server on ws://localhost:8765 with ticks generated every 1.0 second.
    engine = SimulatedMarketDataEngine(update_interval=1.0)
    
    try:
        asyncio.run(engine.start_server())
    except KeyboardInterrupt:
        logger.info("Market Data Engine stopped by user.")
