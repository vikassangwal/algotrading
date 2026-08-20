import logging
import os
import json
import time
import requests
from datetime import datetime, timezone
from typing import List

try:
    import pyotp
except ImportError:
    pyotp = None

from dotenv import load_dotenv
load_dotenv()

from .provider import DataProvider, Quote, Candle, OptionChain, NewsItem
from .mock_provider import MockProvider

logger = logging.getLogger("elco.kotak")

class KotakRestClient:
    def __init__(self, access_token: str, mobile_number: str, ucc: str, mpin: str, totp_secret: str):
        self.access_token = access_token
        self.mobile_number = mobile_number
        self.ucc = ucc
        self.mpin = mpin
        self.totp_secret = totp_secret
        self.client = None
        self._logged_in = False
        
    def _generate_totp(self) -> str:
        if not pyotp:
            logger.error("pyotp is not installed.")
            return ""
        if not self.totp_secret:
            logger.error("TOTP secret is missing.")
            return ""
        totp = pyotp.TOTP(self.totp_secret.replace(' ', ''))
        return totp.now()

    def login(self) -> bool:
        try:
            from neo_api_client import NeoAPI
            
            logger.info("Initializing Kotak Neo SDK...")
            self.client = NeoAPI(consumer_key=self.access_token, environment='prod')
            
            totp_code = self._generate_totp()
            resp1 = self.client.totp_login(mobile_number=self.mobile_number, ucc=self.ucc, totp=totp_code)
            
            if isinstance(resp1, dict) and ("Error" in resp1 or "error" in resp1):
                logger.error(f"Kotak TOTP Login failed: {resp1}")
                return False
                
            resp2 = self.client.totp_validate(mpin=self.mpin)
            
            if isinstance(resp2, dict) and ("Error" in resp2 or "error" in resp2):
                logger.error(f"Kotak MPIN Validate failed: {resp2}")
                return False
                
            logger.info("Successfully logged into Kotak Neo via official SDK!")
            self._logged_in = True
            return True
            
        except ImportError:
            logger.error("ERROR: neo_api_client is not installed! Kotak API requires Python 3.10+.")
            logger.error("Please upgrade Python and run: pip install kotakneoapi")
            return False
        except Exception as e:
            logger.error(f"Kotak login exception: {e}")
            return False

    def place_order(self, symbol: str, quantity: int, transaction_type: str, _retry_count=0):
        if not self._logged_in or not self.client:
            logger.error("Cannot place Kotak order: Not logged in or SDK not installed.")
            return None
            
        try:
            ts = symbol.replace("_", "-")
            if not ts.endswith("-EQ"):
                ts = f"{ts}-EQ"
                
            logger.info(f"Sending Kotak Neo order for {ts} {quantity} {transaction_type}...")
            
            resp = self.client.place_order(
                exchange_segment="nse_cm",
                product="MIS",
                price="0",
                order_type="MKT",
                quantity=str(quantity),
                validity="DAY",
                trading_symbol=ts,
                transaction_type="B" if transaction_type.upper() == "BUY" else "S",
                amo="NO",
                disclosed_quantity="0",
                trigger_price="0"
            )
            
            if isinstance(resp, dict):
                order_id = resp.get("nOrdNo") or resp.get("orderId")
                if order_id:
                    logger.info(f"Kotak order placed successfully: {order_id}")
                    return order_id
                else:
                    logger.error(f"Kotak order rejected: {resp}")
                    return None
            else:
                logger.error(f"Unexpected Kotak order response format: {resp}")
                return None
                
        except Exception as e:
            logger.error(f"Kotak order placement failed: {e}")
            return None
            
    def get_fund_limit(self):
        if not self._logged_in or not self.client:
            return None
        try:
            resp = self.client.limits()
            if isinstance(resp, dict) and "data" in resp:
                data = resp["data"]
                margin = data.get("availableMargin", 100000.0)
                return float(margin)
        except Exception as e:
            logger.warning(f"Kotak get_fund_limit failed: {e}")
        return None


