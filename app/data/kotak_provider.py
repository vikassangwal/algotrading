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
        
        self.view_token = None
        self.view_sid = None
        
        self.session_token = None
        self.session_sid = None
        self.base_url = None
        
        self.session = requests.Session()
        
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
        """Perform 2-step login to get session tokens and baseUrl."""
        if not self.access_token or not self.mobile_number:
            logger.error("Kotak credentials incomplete.")
            return False
            
        try:
            # 1. TOTP Login
            url1 = "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin"
            headers1 = {
                "Authorization": self.access_token,
                "neo-fin-key": "neotradeapi",
                "Content-Type": "application/json"
            }
            payload1 = {
                "mobileNumber": self.mobile_number,
                "ucc": self.ucc,
                "totp": self._generate_totp()
            }
            
            resp1 = self.session.post(url1, headers=headers1, json=payload1, timeout=10)
            if resp1.status_code != 200:
                logger.error(f"Kotak TOTP Login failed: {resp1.status_code} {resp1.text}")
                return False
                
            data1 = resp1.json()
            if "data" not in data1 or "token" not in data1["data"]:
                logger.error(f"Kotak TOTP Login missing token in response.")
                return False
                
            self.view_token = data1["data"]["token"]
            self.view_sid = data1["data"]["sid"]
            
            # 2. MPIN Validate
            url2 = "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate"
            headers2 = {
                "Authorization": self.access_token,
                "neo-fin-key": "neotradeapi",
                "sid": str(self.view_sid),
                "Auth": self.view_token,
                "Content-Type": "application/json"
            }
            payload2 = {
                "mpin": self.mpin
            }
            
            resp2 = self.session.post(url2, headers=headers2, json=payload2, timeout=10)
            if resp2.status_code != 200:
                logger.error(f"Kotak MPIN Validate failed: {resp2.status_code} {resp2.text}")
                return False
                
            data2 = resp2.json()
            if "data" not in data2 or "token" not in data2["data"]:
                logger.error(f"Kotak MPIN Validate missing token.")
                return False
                
            self.session_token = data2["data"]["token"]
            self.session_sid = data2["data"]["sid"]
            
            # Extract baseUrl from response or use fallback
            server_map = data2["data"].get("serverMap", {})
            self.base_url = data2["data"].get("baseUrl")
            if not self.base_url:
                for k, v in server_map.items():
                    if "api-gw" in v or "neo-gw" in v:
                        self.base_url = v
                        break
            if not self.base_url:
                self.base_url = "https://neo-gw.kotaksecurities.com"
                
            logger.info(f"Successfully logged into Kotak Neo! BaseURL: {self.base_url}")
            return True
            
        except Exception as e:
            logger.error(f"Kotak login exception: {e}")
            return False

    def get_fund_limit(self):
        if not self.base_url:
            return None
        url = f"{self.base_url}/orderapi/1.0/quick/user/limits"
        headers = {
            "Authorization": self.access_token, # already has Bearer
            "neo-fin-key": "neotradeapi",
            "Sid": str(self.session_sid),
            "Auth": str(self.session_token),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        body = {"seg": "ALL", "exch": "ALL", "prod": "ALL"}
        try:
            resp = self.session.post(url, headers=headers, data=body, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 503:
                return {"available": "Kotak Margin Servers Offline (503)", "utilized": 0}
            return None
        except Exception as e:
            logger.error(f"Kotak limits API failed: {e}")
            return None

    def place_order(self, symbol, quantity, transaction_type):
        from ..config import config
        if config.paper_mode:
            logger.error("KotakRestClient.place_order called but Paper Mode is ON.")
            return None
            
        if not self.base_url or not self.session_token:
            logger.error("Kotak not logged in. Cannot place order.")
            return None

        ts = f"{symbol}-EQ"
        
        jData = {
            "am": "NO",
            "dq": "0",
            "es": "nse_cm",
            "mp": "0",
            "pc": "MIS",
            "pf": "N",
            "pr": "0",
            "pt": "MKT",
            "qt": str(quantity),
            "rt": "DAY",
            "tp": "0",
            "ts": ts,
            "tt": "B" if transaction_type.upper() == "BUY" else "S"
        }
        
        url = f"{self.base_url}/quick/order/rule/ms/place"
        headers = {
            "Auth": self.session_token,
            "Sid": str(self.session_sid),
            "neo-fin-key": "neotradeapi",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {"jData": json.dumps(jData)}
        
        try:
            resp = self.session.post(url, headers=headers, data=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                if not isinstance(data, dict):
                    data = {}
                    
                inner = data.get("data", data)
                if isinstance(inner, list) and len(inner) > 0:
                    inner = inner[0]
                if isinstance(inner, dict):
                    order_id = inner.get("nOrdNo")
                else:
                    order_id = None
                if order_id:
                    logger.info(f"Kotak LIVE order accepted: {transaction_type} {quantity} {symbol} -> {order_id}")
                    return str(order_id)
            logger.error(f"Kotak order rejected ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Kotak order placement failed: {e}")
            
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
            
        if self._rest_client is None:
            self._rest_client = KotakRestClient(access_token, mobile_number, ucc, mpin, totp_secret)
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