class KotakProvider(DataProvider):
    def __init__(self):
        self.fallback = MockProvider(seed=123)
        self._rest_client = None
        self._logged_in = False
        
    @property
    def rest_client(self):
        from ..config import config
        
        # 1. Try to read from Admin Panel (config)
        access_token = config.api_secret
        
        mobile_number = None
        ucc = None
        mpin = None
        totp_secret = None
        
        # We expect the user to put Mobile,UCC,MPIN,TOTP_Secret separated by commas in the API Key box
        if config.api_key and "," in config.api_key:
            parts = [p.strip() for p in config.api_key.split(",")]
            if len(parts) >= 4:
                mobile_number = parts[0]
                ucc = parts[1]
                mpin = parts[2]
                totp_secret = parts[3]
                
        # Fallback to environment variables (never hardcode credentials)
        if not access_token or not mobile_number:
            access_token = os.getenv("KOTAK_ACCESS_TOKEN", "")
            mobile_number = os.getenv("KOTAK_MOBILE", "")
            ucc = os.getenv("KOTAK_UCC", "")
            mpin = os.getenv("KOTAK_MPIN", "")
            totp_secret = os.getenv("KOTAK_TOTP_SECRET", "")
                
        # 2. Fallback to .env
        if not access_token:
            access_token = os.getenv("KOTAK_ACCESS_TOKEN")
        if not mobile_number:
            mobile_number = os.getenv("KOTAK_MOBILE")
            ucc = os.getenv("KOTAK_UCC")
            mpin = os.getenv("KOTAK_MPIN")
            totp_secret = os.getenv("KOTAK_TOTP_SECRET")
        
        if not access_token or not mobile_number:
            return None
        
        # Detect credential changes — reset client if Admin Panel credentials were updated
        if self._rest_client is not None:
            old_key = self._rest_client.access_token
            clean_new = access_token.replace("Bearer ", "").strip()
            clean_old = old_key.replace("Bearer ", "").strip() if old_key else ""
            if clean_new != clean_old:
                logger.info("Kotak credentials changed in Admin Panel. Resetting client...")
                self._rest_client = None
                self._logged_in = False
            
        if self._rest_client is None:
            self._rest_client = KotakRestClient(access_token, mobile_number, ucc, mpin, totp_secret)
            self._logged_in = self._rest_client.login()
        
        # Retry login if previous attempt failed (transient network error, etc.)
        if not self._logged_in:
            logger.info("Kotak not logged in. Retrying login...")
            self._logged_in = self._rest_client.login()
            
        return self._rest_client if self._logged_in else None

    def get_fund_limit(self):
        rc = self.rest_client
        if rc is not None:
            return rc.get_fund_limit()
        return None

    def get_quote(self, symbol: str) -> Quote:
        rc = self.rest_client
        if rc is not None and rc.base_url:
            try:
                # Reuse Dhan's symbol mapper to get NSE token ID
                from .dhan_provider import DhanRestClient
                raw_sym = symbol.upper().replace(".NS", "")
                sec_id = DhanRestClient._load_symbol_map().get(raw_sym)
                
                if sec_id:
                    url = f"{rc.base_url}/script-details/1.0/quotes/neosymbol/nse_cm|{sec_id}/all"
                    headers = {"Authorization": rc.access_token}
                    resp = rc.session.get(url, headers=headers, timeout=5)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        # Top-level response itself might be a list
                        if isinstance(data, list) and len(data) > 0:
                            data = data[0]
                        if not isinstance(data, dict):
                            data = {}
                            
                        # Extract LTP from Kotak response
                        inner = data.get("data", data)
                        if isinstance(inner, list) and len(inner) > 0:
                            inner = inner[0]
                        if not isinstance(inner, dict):
                            inner = {}
                            
                        ltp = inner.get("ltp") or inner.get("lastPrice") or 0.0
                        if float(ltp) > 0:
                            return Quote(
                                symbol=symbol.upper(),
                                ltp=float(ltp),
                                change_pct=0.0,
                                volume=0,
                                ts=datetime.now(timezone.utc)
                            )
            except Exception as e:
                logger.warning(f"Kotak native get_quote failed for {symbol}: {e}")

        # Fallback to yfinance
        try:
            from ..yf_cache import get_safe_quote
            q = get_safe_quote(symbol)
            if q["ltp"] > 0:
                return Quote(
                    symbol=symbol.upper(),
                    ltp=float(q["ltp"]),
                    change_pct=float(q["change_pct"]),
                    volume=int(q["volume"]),
                    ts=datetime.now(timezone.utc)
                )
        except Exception:
            pass
            
        return self.fallback.get_quote(symbol)

    def get_candles(self, symbol: str, timeframe: str, count: int) -> List[Candle]:
        try:
            import yfinance as yf
            interval = "1d" if timeframe == "1d" else "15m"
            ticker = yf.Ticker(symbol if symbol.endswith(".NS") else f"{symbol}.NS")
            df = ticker.history(period="5d", interval=interval)
            if not df.empty:
                df = df.tail(count)
                candles = []
                for idx, row in df.iterrows():
                    candles.append(Candle(
                        ts=idx if isinstance(idx, datetime) else datetime.now(),
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume'])
                    ))
                if candles:
                    return candles
        except Exception:
            pass
            
        return self.fallback.get_candles(symbol, timeframe, count)

    def get_option_chain(self, symbol: str) -> OptionChain:
        return self.fallback.get_option_chain(symbol)

    def get_news(self, limit: int = 5) -> List[NewsItem]:
        return self.fallback.get_news(limit)

    def get_fundamentals(self, symbol: str) -> dict:
        return self.fallback.get_fundamentals(symbol)

    def get_macro_data(self) -> dict:
        return self.fallback.get_macro_data()

    def get_intermarket_data(self) -> dict:
        return self.fallback.get_intermarket_data()

    def get_sector_data(self, sector_name: str) -> dict:
        return self.fallback.get_sector_data(sector_name)

    def get_derivatives_data(self, symbol: str) -> dict:
        return self.fallback.get_derivatives_data(symbol)

    def get_sentiment_data(self, symbol: str) -> dict:
        return self.fallback.get_sentiment_data(symbol)

    def get_quant_data(self, symbol: str) -> dict:
        return {}

    def get_portfolio_data(self) -> dict:
        return self.fallback.get_portfolio_data()
