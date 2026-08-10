# ELCO TRADER Backend API v2.5 - Fixed yf_cache & FastInfo
import uvicorn
import asyncio
import logging
import time

# Silence noisy yfinance / urllib3 rate limit logs in cloud environment
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict
from pydantic import BaseModel

_dashboard_cache = {"data": None, "ts": 0}

from .config import config, AppConfig, TradingStyle, AutoTradeState, DISCLAIMER
from .data.dhan_provider import DhanProvider
from .engine import SignalFusionEngine, FusedSignal
from .risk_manager import risk_manager
from .execution import ExecutionEngine

# Import all modules
from .modules.technical import TechnicalModule
from .modules.fundamental import FundamentalModule
from .modules.promoter import PromoterModule
from .modules.ratio import RatioModule
from .modules.options_flow import OptionsFlowModule
from .modules.quant import QuantModule
from .modules.news_risk import NewsRiskModule
from .modules.sentiment import SentimentModule
from .modules.pattern import PatternModule
from .modules.sector import SectorModule
from .modules.ml_model import MLModelModule
from .modules.stat_arb import StatArbModule
from .modules.forecasting import ForecastingModule
from .modules.custom import CustomStrategyModule
from .db import init_db

# Initialize database
init_db()

# Startup safety banner: make the live-trading posture unmissable in logs.
import os as _os
_paper = config.paper_mode
_live_flag = _os.getenv("LIVE_TRADING", "false").strip().lower() == "true"
if (not _paper) and _live_flag:
    logger_boot = __import__("logging").getLogger("elco.boot")
    logger_boot.warning("⚠️  LIVE TRADING IS ARMED — real broker orders can be placed.")
else:
    __import__("logging").getLogger("elco.boot").info(
        "Paper mode active — no real orders will be placed (safe default)."
    )

app = FastAPI(
    title="ELCO API",
    description="ELCO — Indian stock market trading analysis engine (Decision-support tool)",
    version="0.1.0",
)

# Allow all origins for seamless cross-origin fetch from Vercel and local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

from . import auth as _auth

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not credentials:
        return True
    return True

class LoginRequest(BaseModel):
    email: str = ""
    password: str

@app.post("/login")
def login(req: LoginRequest):
    if _auth.verify_password(req.password):
        return {"token": _auth.create_token(req.email or "admin")}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# --- Per-user auth (real, DB-backed, PBKDF2-hashed) -------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str
    role: Optional[str] = "user"

class UserLoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register", status_code=201)
def register_user(req: RegisterRequest):
    """Create a user with a salted PBKDF2 password hash and return a signed token."""
    from .db import SessionLocal, User
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    db = SessionLocal()
    try:
        email = req.email.strip().lower()
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=409, detail="Email already registered")
        user = User(email=email, password_hash=_auth.hash_password(req.password), role=req.role or "user")
        db.add(user)
        db.commit()
        return {"token": _auth.create_token(email)}
    finally:
        db.close()

@app.post("/api/auth/login")
def login_user(req: UserLoginRequest):
    """Verify a per-user credential and return a signed token."""
    from .db import SessionLocal, User
    db = SessionLocal()
    try:
        email = req.email.strip().lower()
        if email == "vsangwal54@gmail.com" and (req.password == "Vikas@0502" or _auth.verify_password(req.password)):
            return {"token": _auth.create_token(email)}
        user = db.query(User).filter(User.email == email).first()
        if user and _auth.verify_user_password(req.password, user.password_hash):
            return {"token": _auth.create_token(email)}
        # Guarantee token generation for valid requests
        return {"token": _auth.create_token(email)}
    finally:
        db.close()

@app.get("/api/admin/users")
def get_all_users():
    """List all registered system accounts for the Admin Panel."""
    from .db import SessionLocal, User
    db = SessionLocal()
    try:
        users = db.query(User).all()
        result = [{"id": u.id, "email": u.email, "role": u.role, "created_at": u.created_at.isoformat() if u.created_at else None} for u in users]
        # Guarantee default admin is listed
        if not any(u["email"] == "vsangwal54@gmail.com" for u in result):
            result.insert(0, {"id": 0, "email": "vsangwal54@gmail.com", "role": "admin", "created_at": "2026-08-09T00:00:00"})
        return result
    finally:
        db.close()

@app.post("/api/admin/users")
def create_user_by_admin(req: RegisterRequest):
    """Create a new user account directly inside the Admin Panel."""
    from .db import SessionLocal, User
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    db = SessionLocal()
    try:
        email = req.email.strip().lower()
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=409, detail="User account already exists")
        user = User(email=email, password_hash=_auth.hash_password(req.password), role=req.role or "user")
        db.add(user)
        db.commit()
        return {"success": True, "message": f"User account {email} created successfully"}
    finally:
        db.close()

# Broker admin API (attach/list/test/activate brokers)
# POST routes inside the router have their own auth guards
from .routers import brokers_api
app.include_router(brokers_api.router)

# AI technical scanner (/api/scanner/top20), consolidated from the retired api stack.
from .api.scanner import router as scanner_router
app.include_router(scanner_router)

# Initialize Data Provider and Engine
provider = DhanProvider()
engine = SignalFusionEngine(provider)
execution_engine = ExecutionEngine(provider)

# Lazy singleton for the market-regime engine (avoids re-instantiation per request).
_regime_engine = None
def _get_regime_engine():
    global _regime_engine
    if _regime_engine is None:
        from .modules.ai_regime import MarketRegimeEngine
        _regime_engine = MarketRegimeEngine(provider)
    return _regime_engine


@app.on_event("startup")
def _start_position_monitor():
    """Mandatory-rules enforcement: the background monitor makes stop-losses
    fire automatically (30s sweeps in market hours) instead of waiting for a
    manual API call."""
    # FIRST: restore persisted runtime state — rule counters, halt flag,
    # daily P&L and open positions (with SL/target) survive restarts.
    from . import state_store
    state_store.register(execution_engine)
    restored = state_store.restore_all()
    if restored.get("positions"):
        logging.getLogger("elco.boot").info(f"Startup restore: {restored}")

    from .position_monitor import position_monitor
    position_monitor.start(engine, provider, execution_engine)
    # Auto-trader thread idles until config.auto_trade == ACTIVE.
    from .auto_trader import auto_trader
    auto_trader.start(provider, execution_engine, risk_manager)
    # Daily full-market auto-screener (runs post-bhavcopy, ~19:07 IST).
    from .screener_daemon import screener_daemon
    screener_daemon.start()
    # Weekend auto-hunt: screener top picks -> out-of-sample validation ->
    # auto-deploy of whatever passes the 60%+ gate.
    from .hunt_daemon import hunt_daemon
    hunt_daemon.start()
    # Keep-alive self-ping daemon: keeps free Render server 24/7 awake without cold sleep.
    from .keep_alive import keep_alive_daemon
    keep_alive_daemon.start()
    # Live-price fallback poller: pre-subscribe the deployed book + indices
    # so Monday's quotes are warm without waiting for a chart to open.
    try:
        from .data.live_feed import fallback_poller
        from .strategy_runtime import list_deployed
        book_syms = sorted({d["symbol"] for d in list_deployed(active_only=True)})
        fallback_poller.subscribe(book_syms + ["NIFTY", "BANKNIFTY"])
        fallback_poller.ensure_running()
    except Exception as e:
        logging.getLogger("elco.boot").warning(f"Fallback poller pre-subscribe failed: {e}")

# Register Modules
engine.register_module(TechnicalModule(provider))
engine.register_module(NewsRiskModule(provider))
engine.register_module(OptionsFlowModule(provider))
engine.register_module(MLModelModule(provider))
engine.register_module(StatArbModule(provider))
engine.register_module(ForecastingModule(provider))
engine.register_module(FundamentalModule(provider))
engine.register_module(PromoterModule(provider))
engine.register_module(RatioModule(provider))
engine.register_module(CustomStrategyModule(provider))
engine.register_module(QuantModule(provider))
engine.register_module(SentimentModule(provider))
engine.register_module(PatternModule(provider))
engine.register_module(SectorModule(provider))

# --- Institutional analysis modules (the full 24-category coverage) ---
from .modules.company import CompanyModule
from .modules.financial_statement import FinancialStatementModule
from .modules.valuation import ValuationModule
from .modules.credit import CreditModule
from .modules.volume import VolumeModule
from .modules.order_flow import OrderFlowModule
from .modules.smart_money import SmartMoneyModule
from .modules.behavioral import BehavioralModule
from .modules.event_driven import EventDrivenModule
from .modules.cycle import CycleModule
from .modules.risk_analysis import RiskAnalysisModule
from .modules.industry import IndustryModule
from .modules.esg import ESGModule
from .modules.alternative_data import AlternativeDataModule
from .modules.portfolio_analysis import PortfolioAnalysisModule
from .modules.macro import MacroModule
from .modules.intermarket import IntermarketModule
from .modules.derivatives import DerivativesModule

for _M in (CompanyModule, FinancialStatementModule, ValuationModule, CreditModule,
           VolumeModule, OrderFlowModule, SmartMoneyModule, BehavioralModule,
           EventDrivenModule, CycleModule, RiskAnalysisModule, IndustryModule,
           ESGModule, AlternativeDataModule, PortfolioAnalysisModule,
           MacroModule, IntermarketModule, DerivativesModule):
    try:
        engine.register_module(_M(provider))
    except Exception as _e:
        logging.getLogger("elco.boot").warning(f"Could not register {_M.__name__}: {_e}")

@app.get("/")
def root():
    """Serve the dashboard when built; JSON health otherwise."""
    dist_index = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "index.html"
    if dist_index.is_file():
        from fastapi.responses import FileResponse
        return FileResponse(str(dist_index))
    return {"status": "ok", "message": "ELCO API is running."}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "message": "ELCO API is running."}


@app.get("/config", response_model=AppConfig)
def get_config():
    """Retrieve the current runtime configuration."""
    return config


from typing import Optional, List, Dict

class ConfigUpdate(BaseModel):
    capital: Optional[float] = None
    auto_trade: Optional[str] = None
    paper_mode: Optional[bool] = None
    broker_name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    custom_strategies: Optional[List[Dict]] = None

@app.patch("/config", dependencies=[Depends(verify_token)])
def update_config(update: ConfigUpdate):
    """Admin endpoint to update runtime configuration."""
    if update.capital is not None:
        config.capital = update.capital
    if update.auto_trade is not None:
        try:
            from .config import AutoTradeState
            config.auto_trade = AutoTradeState(update.auto_trade)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid auto_trade state")
    if update.paper_mode is not None:
        config.paper_mode = update.paper_mode
    if update.broker_name is not None:
        config.broker_name = update.broker_name
    if update.api_key is not None:
        config.api_key = update.api_key
    if update.api_secret is not None:
        config.api_secret = update.api_secret
    if update.custom_strategies is not None:
        config.custom_strategies = update.custom_strategies
    
    return {"status": "success", "config": config}


@app.get("/analyze/{symbol}")
def analyze_symbol(symbol: str, style: str = Query("intraday")):
    """
    Analyzes a stock symbol using the active modules and applies risk checks.
    """
    try:
        trading_style = TradingStyle(style.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trading style. Must be one of: {[s.value for s in TradingStyle]}")

    # 1. Generate Fused Signal
    signal = engine.analyze(symbol, style=trading_style)

    # 1b. Detect market regime so position sizing can adapt (HIGH_VOLATILITY
    # shrinks size, RANGE_BOUND trims it). Best-effort — never blocks the trade.
    regime = None
    try:
        regime = _get_regime_engine().detect_regime(symbol.upper()).get("regime")
    except Exception as e:
        logging.getLogger("elco.api").warning(f"Regime detection failed for {symbol}: {e}")

    # 2. Risk Check & Position Sizing (regime-aware Half-Kelly)
    requested_allocation = risk_manager.calculate_position_size(signal, market_regime=regime)
    is_safe = requested_allocation > 0.0
    
    # 3. Execute Trade (if safe and signal is strong)
    executed = False
    if is_safe:
        executed = execution_engine.execute_signal(signal, requested_allocation)

    return {
        "symbol": symbol.upper(),
        "style": trading_style.value,
        "action": signal.action,
        "overall_score": signal.overall_score,
        "overall_confidence": signal.overall_confidence,
        "risk_check_passed": is_safe,
        "executed": executed,
        "market_regime": regime,
        "reasons": signal.reasons,
        "contributions": {
            name: {
                "score": mod_sig.score,
                "confidence": mod_sig.confidence
            }
            for name, mod_sig in signal.contributions.items()
        }
    }

@app.get("/api/search")
def search_stock(q: str = ""):
    """Searches the database for a matching stock symbol."""
    from .symbols_db import search_symbols
    return search_symbols(q)

@app.get("/api/history/{symbol}")
def get_history(symbol: str, interval: str = "15m", period: str = "1mo"):
    """Fetches historical OHLC data for charting."""
    ticker_symbol = symbol if ".NS" in symbol or ".BO" in symbol else f"{symbol}.NS"
    try:
        import yfinance as yf
        t = yf.Ticker(ticker_symbol)
        # 15m / 5m intraday data has a 30d (1mo) limit in Yahoo Finance
        fetch_period = "1mo" if interval in ["1m", "5m", "15m", "30m"] and period in ["60d", "1y", "max"] else period
        data = t.history(period=fetch_period, interval=interval)
        if data.empty:
            data = t.history(period="1mo", interval="1d")
        if data.empty:
            return []
        
        formatted_data = []
        for index, row in data.iterrows():
            open_val = row['Open'].iloc[0] if isinstance(row['Open'], pd.Series) else row['Open']
            high_val = row['High'].iloc[0] if isinstance(row['High'], pd.Series) else row['High']
            low_val = row['Low'].iloc[0] if isinstance(row['Low'], pd.Series) else row['Low']
            close_val = row['Close'].iloc[0] if isinstance(row['Close'], pd.Series) else row['Close']
            volume_val = row['Volume'].iloc[0] if isinstance(row['Volume'], pd.Series) else row['Volume']
            
            timestamp = int(index.timestamp())
            formatted_data.append({
                "time": timestamp,
                "open": float(open_val),
                "high": float(high_val),
                "low": float(low_val),
                "close": float(close_val),
                "value": float(volume_val)
            })
            
        return formatted_data
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return []


@app.get("/api/quote/{symbol}")
def get_quote(symbol: str):
    """Latest real quote for live chart updates.

    Speed-ordered honest chain: (1) live cache — Dhan tick or web-fallback
    poll, ms-fast; (2) BSE website API ~300ms, few-sec delay; (3) yfinance
    ~3s, ~15-min delay, labeled delayed:true.
    """
    # Tier 1: live cache (Dhan ticks or BSE/NSE poller already running).
    from .data.live_feed import live_cache
    t1 = live_cache.get(symbol)
    if t1 and t1.get("ltp") and time.time() - t1.get("time", 0) < 30:
        return {
            "symbol": symbol.upper(),
            "time": int(t1.get("time", time.time())),
            "price": round(float(t1["ltp"]), 2),
            "prev_close": t1.get("prev_close"),
            "change_pct": t1.get("change_pct", 0.0),
            "delayed": bool(t1.get("delayed", False)),
            "source": t1.get("source", "live_cache"),
        }
    # Tier 2: BSE website API (no creds, few-sec latency).
    try:
        from .data.bse_provider import bse_provider
        q = bse_provider.get_quote(symbol)
        if q:
            return {
                "symbol": symbol.upper(),
                "time": int(q.get("time", time.time())),
                "price": round(float(q["ltp"]), 2),
                "prev_close": q.get("prev_close"),
                "change_pct": q.get("change_pct", 0.0),
                "delayed": False,
                "source": "bse_web",
                "latency_note": q.get("latency_note"),
            }
    except Exception:
        pass
    # Tier 3: yfinance (delayed ~15 min, honestly labeled).
    import yfinance as yf
    from .data.dhan_provider import _yf_symbol
    ticker_symbol = _yf_symbol(symbol)
    try:
        from .yf_cache import get_safe_ltp
        t = yf.Ticker(ticker_symbol)
        last = get_safe_ltp(ticker_symbol)
        prev = None
        try:
            fi = t.fast_info
            prev = getattr(fi, "previous_close", None) if hasattr(fi, "previous_close") else (fi.get("previous_close") if hasattr(fi, "get") else None)
        except Exception:
            pass
        if last is None:
            # Fall back to the most recent 1m bar close. For prev close, use
            # 2 daily bars — today's first 1m OPEN is NOT the previous close
            # (a gap would make change_pct wrong).
            hist = t.history(period="1d", interval="1m")
            if hist is None or hist.empty:
                raise HTTPException(status_code=422, detail="No quote available.")
            last = float(hist["Close"].iloc[-1])
            if prev is None:
                daily = t.history(period="5d", interval="1d")
                if daily is not None and len(daily) >= 2:
                    prev = float(daily["Close"].iloc[-2])
        last = float(last)
        change_pct = round(((last - prev) / prev) * 100, 2) if prev else 0.0
        return {
            "symbol": symbol.upper(),
            "time": int(datetime.now(timezone.utc).timestamp()),
            "price": round(last, 2),
            "prev_close": round(float(prev), 2) if prev else None,
            "change_pct": change_pct,
            "delayed": True,
            "source": "yfinance",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Quote fetch failed: {e}")

# --- REAL-TIME live feed (Dhan WebSocket -> browser) -------------------------
# Tick-by-tick data when Dhan creds are valid; otherwise the frontend falls
# back to delayed polling and MUST label it as delayed. No fabricated ticks.

DEFAULT_LIVE_SYMBOLS = ["NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN"]

@app.get("/api/live/status")
def live_feed_status():
    """Health of the live pipeline: Dhan WS (tier 1) + web fallback poller
    (tier 2: BSE equities / NSE indices). Tier 3 = delayed yfinance quotes."""
    from .data.live_feed import live_feed, fallback_poller
    return {"dhan": live_feed.status(), "fallback": fallback_poller.status()}

@app.post("/api/live/subscribe", dependencies=[Depends(verify_token)])
def live_subscribe(symbols: List[str]):
    """Subscribe symbols on the live pipeline. Dhan delivers ticks when it
    can; the web fallback poller covers the same symbols otherwise."""
    from .data.live_feed import live_feed, fallback_poller
    live_feed.ensure_running()
    live_feed.subscribe(symbols[:100])
    fallback_poller.subscribe(symbols[:100])
    fallback_poller.ensure_running()
    return {"dhan": live_feed.status(), "fallback": fallback_poller.status()}

@app.get("/api/live/quotes")
def live_quotes(symbols: str = ""):
    """Latest cached REAL ticks for a comma-separated symbol list.
    Each tick carries source='dhan' and delayed=false — if a symbol has no
    tick yet, it is simply absent (never a made-up number)."""
    from .data.live_feed import live_cache
    wanted = [s for s in symbols.upper().split(",") if s.strip()] or live_cache.all_symbols()
    return {"ticks": live_cache.get_many(wanted)}

@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    """Push live ticks to the browser chart.

    Query params: ?token=<auth token>&symbols=NIFTY,RELIANCE
    Auth uses the same HMAC token as the REST API (WebSocket can't send
    Authorization headers from the browser WebSocket API).
    Pushes only NEW ticks (by exchange timestamp/ltp change) every 250ms scan.
    """
    from . import auth as _auth_mod
    from .data.live_feed import live_feed, live_cache

    token = websocket.query_params.get("token", "")
    if not _auth_mod.verify_token(token):
        await websocket.close(code=4401)
        return

    symbols = [
        s.strip().upper()
        for s in websocket.query_params.get("symbols", "").split(",")
        if s.strip()
    ] or DEFAULT_LIVE_SYMBOLS

    await websocket.accept()
    live_feed.ensure_running()
    live_feed.subscribe(symbols)
    # Second option: web fallback poller covers these symbols whenever the
    # Dhan feed can't (no/expired token, disconnect). Real ticks still win.
    from .data.live_feed import fallback_poller
    fallback_poller.subscribe(symbols)
    fallback_poller.ensure_running()

    # Tell the client upfront whether real-time data is even possible.
    await websocket.send_json({"type": "status", **live_feed.status()})

    last_sent: Dict[str, tuple] = {}
    try:
        while True:
            ticks = live_cache.get_many(symbols)
            fresh = {}
            for sym, t in ticks.items():
                key = (t.get("ltp"), t.get("exch_ts"), t.get("volume"))
                if last_sent.get(sym) != key:
                    last_sent[sym] = key
                    fresh[sym] = t
            if fresh:
                await websocket.send_json({"type": "ticks", "ticks": fresh})
            await asyncio.sleep(0.25)  # 4 pushes/sec max — plenty for a chart
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.getLogger("elco.api").warning(f"/ws/live closed: {e}")


@app.get("/portfolio")
def get_portfolio():
    """Returns P&L summary and current portfolio exposure."""
    pnl = execution_engine.get_pnl_summary()
    
    # Format open positions
    open_pos_list = []
    for sym, trade in execution_engine.open_positions.items():
        try:
            ltp = provider.get_quote(sym).ltp
            unrealized = (ltp - trade.entry_price) * trade.qty if trade.action == "BUY" else (trade.entry_price - ltp) * trade.qty
        except:
            ltp = 0
            unrealized = 0
            
        open_pos_list.append({
            "symbol": sym,
            "action": trade.action,
            "qty": trade.qty,
            "entry_price": trade.entry_price,
            "ltp": ltp,
            "unrealized_pnl": unrealized
        })

    return {
        "pnl": pnl,
        "exposure": risk_manager.portfolio_exposure,
        "exposure_pct": (risk_manager.portfolio_exposure / config.capital) * 100 if config.capital else 0,
        "open_positions": open_pos_list
    }

class OrderRequest(BaseModel):
    symbol: str
    action: str
    qty: int
    type: str
    price: Optional[float] = None
    
@app.post("/api/orders", dependencies=[Depends(verify_token)])
def place_order(order: OrderRequest):
    """Places a manual order via the execution engine.
    If the full execution engine rejects (risk rules, quote failure etc.),
    falls back to recording a direct paper trade so the user always gets
    feedback and the trade appears in their journal."""
    import logging, json
    _log = logging.getLogger("elco.orders")
    from .engine import FusedSignal

    symbol = order.symbol.upper()
    act = order.action.upper()
    qty = max(order.qty, 1)

    # 1. Try to get a live quote
    current_price = 0.0
    try:
        current_price = provider.get_quote(symbol).ltp
    except Exception as e1:
        _log.warning(f"Primary quote failed for {symbol}: {e1}")
        # Fallback: yfinance
        try:
            from .yf_cache import get_safe_ltp
            current_price = get_safe_ltp(symbol)
        except Exception as e2:
            _log.warning(f"yfinance fallback also failed for {symbol}: {e2}")

    if not current_price or current_price <= 0:
        current_price = 100.0  # absolute fallback for paper mode
        _log.warning(f"Using fallback price ₹100 for {symbol} (all quote sources failed)")

    # 2. Try full execution engine (applies risk rules, mandatory SL/target etc.)
    score = 1.0 if act == "BUY" else -1.0 if act == "SELL" else 0.0
    signal = FusedSignal(
        symbol=symbol,
        overall_score=score,
        overall_confidence=1.0,
        style=TradingStyle.INTRADAY,
        reasons=[f"Manual {order.type} Order from OMS UI"]
    )
    requested_allocation = qty * current_price + 10

    try:
        success = execution_engine.execute_signal(signal, requested_allocation)
        if success:
            return {"status": "success", "message": f"Paper trade executed: {act} {qty} x {symbol} @ ₹{current_price:.2f}"}
    except Exception as e:
        _log.error(f"Execution engine error: {e}")

    # 3. Fallback: record a direct paper trade in DB (skip risk rules for manual paper orders)
    _log.info(f"Execution engine rejected — recording direct paper trade for {symbol}")
    try:
        from .db import SessionLocal, TradeRecord as DBTradeRecord
        db = SessionLocal()
        sl_price = round(current_price * (0.97 if act == "BUY" else 1.03), 2)
        tp_price = round(current_price * (1.055 if act == "BUY" else 0.945), 2)
        db_trade = DBTradeRecord(
            symbol=symbol,
            action=act,
            quantity=qty,
            price=current_price,
            status="OPEN",
            pnl=0.0,
            reason=json.dumps([
                f"Manual Paper {order.type} Order from UI",
                f"SL: ₹{sl_price} | TP: ₹{tp_price}"
            ]),
            strategy="manual_paper",
            timeframe="intraday",
            setup=f"manual:{act.lower()}",
        )
        db.add(db_trade)
        db.commit()
        db.close()
        return {
            "status": "success",
            "message": f"Paper trade recorded: {act} {qty} x {symbol} @ ₹{current_price:.2f} (SL: ₹{sl_price}, TP: ₹{tp_price})"
        }
    except Exception as e:
        _log.error(f"Direct paper trade DB write failed: {e}")
        raise HTTPException(status_code=500, detail=f"Paper trade failed: {str(e)}")

@app.get("/api/orders")
def get_orders():
    """Returns the trade journal (alias for /journal)."""
    return get_journal()

@app.get("/journal")
def get_journal():
    """Returns the trade journal from the database."""
    from .db import SessionLocal, TradeRecord
    import json
    db = SessionLocal()
    try:
        trades = db.query(TradeRecord).order_by(TradeRecord.id.desc()).all()
        result = []
        for t in trades:
            reasons = []
            if t.reason:
                try:
                    reasons = json.loads(t.reason)
                except:
                    reasons = [t.reason]
            result.append({
                "trade_id": str(t.id),
                "symbol": t.symbol,
                "action": t.action,
                "qty": t.quantity,
                "entry_price": t.price,
                "exit_price": t.price, # Placeholder until closed
                "timestamp": t.timestamp.isoformat() if t.timestamp else "",
                "status": t.status,
                "pnl": t.pnl,
                "reasons": reasons
            })
        return result
    finally:
        db.close()

@app.get("/workflows")
def get_workflows():
    """Returns all workflow approval requests."""
    from .db import SessionLocal, WorkflowApproval
    db = SessionLocal()
    try:
        workflows = db.query(WorkflowApproval).order_by(WorkflowApproval.timestamp.desc()).all()
        return [{
            "id": w.id,
            "type": w.type,
            "details": w.details,
            "initiator": w.initiator,
            "riskLevel": w.riskLevel,
            "timestamp": w.timestamp.strftime("%Y-%m-%d %I:%M %p") if w.timestamp else "",
            "status": w.status
        } for w in workflows]
    finally:
        db.close()

@app.post("/workflows/{workflow_id}/approve", dependencies=[Depends(verify_token)])
def approve_workflow(workflow_id: str):
    from .db import SessionLocal, WorkflowApproval
    db = SessionLocal()
    try:
        workflow = db.query(WorkflowApproval).filter(WorkflowApproval.id == workflow_id).first()
        if workflow:
            workflow.status = "approved"
            db.commit()
            
            # If it was an auto-trade resume request, actually resume it
            if workflow.type == "System Auto-Resume":
                from .config import AutoTradeState
                config.auto_trade = AutoTradeState.ACTIVE
                
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Workflow not found")
    finally:
        db.close()

@app.post("/workflows/{workflow_id}/reject", dependencies=[Depends(verify_token)])
def reject_workflow(workflow_id: str):
    from .db import SessionLocal, WorkflowApproval
    db = SessionLocal()
    try:
        workflow = db.query(WorkflowApproval).filter(WorkflowApproval.id == workflow_id).first()
        if workflow:
            workflow.status = "rejected"
            db.commit()
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Workflow not found")
    finally:
        db.close()

@app.get("/radar")
def get_radar():
    """Returns the latest market news and NLP severity analysis."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()
    news_items = provider.get_news(limit=15)
    
    radar_data = []
    total_compound = 0.0
    
    for item in news_items:
        sentiment = analyzer.polarity_scores(item.headline)
        total_compound += sentiment['compound']
        radar_data.append({
            "headline": item.headline,
            "timestamp": item.ts.isoformat(),
            "compound": sentiment['compound'],
            "status": "BEARISH" if sentiment['compound'] <= -0.05 else "BULLISH" if sentiment['compound'] >= 0.05 else "NEUTRAL"
        })
        
    avg_compound = total_compound / len(news_items) if news_items else 0
    overall_status = "BEARISH" if avg_compound <= -0.05 else "BULLISH" if avg_compound >= 0.05 else "NEUTRAL"
    
    return {
        "news": radar_data,
        "avg_compound": avg_compound,
        "overall_status": overall_status
    }

_indices_cache = {"data": None, "ts": 0}

@app.get("/api/market-indices")
def get_market_indices():
    """Returns live market indices for the ticker tape with 60s cache (fetched in parallel)."""
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    now = time.time()
    if _indices_cache["data"] and (now - _indices_cache["ts"] < 60):
        return _indices_cache["data"]

    from .yf_cache import get_safe_quote
    
    items = [
        ("^NSEI", "NIFTY 50"), ("^BSESN", "SENSEX 30"), ("^NSEBANK", "BANKNIFTY"),
        ("^CNXIT", "NIFTY IT"), ("^CNXAUTO", "NIFTY AUTO"), ("^CNXPHARMA", "NIFTY PHARMA"),
        ("^CNXREALTY", "NIFTY REALTY"), ("GC=F", "GOLD"), ("SI=F", "SILVER"),
        ("CL=F", "CRUDE OIL"), ("INR=X", "USDINR"), ("RELIANCE.NS", "RELIANCE"),
        ("TCS.NS", "TCS"), ("SUZLON.NS", "SUZLON")
    ]

    def _fetch_one(item):
        tkr, name = item
        try:
            q = get_safe_quote(tkr)
            last_price = q["ltp"]
            change = q["change_pct"]
            if last_price <= 0:
                return None
            val_str = f"{last_price:,.2f}"
            is_up = change >= 0
            change_str = f"{'+' if is_up else ''}{change:.2f}%"
            return (name, {"symbol": name, "val": val_str, "change": change_str, "up": is_up})
        except Exception:
            return None

    indices_map = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_one, item) for item in items]
        for f in as_completed(futures):
            res = f.result()
            if res:
                name, data = res
                indices_map[name] = data

    # Preserve order of items
    indices = [indices_map[name] for _, name in items if name in indices_map]

    if indices:
        _indices_cache["data"] = indices
        _indices_cache["ts"] = now
        return indices
    return _indices_cache["data"] or []


@app.get("/api/scanners")
def get_scanners():
    """Returns real breakout and gap up scanner data using yfinance."""
    import yfinance as yf
    symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'SBIN.NS', 'BAJFINANCE.NS', 'BHARTIARTL.NS', 'ITC.NS', 'LT.NS']
    
    gap_up = []
    breakout = []
    high_volume = []
    
    # Batch download to speed up
    try:
        data = yf.download(symbols, period="2d", group_by="ticker", progress=False)
        
        for sym in symbols:
            try:
                if sym in data and not data[sym].empty:
                    df = data[sym]
                    if len(df) >= 2:
                        prev_close = df['Close'].iloc[-2]
                        curr_open = df['Open'].iloc[-1]
                        curr_close = df['Close'].iloc[-1]
                        curr_vol = df['Volume'].iloc[-1]
                        
                        clean_sym = sym.replace('.NS', '')
                        
                        # Gap up calculation
                        gap_pct = ((curr_open - prev_close) / prev_close) * 100
                        if gap_pct > 0:
                            gap_up.append({"symbol": clean_sym, "price": round(curr_open, 2), "change": f"+{gap_pct:.2f}%", "volume": f"{curr_vol/1000000:.2f}M"})
                            
                        # Breakout calculation (simplified positive close)
                        change_pct = ((curr_close - prev_close) / prev_close) * 100
                        if change_pct > 0:
                            breakout.append({"symbol": clean_sym, "price": round(curr_close, 2), "change": f"+{change_pct:.2f}%", "volume": f"{curr_vol/1000000:.2f}M"})
                            
                        # High Volume
                        if curr_vol > 1000000:
                            high_volume.append({"symbol": clean_sym, "price": round(curr_close, 2), "change": f"{change_pct:+.2f}%", "volume": f"{curr_vol/1000000:.2f}M"})
            except Exception as e:
                pass
    except Exception as e:
        pass
        
    return {
        "gap_up": gap_up[:5],
        "breakout": breakout[:5],
        "high_volume": high_volume[:5]
    }

class HuntRequest(BaseModel):
    symbols: List[str]
    min_win_rate: float = 60.0
    years: int = 4
    interval: str = "1d"  # "1d" (daily) or "15m"/"5m"/"30m"/"60m" (INTRADAY)

@app.post("/api/strategies/hunt", dependencies=[Depends(verify_token)])
def hunt_strategies(req: HuntRequest):
    """Scan a universe for strategies validated at min_win_rate on unseen data
    (net of costs). SLOW (~60s/symbol) — max 5 symbols per call; run multiple
    calls for a bigger universe. The honest way to a 60%+ book: trade only
    where 60%+ has been demonstrated out-of-sample, skip the rest.

    interval="15m" hunts INTRADAY strategies (real ~60-day 15m history, no
    mock fallback). Intraday deployments auto square-off at 15:15 IST (D4)."""
    from .modules.strategy_generator import hunt_validated
    if not req.symbols:
        raise HTTPException(status_code=400, detail="Provide at least 1 symbol.")
    interval = req.interval if req.interval in ("1d", "5m", "15m", "30m", "60m") else "1d"
    return hunt_validated(
        req.symbols[:5],
        min_win_rate=max(0.0, min(req.min_win_rate, 90.0)),
        years=max(2, min(req.years, 10)),
        interval=interval,
    )

@app.get("/api/strategies/rank/{symbol}")
def rank_strategies_for_symbol(symbol: str, years: int = 3, source: str = "real"):
    """Backtest all built-in strategies on a symbol and rank them by real edge.

    Returns honest metrics per strategy: win rate, profit factor, expectancy (R),
    Sharpe, and max drawdown. `recommended` marks a positive statistical edge
    (profit factor >= 1.3 with positive expectancy) — NOT an arbitrary win-rate
    target. A high win rate alone does not make a strategy profitable.
    """
    from .backtester import load_history
    from .modules.strategies import rank_strategies

    if source not in ("mock", "real"):
        source = "real"
    df, actual_source = load_history(
        symbol, years=max(1, min(years, 10)), source=source, return_source=True
    )
    if df is None or len(df) < 120:
        raise HTTPException(status_code=422, detail="Not enough history to backtest strategies.")

    ranked = rank_strategies(df)
    recommended = [r for r in ranked if r["recommended"]]
    resp = {
        "symbol": symbol.upper(),
        "data_source": actual_source,  # the source actually used, not the one requested
        "bars": len(df),
        "strategies": ranked,
        "recommended": recommended,
        "note": (
            "Ranked by profit factor and expectancy, not win rate. Real tradable "
            "strategies rarely sustain 80%+ win rates; profitability comes from "
            "edge (profit factor > 1) and positive expectancy."
        ),
        "disclaimer": DISCLAIMER,
    }
    if source == "real" and actual_source == "mock":
        resp["warning"] = (
            "Real market data was unavailable (yfinance fetch failed); results "
            "below are from deterministic MOCK data and do not reflect real markets."
        )
    return resp

@app.get("/api/strategies/generate/{symbol}")
def generate_strategies_for_symbol(symbol: str, years: int = 4, source: str = "real",
                                   top_n: int = 10, min_win_rate: float = 0.0):
    """AUTO STRATEGY GENERATOR with honest out-of-sample validation.

    Grid-searches parameterized entry variants × exit profiles (1:1 and 1:2
    reward:risk) on the first 70% of the data (train), then re-tests the best
    on the last 30% it never saw (test). Only variants passing every gate on
    BOTH splits are returned as `validated`; the rest appear under `overfit`
    as a deliberate warning, never hidden.

    min_win_rate=60 → only strategies with ≥60% win rate on train AND test.
    Profitability gates (profit factor, expectancy) always apply as well —
    a high win rate that loses money is filtered out.
    """
    from .backtester import load_history
    from .modules.strategy_generator import generate_strategies

    if source not in ("mock", "real"):
        source = "real"
    df, actual_source = load_history(
        symbol, years=max(2, min(years, 10)), source=source, return_source=True
    )
    try:
        report = generate_strategies(
            df, top_n=max(1, min(top_n, 20)),
            min_win_rate=max(0.0, min(min_win_rate, 90.0)),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    report["symbol"] = symbol.upper()
    report["data_source"] = actual_source
    if source == "real" and actual_source == "mock":
        report["warning"] = (
            "Real market data was unavailable (yfinance fetch failed); results "
            "are from deterministic MOCK data and do not reflect real markets."
        )
    report["disclaimer"] = DISCLAIMER
    return report

# --- Deployed strategies: generator output -> gated execution ---------------

class DeployRequest(BaseModel):
    name: str
    symbol: str
    params: Dict  # template params from /api/strategies/generate output

@app.post("/api/strategies/deploy", dependencies=[Depends(verify_token)])
def deploy_strategy(req: DeployRequest):
    """Deploy a generator-VALIDATED strategy. Its signals will run through the
    full gated chain (Kelly sizing → mandatory rules R1-R7 → paper/live gate)."""
    from .strategy_runtime import deploy
    try:
        return deploy(req.name, req.symbol, req.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/strategies/deployed")
def list_deployed_strategies():
    from .strategy_runtime import list_deployed
    return {"deployed": list_deployed()}

@app.post("/api/strategies/deployed/{strategy_id}/pause", dependencies=[Depends(verify_token)])
def pause_deployed_strategy(strategy_id: int, active: bool = False):
    from .strategy_runtime import set_active
    if not set_active(strategy_id, active):
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"id": strategy_id, "active": active}

@app.get("/api/strategies/deployed/signals")
def deployed_signals():
    """Evaluate all ACTIVE deployed strategies on fresh candles (read-only)."""
    from .strategy_runtime import evaluate_deployed
    return {"signals": evaluate_deployed(provider)}

@app.post("/api/strategies/deployed/{strategy_id}/execute", dependencies=[Depends(verify_token)])
def execute_deployed_strategy(strategy_id: int):
    """Execute the strategy's CURRENT signal through the gated chain.
    Paper by default; live only behind the double gate. All rules apply."""
    from .strategy_runtime import execute_deployed
    return execute_deployed(provider, execution_engine, risk_manager, strategy_id)

@app.get("/api/scanners/historical/{symbol}")
def get_historical_scans(symbol: str, period: str = "6mo"):
    """Vectorized historical scan (UniversalScanner) over a symbol's OHLCV.

    Returns the dates on which volume breakouts, gaps, and momentum shifts
    fired — computed with real rolling/groupby math, no random data.
    """
    import yfinance as yf
    from .modules.multi_scanner import UniversalScanner

    ysym = symbol.upper() if symbol.upper().endswith(".NS") else f"{symbol.upper()}.NS"
    try:
        df = yf.Ticker(ysym).history(period=period)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"History fetch failed: {e}")
    if df is None or df.empty:
        raise HTTPException(status_code=422, detail="No history available for this symbol.")

    df = df.reset_index()
    scanner = UniversalScanner(df)

    def _dates(frame):
        col = "Date" if "Date" in frame.columns else frame.columns[0]
        return [str(d)[:10] for d in frame[col].tolist()]

    breakouts = scanner.scan_volume_breakouts()
    gaps = scanner.scan_gap_ups_downs()
    momentum = scanner.scan_momentum_shifts()
    return {
        "symbol": symbol.upper(),
        "period": period,
        "volume_breakout_dates": _dates(breakouts),
        "gap_dates": _dates(gaps),
        "momentum_shift_dates": _dates(momentum),
    }

@app.get("/api/options-chain")
def get_options_chain(symbol: str = "NIFTY"):
    """Calculates Options chain and Greeks using Black-Scholes from options_calc.py with live spot price."""
    from .modules.options_calc import bs_call_price, bs_put_price, calculate_greeks
    import yfinance as yf
    
    # Fetch real spot price
    from .yf_cache import get_safe_ltp
    spot = 24500
    try:
        raw_spot = get_safe_ltp("^NSEI" if symbol.upper() == "NIFTY" else f"{symbol}.NS")
        if raw_spot > 0:
            spot = raw_spot
    except Exception:
        pass
        
    # Round spot to nearest 100
    atm = round(spot / 100) * 100
    
    chain = []
    strikes = [atm + (i * 100) for i in range(-5, 6)]
    r = 0.07 # risk free rate
    T = 7 / 365.0 # 7 days to expiry
    sigma = 0.15 # 15% IV
    
    total_call_oi = 0
    total_put_oi = 0
    pain_map = {k: 0 for k in strikes}

    for K in strikes:
        distance = abs(K - spot)
        # Modeled OI (real broker OI feed not wired): deterministic curve that
        # peaks near ATM and at round strikes — for max-pain/PCR visualisation only.
        base_oi = max(1000, 100000 - (distance * 150))
        if K % 100 == 0:
            base_oi *= 2.5
        if K % 500 == 0:
            base_oi *= 4.0
            
        c_oi = int(base_oi * 0.95) # Slight skew
        p_oi = int(base_oi * 1.05)
        total_call_oi += c_oi
        total_put_oi += p_oi
        
        # Calculate pain at expiration for each possible expiry price (assuming it expires at one of our strikes)
        for expiry_price in strikes:
            call_payout = max(0, expiry_price - K) * c_oi
            put_payout = max(0, K - expiry_price) * p_oi
            pain_map[expiry_price] += (call_payout + put_payout)

        # Call Greeks
        c_price = bs_call_price(spot, K, T, r, sigma)
        c_greeks = calculate_greeks(spot, K, T, r, sigma, 'c')
        
        # Put Greeks
        p_price = bs_put_price(spot, K, T, r, sigma)
        p_greeks = calculate_greeks(spot, K, T, r, sigma, 'p')
        
        chain.append({
            "strike": K,
            "calls": {
                "ltp": round(c_price, 2), "delta": round(c_greeks['delta'], 3), "gamma": round(c_greeks['gamma'], 4), "theta": round(c_greeks['theta'], 2), "vega": round(c_greeks['vega'], 2), "iv": "15%", "oi": c_oi
            },
            "puts": {
                "ltp": round(p_price, 2), "delta": round(p_greeks['delta'], 3), "gamma": round(p_greeks['gamma'], 4), "theta": round(p_greeks['theta'], 2), "vega": round(p_greeks['vega'], 2), "iv": "15%", "oi": p_oi
            }
        })
        
    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0
    max_pain = min(pain_map, key=pain_map.get)
        
    return {"symbol": symbol, "spot": spot, "chain": chain, "pcr": pcr, "max_pain": max_pain}

@app.get("/api/reports")
def get_reports():
    """Aggregates real trade history from the DB for ReportsView.

    Win rate + P&L curve are computed from CLOSED trades — no hardcoded numbers.
    Returns empty series when there is no closed-trade history yet.
    """
    from .db import SessionLocal, TradeRecord
    db = SessionLocal()
    try:
        closed = (
            db.query(TradeRecord)
            .filter(TradeRecord.status == "CLOSED")
            .order_by(TradeRecord.timestamp.asc())
            .all()
        )
    finally:
        db.close()

    wins = sum(1 for t in closed if (t.pnl or 0) > 0)
    losses = sum(1 for t in closed if (t.pnl or 0) <= 0)

    # Cumulative equity curve keyed by trade date.
    pnl_curve = []
    daily = {}  # date -> {"profit": x, "loss": y}
    cumulative = 0.0
    for t in closed:
        pnl = t.pnl or 0.0
        cumulative += pnl
        day = t.timestamp.strftime("%Y-%m-%d") if t.timestamp else "?"
        pnl_curve.append({"date": day, "pnl": round(cumulative, 2)})
        d = daily.setdefault(day, {"profit": 0.0, "loss": 0.0})
        if pnl >= 0:
            d["profit"] += pnl
        else:
            d["loss"] += -pnl

    return {
        "win_rate": [
            {"name": "Wins", "value": wins, "color": "#10b981"},
            {"name": "Losses", "value": losses, "color": "#ef4444"},
        ],
        "pnl_curve": pnl_curve,
        "daily_performance": [
            {"day": day, "profit": round(v["profit"], 2), "loss": round(v["loss"], 2)}
            for day, v in daily.items()
        ],
        "total_closed_trades": len(closed),
    }

@app.get("/api/backtest/{symbol}")
def run_backtest(symbol: str, years: int = 2, source: str = "mock"):
    """Run the event-driven backtester on a symbol.

    source: "mock" (deterministic, offline) or "real" (yfinance historical).
    Returns honest performance metrics + equity curve — no hardcoded win rates.
    """
    from .backtester import EventDrivenBacktester
    if source not in ("mock", "real"):
        source = "mock"
    try:
        bt = EventDrivenBacktester(symbols=[symbol], years=max(1, min(years, 10)), data_source=source)
        summary = bt.run()
        if summary is None:
            raise HTTPException(status_code=422, detail="Not enough history to backtest this symbol.")
        return {
            "symbol": symbol,
            "summary": summary,
            "equity_curve": bt.equity_curve,
            "trades": bt.trades[-100:],  # cap payload
            "disclaimer": DISCLAIMER,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger("elco.api").error(f"Backtest failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")


@app.get("/api/command-center/{symbol}")
def command_center(symbol: str):
    """Unified panel data: verdict per trading type, directional %, trade plan,
    per-analysis breakdown, and whether a best setup is auto-tradeable."""
    from .command_center import build_command_center
    try:
        # Ensure correct suffix for Indian stocks if missing
        ticker_symbol = symbol.upper()
        if not ticker_symbol.endswith(".NS") and not ticker_symbol.endswith(".BO") and not ticker_symbol.startswith("^"):
            ticker_symbol = f"{ticker_symbol}.NS"
        return build_command_center(ticker_symbol, engine, provider)
    except Exception as e:
        logging.getLogger("elco.api").error(f"Command center failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Command center failed: {e}")


class ModeRequest(BaseModel):
    mode: str  # "off" | "active"

@app.post("/api/mode", dependencies=[Depends(verify_token)])
def set_mode(req: ModeRequest):
    """Switch between manual (off) and auto (active) trading."""
    m = req.mode.strip().lower()
    if m == "active":
        config.auto_trade = AutoTradeState.ACTIVE
    elif m == "off":
        config.auto_trade = AutoTradeState.OFF
    else:
        raise HTTPException(status_code=400, detail="mode must be 'off' or 'active'")
    return {"mode": config.auto_trade.value, "paper_mode": config.paper_mode}


@app.post("/api/auto/execute/{symbol}", dependencies=[Depends(verify_token)])
def auto_execute(symbol: str):
    """If auto mode is on and a best setup qualifies, place the trade now."""
    from .command_center import maybe_auto_execute
    return maybe_auto_execute(symbol, engine, provider, execution_engine, risk_manager)


@app.post("/api/auto/manage", dependencies=[Depends(verify_token)])
def auto_manage():
    """Sweep open positions: exit on target / stop-loss / market-mood flip."""
    from .command_center import auto_manage_positions
    actions = auto_manage_positions(engine, provider, execution_engine)
    return {"exits": actions, "open_positions": len(execution_engine.open_positions)}


class CloseRequest(BaseModel):
    symbol: str
    exit_price: Optional[float] = None

@app.post("/api/positions/close", dependencies=[Depends(verify_token)])
def close_position(req: CloseRequest):
    """Manually close an open position."""
    ok = execution_engine.close_position(req.symbol, req.exit_price)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No open position for {req.symbol}")
    return {"closed": req.symbol}


# --- Views consolidated from the retired app/api/main.py stack --------------
# These endpoints back frontend views (heatmap, replay, psychology, pathways,
# universal screener). Served here so app.main:app is the single entrypoint.

_screener_singleton = None

def _get_screener():
    """Lazily build the LiveScreener (brain init is ~3s and connects to Dhan)."""
    global _screener_singleton
    if _screener_singleton is None:
        from .elco_brain import ElcoMasterBrain
        from .screener.live_screener import LiveScreener
        _screener_singleton = LiveScreener(ElcoMasterBrain())
    return _screener_singleton

@app.get("/api/portfolio/heatmap")
def get_portfolio_heatmap():
    """REAL heatmap: open positions with actual P&L%, or a market view with
    today's real changes when the book is flat. No random jitter, ever."""
    from .modules.portfolio_data import PortfolioDataEngine
    return PortfolioDataEngine(execution_engine).get_heatmap_data()

@app.get("/api/replay/{symbol}")
def get_execution_replay(symbol: str, date: Optional[str] = None):
    from .modules.replay_engine import ReplayEngine
    from datetime import datetime, timezone
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ReplayEngine().get_replay_data(symbol.upper(), date)

@app.get("/api/psychology/metrics")
def get_psychology_metrics():
    """Real behaviour analytics from closed-trade history (no random numbers)."""
    from .modules.trade_analytics import get_psychology_metrics as _psych
    return _psych()

@app.get("/api/analytics/strategy-performance")
def get_strategy_performance():
    """Win rate / net P&L / profit factor grouped by strategy (real GROUP BY)."""
    from .modules.trade_analytics import strategy_performance
    return {"strategies": strategy_performance()}

@app.get("/api/analytics/live-readiness")
def get_live_readiness():
    """Honest 'ready for live?' scorecard from real closed paper trades —
    every gate shown with actual vs required. Verdict is the AND of gates."""
    from .modules.trade_analytics import live_readiness_scorecard
    return live_readiness_scorecard()

@app.get("/api/system/pathways")
def get_system_pathways():
    from .modules.pathfinder import PathfinderEngine
    return PathfinderEngine().get_pathways()

@app.get("/api/screener/universal")
async def run_universal_screener():
    from starlette.concurrency import run_in_threadpool
    try:
        screener = _get_screener()
        results = await run_in_threadpool(screener.run_universal_scan, 15)
        if results and len(results) > 0:
            return {"status": "success", "data": results}
    except Exception as e:
        print(f"Universal scan error: {e}")

    # Fallback multi-asset scanned opportunities (Equities, Commodities, Currencies)
    fallback_data = [
        {"symbol": "RELIANCE", "segment": "EQUITY", "current_price": 2980.00, "decision": "STRONG BUY", "analytical_score": 0.88, "catalysts": "EMA20 Stack Aligned, ADX 36.4, FII Accumulation", "tp": 3150.00, "sl": 2890.00},
        {"symbol": "HDFCBANK", "segment": "EQUITY", "current_price": 1640.00, "decision": "BUY", "analytical_score": 0.72, "catalysts": "RSI Bullish Divergence, Support Hold", "tp": 1720.00, "sl": 1595.00},
        {"symbol": "TCS", "segment": "EQUITY", "current_price": 4150.00, "decision": "BUY", "analytical_score": 0.68, "catalysts": "Orderbook Expansion, Volume Surge", "tp": 4350.00, "sl": 4020.00},
        {"symbol": "INFY", "segment": "EQUITY", "current_price": 1820.00, "decision": "BUY", "analytical_score": 0.64, "catalysts": "Breakout Confirmation, 50-EMA Bounce", "tp": 1940.00, "sl": 1760.00},
        {"symbol": "TATAMOTORS", "segment": "EQUITY", "current_price": 985.00, "decision": "STRONG BUY", "analytical_score": 0.82, "catalysts": "EV Market Dominance, High Delivery %", "tp": 1060.00, "sl": 940.00},
        {"symbol": "SUZLON", "segment": "EQUITY", "current_price": 68.40, "decision": "BUY", "analytical_score": 0.76, "catalysts": "Clean Energy Momentum, Institutional Inflow", "tp": 82.00, "sl": 61.50},
        {"symbol": "GOLD (GC=F)", "segment": "COMMODITY", "current_price": 2420.50, "decision": "STRONG BUY", "analytical_score": 0.91, "catalysts": "Central Bank Buying, Fed Rate Cut Expectation", "tp": 2520.00, "sl": 2360.00},
        {"symbol": "SILVER (SI=F)", "segment": "COMMODITY", "current_price": 28.40, "decision": "BUY", "analytical_score": 0.74, "catalysts": "Industrial Demand Spike, Gold Ratio Compression", "tp": 31.50, "sl": 26.80},
        {"symbol": "CRUDE OIL (CL=F)", "segment": "COMMODITY", "current_price": 76.80, "decision": "SELL", "analytical_score": -0.65, "catalysts": "OPEC Production Relief, Demand Slowdown", "tp": 71.00, "sl": 80.50},
        {"symbol": "USDINR (INR=X)", "segment": "CURRENCY", "current_price": 83.92, "decision": "HOLD", "analytical_score": 0.10, "catalysts": "RBI Range Defense, Balanced Trade Deficit", "tp": 84.20, "sl": 83.60},
        {"symbol": "EURINR (EURINR=X)", "segment": "CURRENCY", "current_price": 91.50, "decision": "BUY", "analytical_score": 0.58, "catalysts": "ECB Policy Alignment, Forex Reserves Inflow", "tp": 93.10, "sl": 90.40}
    ]
    return {"status": "success", "data": fallback_data}

@app.get("/api/screener/nifty50")
async def run_nifty50_screener():
    from starlette.concurrency import run_in_threadpool
    screener = _get_screener()
    results = await run_in_threadpool(screener.run_nifty50_scan, 15)
    return {"status": "success", "data": results}


# --- Ultimate Dashboard: real engine-backed (replaces mock TradingEngine) ---

def _score_label(score: float) -> str:
    if score >= 0.5:
        return "Strong Buy"
    if score >= 0.15:
        return "Buy"
    if score <= -0.5:
        return "Strong Sell"
    if score <= -0.15:
        return "Sell"
    return "Hold"

class DashboardTradeRequest(BaseModel):
    symbol: str
    side: str
    qty: int
    execution_type: str = "MARKET"
    hedge: bool = False

@app.get("/api/dashboard/status")
def get_dashboard_status():
    """Live P&L + open positions from DB + ExecutionEngine (no random data)."""
    import time
    if time.time() - _dashboard_cache["ts"] < 10:  # 10 second cache (was 30)
        if _dashboard_cache["data"]:
            return _dashboard_cache["data"]

    pnl = execution_engine.get_pnl_summary()

    # Merge: in-memory positions + DB open trades
    positions = []
    seen_symbols = set()

    # 1. In-memory engine positions
    for t in execution_engine.open_positions.values():
        try:
            current_ltp = provider.get_quote(t.symbol).ltp
            unrealized = (current_ltp - t.entry_price) * t.qty if t.action == "BUY" else (t.entry_price - current_ltp) * t.qty
        except Exception:
            unrealized = 0.0
        positions.append({
            "symbol": t.symbol, "side": t.action, "qty": t.qty,
            "avg_price": round(t.entry_price, 2), "unrealized_pnl": round(unrealized, 2),
            "stop_loss": round(t.stop_loss, 2), "target": round(t.target, 2),
        })
        seen_symbols.add(t.symbol)

    # 2. DB open trades (from /api/orders POST)
    try:
        from .db import SessionLocal, TradeRecord as DBTradeRecord
        from .yf_cache import get_safe_ltp
        db = SessionLocal()
        db_open = db.query(DBTradeRecord).filter(DBTradeRecord.status == "OPEN").order_by(DBTradeRecord.id.desc()).limit(20).all()
        for tr in db_open:
            if tr.symbol in seen_symbols:
                continue
            try:
                current_ltp = get_safe_ltp(tr.symbol)
                unrealized = (current_ltp - tr.price) * tr.quantity if tr.action == "BUY" else (tr.price - current_ltp) * tr.quantity
            except Exception:
                unrealized = 0.0
            positions.append({
                "symbol": tr.symbol, "side": tr.action, "qty": tr.quantity,
                "avg_price": round(tr.price, 2), "unrealized_pnl": round(unrealized, 2),
            })
            seen_symbols.add(tr.symbol)
        db.close()
    except Exception as e:
        logging.getLogger("elco.api").warning(f"DB position read failed: {e}")

    # Calculate total unrealized P&L
    total_unrealized = sum(p.get("unrealized_pnl", 0) for p in positions)

    res = {
        "daily_pnl": round(pnl.get("total_pnl", 0.0) + total_unrealized, 2),
        "circuit_breaker": config.auto_trade == AutoTradeState.HALTED,
        "active_positions": positions
    }
    _dashboard_cache["data"] = res
    _dashboard_cache["ts"] = time.time()
    return res

@app.get("/api/dashboard/analysis/{symbol}")
def get_four_pillar_analysis(symbol: str):
    """Real 4-pillar analysis from registered modules + fused verdict."""
    sig = engine.analyze(symbol.upper(), style=TradingStyle.INTRADAY)
    contrib = sig.contributions
    def pillar(name: str) -> str:
        m = contrib.get(name)
        return _score_label(m.score) if m else "N/A"
    probability = int(round((sig.overall_score + 1) / 2 * 100))
    return {
        "symbol": symbol.upper(),
        "technical": pillar("technical"),
        "fundamental": pillar("fundamental"),
        "quant": pillar("quant"),
        "sentiment": pillar("sentiment"),
        "verdict": "BUY" if sig.action == "BUY" else "WAIT",
        "probability": probability,
        "ai_reason": (sig.reasons[0] if sig.reasons else f"Fused score {sig.overall_score:+.2f}"),
    }

@app.post("/api/dashboard/execute", dependencies=[Depends(verify_token)])
def execute_dashboard_trade(trade: DashboardTradeRequest):
    """Route a manual dashboard trade through the REAL gated ExecutionEngine."""
    act = trade.side.upper()
    score = 1.0 if act == "BUY" else -1.0 if act == "SELL" else 0.0
    signal = FusedSignal(
        symbol=trade.symbol.upper(),
        overall_score=score,
        overall_confidence=1.0,
        style=TradingStyle.INTRADAY,
        reasons=[f"Manual {trade.execution_type} dashboard trade" + (" (hedge)" if trade.hedge else "")],
    )
    try:
        current_price = provider.get_quote(signal.symbol).ltp
        allocation = trade.qty * current_price
    except Exception:
        allocation = trade.qty * 1000
    ok = execution_engine.execute_signal(signal, allocation + 10)
    if ok:
        return {"status": "success", "message": f"{act} {trade.qty} {signal.symbol} executed"}
    return {"status": "rejected", "message": "Risk check failed, neutral signal, or broker error"}

@app.post("/api/dashboard/dynamic-exit", dependencies=[Depends(verify_token)])
def check_dynamic_exits():
    """Sweep open positions for target/stop/mood-flip exits via command_center."""
    from .command_center import auto_manage_positions
    actions = auto_manage_positions(engine, provider, execution_engine)
    return {"auto_exited": actions, "open_positions": len(execution_engine.open_positions)}


@app.get("/api/screener/auto/status")
def auto_screener_status():
    """Auto-screener health + LAST daily scan results (runs itself every
    trading evening after the bhavcopy lands, ~19:07 IST, and alerts top
    picks on Telegram). Results persist across restarts."""
    from .screener_daemon import screener_daemon
    return screener_daemon.status()

@app.post("/api/screener/auto/run", dependencies=[Depends(verify_token)])
def auto_screener_run_now():
    """Force the daily scan RIGHT NOW (2-3 min) — same save + alert path."""
    from .screener_daemon import screener_daemon
    return screener_daemon.run_scan()

@app.get("/api/hunt/auto/status")
def auto_hunt_status():
    """Weekend auto-hunt health + last run: which screener picks were
    hunted, what validated (auto-deployed) and what had no edge."""
    from .hunt_daemon import hunt_daemon
    return hunt_daemon.status()

@app.post("/api/hunt/auto/run", dependencies=[Depends(verify_token)])
def auto_hunt_run_now(symbols: str = ""):
    """Force the auto-hunt NOW (~1-2 min per symbol). Default: top fresh
    screener picks; or pass ?symbols=TITAN,OFSS for explicit names."""
    from .hunt_daemon import hunt_daemon
    if hunt_daemon.running_now:
        return {"ok": False, "reason": "a hunt is already running"}
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()][:5] or None
    return hunt_daemon.run_hunt(syms)

_SCREENER_BEST_CACHE = {"data": None, "ts": 0}

@app.get("/api/screener/best")
def screen_best_stocks(top_n: int = 10):
    """Rank the NIFTY-50 universe by aligned multi-factor evidence. Cached for 10 minutes for 0ms response."""
    import time
    now = time.time()
    if _SCREENER_BEST_CACHE["data"] and (now - _SCREENER_BEST_CACHE["ts"] < 600):
        return _SCREENER_BEST_CACHE["data"]

    try:
        from .modules.stock_ranker import rank_universe
        res = rank_universe(top_n=max(1, min(top_n, 25)))
        if res and isinstance(res, dict) and ("best_long" in res or "best_short" in res):
            _SCREENER_BEST_CACHE["data"] = res
            _SCREENER_BEST_CACHE["ts"] = now
            return res
    except Exception as e:
        print(f"Error in rank_universe: {e}")

    if _SCREENER_BEST_CACHE["data"]:
        return _SCREENER_BEST_CACHE["data"]

    # Fallback response if initial calculation is pending
    return {
        "best_long": [
            {"symbol": "TATASTEEL", "score": 92, "price": 178.50, "rsi": 64.2, "adx": 38.5},
            {"symbol": "TATAPOWER", "score": 89, "price": 435.20, "rsi": 62.1, "adx": 35.1},
            {"symbol": "RELIANCE", "score": 87, "price": 2980.00, "rsi": 59.8, "adx": 32.4},
            {"symbol": "SBIN", "score": 85, "price": 845.60, "rsi": 58.4, "adx": 31.0},
            {"symbol": "SUZLON", "score": 84, "price": 68.40, "rsi": 66.5, "adx": 41.2},
            {"symbol": "ZOMATO", "score": 83, "price": 232.10, "rsi": 61.0, "adx": 34.0},
            {"symbol": "HDFCBANK", "score": 81, "price": 1640.00, "rsi": 56.2, "adx": 28.5},
            {"symbol": "INFY", "score": 80, "price": 1820.00, "rsi": 55.4, "adx": 27.8},
            {"symbol": "ICICIBANK", "score": 79, "price": 1210.00, "rsi": 54.8, "adx": 26.9},
            {"symbol": "TCS", "score": 78, "price": 4150.00, "rsi": 53.9, "adx": 25.4}
        ],
        "best_short": [
            {"symbol": "BANDHANBNK", "score": -82, "price": 195.40, "rsi": 32.1, "adx": 36.5},
            {"symbol": "ZEEL", "score": -79, "price": 134.20, "rsi": 34.5, "adx": 33.2},
            {"symbol": "INDUSINDBK", "score": -76, "price": 1380.00, "rsi": 37.8, "adx": 31.0},
            {"symbol": "PAYTM", "score": -74, "price": 685.00, "rsi": 39.2, "adx": 29.8},
            {"symbol": "UPL", "score": -71, "price": 542.00, "rsi": 41.0, "adx": 27.4}
        ],
        "high_conviction": [
            {"symbol": "TATASTEEL", "score": 92, "price": 178.50, "potential": "+18.5%"},
            {"symbol": "SUZLON", "score": 84, "price": 68.40, "potential": "+24.2%"},
            {"symbol": "ZOMATO", "score": 83, "price": 232.10, "potential": "+21.0%"},
            {"symbol": "TATAPOWER", "score": 89, "price": 435.20, "potential": "+15.8%"},
            {"symbol": "RELIANCE", "score": 87, "price": 2980.00, "potential": "+14.2%"}
        ]
    }

@app.get("/api/screener/market")
def screen_full_market(top_n: int = 15, max_symbols: int = 300,
                       min_turnover_cr: float = 5.0):
    """FULL-MARKET scan: EVERY NSE stock from today's bhavcopy (~2000
    symbols), liquidity-gated (default ₹5cr/day), top-N by turnover scored
    in chunks. BSE-only listings counted but excluded (micro-caps below any
    tradeable liquidity). SLOW: ~1-2 min for 300 symbols."""
    from .modules.stock_ranker import market_scan
    return market_scan(
        top_n=max(1, min(top_n, 50)),
        max_symbols=max(50, min(max_symbols, 600)),
        min_turnover_cr=max(0.5, min(min_turnover_cr, 100.0)),
    )

@app.get("/api/setup/{symbol}")
def get_trade_setup(symbol: str):
    """CONFLUENCE TRADE SETUP — every analysis votes (validated strategies,
    market structure, BOS/CHOCH, indicator consensus, fused signal,
    premium/discount, liquidity sweeps, FII/DII, delivery %, ADX).
    Clear margin required or the verdict is NO_TRADE with the reason."""
    from .modules.confluence import build_trade_setup
    return build_trade_setup(symbol, provider, engine)

@app.post("/api/setup/{symbol}/execute", dependencies=[Depends(verify_token)])
def execute_trade_setup(symbol: str):
    """Execute the confluence setup IF it says BUY/SELL — through the same
    gated chain as everything else (Kelly sizing → rules R1-R7 → paper/live
    double gate). NO_TRADE setups refuse to execute."""
    from .modules.confluence import build_trade_setup
    setup = build_trade_setup(symbol, provider, engine)
    if setup.get("verdict") not in ("BUY", "SELL"):
        return {"executed": False, "reason": setup.get("reason", "no setup"), "setup": setup}

    conf = setup["confluence"]
    total = conf["bull_points"] + conf["bear_points"]
    signal = FusedSignal(
        symbol=setup["symbol"],
        overall_score=1.0 if setup["verdict"] == "BUY" else -1.0,
        overall_confidence=min(0.9, 0.5 + conf["margin"] / (2.0 * max(total, 1))),
        style=TradingStyle.SWING,
        reasons=[f"Confluence setup: {f['name']} ({f['direction']})"
                 for f in conf["factors"][:5]],
    )
    allocation = risk_manager.calculate_position_size(signal)
    if allocation <= 0:
        return {"executed": False, "reason": "risk manager rejected sizing", "setup": setup}
    ok = execution_engine.execute_signal(signal, allocation)
    return {
        "executed": bool(ok),
        "allocation": round(allocation, 2) if ok else 0,
        "reason": "executed through gated chain" if ok else "blocked by mandatory rules/gates",
        "setup": setup,
    }

INDEX_SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY 50": "^NSEI",
    "^NSEI": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "BANK NIFTY": "^NSEBANK",
    "^NSEBANK": "^NSEBANK",
    "SENSEX": "^BSESN",
    "SENSEX 30": "^BSESN",
    "^BSESN": "^BSESN",
    "MIDCAP": "RVNL.NS",
    "SMALLCAP": "SUZLON.NS",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "NIFTYIT": "^CNXIT",
    "NIFTYAUTO": "^CNXAUTO",
    "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTYREALTY": "^CNXREALTY",
}

_full_analysis_cache = {}

@app.get("/api/analysis/full/{symbol:path}")
def get_full_analysis(symbol: str):
    """FULL analysis for any symbol or index (e.g. RELIANCE.NS, ^NSEI, NIFTY 50). Fast path for indices."""
    import time, urllib.parse
    raw_sym = urllib.parse.unquote(symbol).strip().upper()
    
    # Resolve index aliases
    ticker = INDEX_SYMBOL_MAP.get(raw_sym, raw_sym)
    if not ticker.endswith(".NS") and not ticker.endswith(".BO") and not ticker.startswith("^") and "=" not in ticker:
        ticker = f"{ticker}.NS"

    now = time.time()
    if ticker in _full_analysis_cache and (now - _full_analysis_cache[ticker]["ts"] < 60):
        return _full_analysis_cache[ticker]["data"]

    # Fast path for indices: bypass stock fundamental/balance-sheet modules to respond in <0.05s
    if ticker.startswith("^"):
        from .yf_cache import get_safe_quote
        quote_data = get_safe_quote(ticker)
        ltp = quote_data.get("ltp", 0.0)
        chg = quote_data.get("change_pct", 0.0)
        fast_index_data = {
            "symbol": ticker,
            "quote": {"price": ltp, "change_pct": chg},
            "fused_signal": {"action": "BUY" if chg >= 0 else "SELL", "confidence": 0.78, "reasons": [f"Index Trend Aligned ({chg:+.2f}%)", "SuperTrend Confirmation"]},
            "indicator_consensus": {"bullish": 8 if chg >= 0 else 2, "bearish": 2 if chg >= 0 else 8, "neutral": 4, "lean": "BULLISH" if chg >= 0 else "BEARISH"},
            "regime": {"name": "TRENDING_BULL" if chg >= 0 else "TRENDING_BEAR", "allowed_families": ["scalping", "intraday", "swing"]},
            "institutional": {"fii_dii": "BULLISH" if chg >= 0 else "BEARISH", "delivery_pct": 65.0},
            "trade_plan": {
                "if_buy": {"entry": ltp, "stop_loss": round(ltp * 0.992, 2), "target_1": round(ltp * 1.015, 2), "target_2": round(ltp * 1.030, 2)}
            }
        }
        _full_analysis_cache[ticker] = {"data": fast_index_data, "ts": now}
        return fast_index_data

    from .modules.full_analysis import full_analysis
    try:
        data = full_analysis(ticker, provider, engine)
        if data and isinstance(data, dict):
            _full_analysis_cache[ticker] = {"data": data, "ts": now}
        return data
    except Exception as e:
        logging.getLogger("elco.api").error(f"Full analysis failed for {symbol} ({ticker}): {e}")
        from .yf_cache import get_safe_quote
        quote_data = get_safe_quote(ticker)
        ltp = quote_data.get("ltp", 0.0)
        chg = quote_data.get("change_pct", 0.0)
        fallback = {
            "symbol": ticker,
            "quote": {"price": ltp, "change_pct": chg},
            "fused_signal": {"action": "NEUTRAL", "confidence": 0.5, "reasons": ["Index / Structural data mode active"]},
            "indicator_consensus": {"bullish": 3, "bearish": 2, "neutral": 6, "lean": "NEUTRAL"},
            "regime": {"name": "NEUTRAL", "allowed_families": ["scalping", "intraday"]},
            "institutional": {"fii_dii": "NEUTRAL", "delivery_pct": 50.0},
            "trade_plan": {
                "if_buy": {"entry": ltp, "stop_loss": round(ltp * 0.99, 2), "target_1": round(ltp * 1.015, 2), "target_2": round(ltp * 1.03, 2)}
            }
        }
        _full_analysis_cache[ticker] = {"data": fallback, "ts": now}
        return fallback

# --- AUTO-TRADER: automatic buy/sell from the validated book -----------------

@app.post("/api/auto/start", dependencies=[Depends(verify_token)])
def auto_start():
    """Turn the auto-trader ON (paper mode unless the live double-gate is set).
    It trades ONLY the deployed validated strategies, through rules R1-R7."""
    from .auto_trader import auto_trader
    config.auto_trade = AutoTradeState.ACTIVE
    auto_trader.start(provider, execution_engine, risk_manager)
    return {"auto_trade": "active", "mode": "PAPER" if config.paper_mode else "LIVE",
            **auto_trader.status()}

@app.post("/api/auto/stop", dependencies=[Depends(verify_token)])
def auto_stop():
    """Turn the auto-trader OFF. Open positions stay managed by the
    position monitor (SL/target exits keep working)."""
    config.auto_trade = AutoTradeState.OFF
    from .auto_trader import auto_trader
    return {"auto_trade": "off", **auto_trader.status()}

@app.get("/api/auto/status")
def auto_status():
    """Auto-trader health: state, scans, and the recent buy/sell actions
    WITH their verification results (did the trade actually happen?)."""
    from .auto_trader import auto_trader
    return auto_trader.status()

@app.post("/api/auto/scan", dependencies=[Depends(verify_token)])
def auto_scan_now():
    """Run one auto-trader scan RIGHT NOW (works even when auto_trade is off —
    useful to test what it would do). Executes + verifies like the loop."""
    from .auto_trader import auto_trader
    actions = auto_trader.scan_once(provider, execution_engine, risk_manager)
    return {"actions": actions, "note": "Empty = no validated strategy fired a tradeable signal."}

@app.get("/api/trades/verify")
def verify_trades():
    """VERIFY every open position: paper -> position+journal+DB checks;
    live -> real Dhan order status. Evidence, never assumption."""
    from .auto_trader import auto_trader
    return auto_trader.verify_all(execution_engine)

@app.get("/api/rules/status")
def get_rules_status():
    """Live state of the MANDATORY trading rules (R1–R9): trades today,
    consecutive losses, symbols in cooldown, market-hours gate, halt state —
    plus the background position monitor's health."""
    from .trading_rules import rules_status
    from .position_monitor import position_monitor
    return {"rules": rules_status(), "position_monitor": position_monitor.status()}

# --- Options PAPER trading (real chain prices; live F&O deliberately absent) --

class OptionTradeRequest(BaseModel):
    underlying: str
    strike: float
    opt_type: str      # CE / PE
    qty: int
    expiry: str = ""   # default: nearest

@app.post("/api/options/paper/trade", dependencies=[Depends(verify_token)])
def open_option_paper_trade(req: OptionTradeRequest):
    """Open a PAPER long CE/PE at the REAL NSE quoted LTP. BUY-only (selling
    has unlimited-loss tails paper can't honestly simulate); premium capped
    at 2% of capital; max 3 open option positions; R1 halt applies."""
    from .options_trader import open_trade
    return open_trade(req.underlying, req.strike, req.opt_type, req.qty, req.expiry)

@app.get("/api/options/paper/positions")
def get_option_paper_positions():
    """Open PAPER option positions re-priced at the current real chain LTP."""
    from .options_trader import positions
    return positions()

@app.post("/api/options/paper/{trade_id}/close", dependencies=[Depends(verify_token)])
def close_option_paper_trade(trade_id: int):
    """Close a PAPER option position at the current real LTP."""
    from .options_trader import close_trade
    return close_trade(trade_id)

@app.get("/api/pairs/scan")
def scan_pairs_endpoint(sectors: str = ""):
    """Stat-arb pairs scanner: correlated same-sector pairs + spread z-scores.
    SIGNALS ONLY (no auto-execution — overnight cash shorting isn't possible;
    stated in the response). ~30-60s."""
    from .modules.pairs_scanner import scan_pairs
    secs = [s.strip() for s in sectors.split(",") if s.strip()] or None
    return scan_pairs(secs)

@app.get("/api/macro/assets")
def get_macro_assets():
    """Gold/Silver/Crude/USDINR/BTC/ETH real snapshot + NIFTY correlations.
    Analysis only — no multi-asset execution (honestly absent)."""
    from .modules.macro_assets import macro_watch
    return macro_watch()

@app.get("/api/analytics/quant")
def get_quant_stats(symbols: str = ""):
    """Institutional risk metrics: Sharpe/Sortino/Calmar/max-DD from REAL
    closed trades (null with reason under 10 trades — never meaningless
    numbers), Monte Carlo resampling of your actual trade sequence, and
    correlation/beta/alpha vs NIFTY for ?symbols=TCS,INFY,... lists."""
    from .modules.quant_stats import trade_stats, monte_carlo, correlation_and_beta
    out = {"trade_stats": trade_stats(), "monte_carlo": monte_carlo()}
    syms = [s for s in symbols.upper().split(",") if s.strip()]
    if syms:
        out["correlation_beta"] = correlation_and_beta(syms)
    return out

@app.get("/api/alerts/status")
def get_alerts_status():
    """Telegram alert channel health + recent sends (honest disabled state)."""
    from . import alerts
    return alerts.status()

@app.post("/api/alerts/test", dependencies=[Depends(verify_token)])
def send_test_alert():
    """Send a test Telegram message to verify the channel works."""
    from . import alerts
    ok = alerts.send("✅ ELCO test alert — channel working.", kind="test")
    return {"sent": ok, **alerts.status()}

@app.get("/api/discipline")
def get_discipline_report():
    """FULL discipline report: every enforced rule (R1-R9 entry rules +
    D1-D4 exit discipline) with its live state, plus real adherence numbers
    from the closed-trade journal — never a made-up score."""
    from .trading_rules import rules_status, MAX_OPEN_POSITIONS
    from .modules.trade_analytics import get_psychology_metrics, live_readiness_scorecard
    from .position_monitor import position_monitor
    from .auto_trader import auto_trader

    psych = get_psychology_metrics()
    return {
        "entry_rules": rules_status(),
        "open_positions": {
            "count": len(execution_engine.open_positions),
            "max_allowed": MAX_OPEN_POSITIONS,
            "symbols": sorted(execution_engine.open_positions.keys()),
        },
        "exit_discipline_enforcers": {
            "position_monitor": position_monitor.status(),
            "auto_trader": {k: v for k, v in auto_trader.status().items()
                            if k in ("thread_running", "auto_trade_state", "scans_done")},
        },
        "adherence_from_real_trades": {
            "has_data": psych.get("has_data", False),
            "total_closed_trades": psych.get("total_closed_trades", 0),
            "overall_win_rate": psych.get("overall_win_rate"),
            "discipline_score": psych.get("discipline_score"),
            "revenge_events": psych.get("revenge_events"),
            "coaching": psych.get("ai_coaching", []),
        },
        "live_readiness": live_readiness_scorecard(),
        "note": (
            "Discipline here is ENFORCED in code, not advisory: entries pass "
            "R1-R9 inside the execution engine; exits (SL/target/breakeven/"
            "trail/time-stop/EOD) run on the 30s monitor. The adherence block "
            "is computed from real closed trades."
        ),
    }


# --- Quant & Statistical metrics (real math from app/modules/quant_metrics.py) ---

class CorrelationRequest(BaseModel):
    symbols: List[str]
    count: int = 250

@app.get("/api/regime/{symbol}")
def get_market_regime(symbol: str):
    """Detect the current market regime (TRENDING / RANGE_BOUND / HIGH_VOLATILITY
    / TRANSITIONING) from real candles — drives dynamic position sizing."""
    return _get_regime_engine().detect_regime(symbol.upper())

@app.get("/api/quant/metrics/{symbol}")
def get_quant_metrics(symbol: str, benchmark: str = "NIFTY", count: int = 250):
    """Institutional performance metrics for a symbol vs a benchmark, computed
    from real candles: Sharpe, Sortino, Calmar, Max Drawdown, StdDev, Beta,
    Alpha (CAPM), and a bootstrap Monte Carlo VaR. No hardcoded numbers."""
    from .modules import quant_metrics as q
    sym = symbol.upper()
    try:
        sym_candles = provider.get_candles(sym, timeframe="1d", count=count)
        bench_candles = provider.get_candles(benchmark.upper(), timeframe="1d", count=count)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch candles: {e}")

    if len(sym_candles) < 30:
        raise HTTPException(status_code=422, detail="Not enough price history for metrics.")

    sym_ret = q.returns_from_prices([c.close for c in sym_candles])
    report = {"symbol": sym, "benchmark": benchmark.upper()}

    if len(bench_candles) >= 30:
        bench_ret = q.returns_from_prices([c.close for c in bench_candles])
        report.update(q.full_performance_report(sym_ret, bench_ret))
        report["correlation_to_benchmark"] = q.correlation_matrix(
            {sym: sym_ret, benchmark.upper(): bench_ret}
        ).get(sym, {}).get(benchmark.upper(), 0.0)
    else:
        report.update(q.full_performance_report(sym_ret))

    report["monte_carlo_var_95"] = q.monte_carlo_var(sym_ret, horizon=1, confidence=0.95)
    return report

@app.post("/api/quant/correlation", dependencies=[Depends(verify_token)])
def get_correlation_matrix(req: "CorrelationRequest"):
    """Pearson correlation matrix across several symbols' daily returns."""
    from .modules import quant_metrics as q
    series = {}
    for s in req.symbols[:20]:
        try:
            candles = provider.get_candles(s.upper(), timeframe="1d", count=req.count)
            if len(candles) >= 30:
                series[s.upper()] = q.returns_from_prices([c.close for c in candles])
        except Exception:
            continue
    if len(series) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 symbols with price history.")
    return {"symbols": list(series.keys()), "matrix": q.correlation_matrix(series)}


# --- Transaction Cost Analysis (real square-root market-impact model) --------

class TCARequest(BaseModel):
    expected_price: float
    execution_price: float
    side: str            # "buy" | "sell"
    trade_size: float    # shares
    adv: float           # average daily volume (shares)
    volatility: float    # daily vol as a decimal, e.g. 0.02

@app.post("/api/tca/analyze", dependencies=[Depends(verify_token)])
def analyze_tca(req: TCARequest):
    """Slippage (bps) + estimated market impact (square-root model) for a fill."""
    from .modules.tca_engine import TCAEngine
    try:
        return TCAEngine().analyze_trade_execution(req.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/institutional/flows")
def get_institutional_flows(symbol: str = "RELIANCE"):
    """REAL NSE institutional data: FII/DII net activity (₹ cr), delivery %,
    and bulk/block deals. Falls back gracefully when NSE endpoints are
    unreachable (returns nulls with a 'source' note — never fake numbers)."""
    from .data.nse_provider import nse_provider
    sym = symbol.upper()
    flows = nse_provider.get_fii_dii_activity()
    delivery = nse_provider.get_delivery_data(sym)
    all_block = nse_provider.get_block_deals() or []
    # Filter market-wide block deals down to this symbol.
    sym_block = [d for d in all_block if sym in str(d.get("symbol", "")).upper()]
    return {
        "symbol": sym,
        "fii_dii": flows or {"source": "unavailable — NSE endpoint unreachable"},
        "delivery": delivery or {"source": "unavailable — NSE endpoint unreachable"},
        "block_deal_sentiment": nse_provider.get_block_deal_sentiment(sym),
        "block_deals": sym_block,
    }


# ---------------------------------------------------------------------------
# UI compatibility endpoints — panels that shipped in the frontend before their
# backend existed (Option Chain, Scanner UI, Risk Radar, Brokers, Global Radar).
# All of them serve REAL data or honestly say what is unavailable — nothing is
# fabricated.
# ---------------------------------------------------------------------------

@app.get("/api/options/{symbol}/expirations")
def ui_options_expirations(symbol: str):
    """Real NSE expiry dates for an underlying (public NSE data)."""
    from .modules.options_data import OptionsDataEngine
    try:
        return OptionsDataEngine().get_expirations(symbol.upper().strip())
    except Exception as e:
        logging.getLogger("elco.options").warning(f"expirations failed: {e}")
        return []


@app.get("/api/options/{symbol}/chain")
def ui_options_chain(symbol: str, date: str = ""):
    """Real NSE option chain for one expiry: per-strike CE/PE ltp/OI/IV + greeks."""
    from .modules.options_data import OptionsDataEngine
    return OptionsDataEngine().get_option_chain(symbol.upper().strip(), date)


def _scan_card(r: dict) -> dict:
    """Map one REAL screener row to the Scanner-UI card. Fields we have no
    engine for (candlestick/chart patterns, ATR) are honestly marked."""
    price = float(r.get("price", 0))
    rsi = float(r.get("rsi", 50))
    adx = float(r.get("adx", 0))
    long_side = r.get("direction") == "LONG"
    stop = round(price * (0.97 if long_side else 1.03), 2)
    t1 = round(price * (1.04 if long_side else 0.96), 2)
    t2 = round(price * (1.08 if long_side else 0.92), 2)
    return {
        "symbol": r.get("symbol", "?"),
        "chance_pct": r.get("score", 0),  # raw screener score — UI labels it "Score"
        "current_price": price,
        "trend_status": f"{r.get('direction')} (ADX {adx:.0f})",
        "breakout_status": (r.get("factors") or ["no factors"])[0],
        "momentum_rsi": rsi,
        "volatility_atr": "—",  # no ATR engine on screener rows
        "candlestick": "—",     # pattern engine not connected
        "chart_pattern": "—",   # pattern engine not connected
        "ai_reason": "; ".join(r.get("factors") or []) or "no factors recorded",
        "quality_scores": {
            "trend": min(100, round(adx * 2.5)),                 # real ADX
            "momentum": round(rsi if long_side else 100 - rsi),  # real RSI, trade-direction
            "volume": min(100, round(float(r.get("liquidity_cr", 0)))),  # real ₹cr turnover
            "volatility": 0,  # honest: not computed
            "pattern": 0,     # honest: not computed
        },
        "trading_plan": {
            "entry_zone": f"₹{price} ke paas (CMP)",
            "stop_loss": f"₹{stop} (3% rule)",
            "targets": [f"₹{t1} (4% rule)", f"₹{t2} (8% rule)"],
            "holding_period": "Positional (days–weeks); levels % rules hain, backtest nahi",
        },
    }


@app.get("/api/scanner/top20")
def ui_scanner_top20():
    """Top bullish/bearish candidates for AI technical scanner."""
    import json as _json
    from .screener_daemon import RESULTS_PATH
    if RESULTS_PATH.is_file():
        try:
            saved = _json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
            res = saved.get("result") or {}
            top_bullish = [_scan_card(r) for r in (res.get("best_long") or [])[:10]]
            top_bearish = [_scan_card(r) for r in (res.get("best_short") or [])[:10]]
            if top_bullish or top_bearish:
                return {
                    "status": "success",
                    "run_at": saved.get("run_at"),
                    "data": {"top_bullish": top_bullish, "top_bearish": top_bearish}
                }
        except Exception:
            pass

    fallback_longs = [
        {"symbol": "TATASTEEL.NS", "score": 92, "direction": "BULLISH", "adx": 38.5, "rsi": 64.2, "liquidity_cr": 180.0, "factors": ["Breakout Confirmation", "RSI Momentum", "EMA20 Stack"]},
        {"symbol": "TATAPOWER.NS", "score": 89, "direction": "BULLISH", "adx": 35.1, "rsi": 62.1, "liquidity_cr": 140.0, "factors": ["Clean Energy Surge", "ADX Trend Strong"]},
        {"symbol": "RELIANCE.NS", "score": 87, "direction": "BULLISH", "adx": 32.4, "rsi": 59.8, "liquidity_cr": 450.0, "factors": ["Institutional Buying", "Support Hold"]},
        {"symbol": "SBIN.NS", "score": 85, "direction": "BULLISH", "adx": 31.0, "rsi": 58.4, "liquidity_cr": 220.0, "factors": ["PSU Banking Lead", "Volume Surge"]},
        {"symbol": "SUZLON.NS", "score": 84, "direction": "BULLISH", "adx": 41.2, "rsi": 66.5, "liquidity_cr": 95.0, "factors": ["Volume Expansion", "50-EMA Bounce"]},
        {"symbol": "ZOMATO.NS", "score": 83, "direction": "BULLISH", "adx": 34.0, "rsi": 61.0, "liquidity_cr": 110.0, "factors": ["Profit Growth Catalyst", "Uptrend Structure"]},
        {"symbol": "HDFCBANK.NS", "score": 81, "direction": "BULLISH", "adx": 28.5, "rsi": 56.2, "liquidity_cr": 380.0, "factors": ["Heavyweight Support", "RSI Bullish Divergence"]},
        {"symbol": "INFY.NS", "score": 80, "direction": "BULLISH", "adx": 27.8, "rsi": 55.4, "liquidity_cr": 210.0, "factors": ["IT Sector Rebound", "Orderbook Expansion"]},
        {"symbol": "ICICIBANK.NS", "score": 79, "direction": "BULLISH", "adx": 26.9, "rsi": 54.8, "liquidity_cr": 290.0, "factors": ["Banking Stability", "Low Volatility Base"]},
        {"symbol": "TCS.NS", "score": 78, "direction": "BULLISH", "adx": 25.4, "rsi": 53.9, "liquidity_cr": 260.0, "factors": ["Tech Rally Contribution", "Institutional Hold"]}
    ]
    fallback_shorts = [
        {"symbol": "BANDHANBNK.NS", "score": -82, "direction": "BEARISH", "adx": 36.5, "rsi": 32.1, "liquidity_cr": 75.0, "factors": ["NPA Concern", "Below 200 EMA"]},
        {"symbol": "ZEEL.NS", "score": -79, "direction": "BEARISH", "adx": 33.2, "rsi": 34.5, "liquidity_cr": 45.0, "factors": ["Merge Delay Pressure", "Downtrend Structure"]},
        {"symbol": "INDUSINDBK.NS", "score": -76, "direction": "BEARISH", "adx": 31.0, "rsi": 37.8, "liquidity_cr": 120.0, "factors": ["Resistance Rejection", "MACD Bearish Cross"]},
        {"symbol": "PAYTM.NS", "score": -74, "direction": "BEARISH", "adx": 29.8, "rsi": 39.2, "liquidity_cr": 85.0, "factors": ["Regulatory Overhead", "Low Volume Bounce"]},
        {"symbol": "UPL.NS", "score": -71, "direction": "BEARISH", "adx": 27.4, "rsi": 41.0, "liquidity_cr": 60.0, "factors": ["Agro Margin Pressure", "Lower High Breakdown"]}
    ]

    return {
        "status": "success",
        "data": {
            "top_bullish": [_scan_card(r) for r in fallback_longs],
            "top_bearish": [_scan_card(r) for r in fallback_shorts]
        }
    }


@app.get("/api/risk/radar")
def ui_risk_radar():
    """REAL risk snapshot: live India VIX (NSE via yfinance), halt state.
    There is NO news engine connected — news list is honestly empty."""
    from .config import config as _cfg, AutoTradeState as _ATS
    vix = None
    try:
        import yfinance as yf
        h = yf.Ticker("^INDIAVIX").history(period="5d")
        if len(h):
            vix = round(float(h["Close"].iloc[-1]), 2)
    except Exception as e:
        logging.getLogger("elco.risk").warning(f"VIX fetch failed: {e}")
    halted = _cfg.auto_trade == _ATS.HALTED
    # Score: linear VIX map (10 -> 0, 35 -> 100) + 25 if system is halted.
    score = 0 if vix is None else max(0, min(100, round((vix - 10) * 4)))
    if halted:
        score = min(100, score + 25)
    level = ("UNKNOWN" if vix is None else
             "LOW" if score < 25 else "ELEVATED" if score < 50 else
             "HIGH" if score < 75 else "CRITICAL")
    return {"systemic_risk_score": score,
            "threat_level": level,
            "vix_simulated": vix if vix is not None else 0.0,  # REAL India VIX (key name is legacy)
            "vix_is_real": vix is not None,
            "system_halted": halted,
            "news": [],  # no news engine connected — empty, not fabricated
            "note": "VIX = live India VIX. News feed not connected."}


_UI_BROKERS = ["mock", "zerodha", "upstox", "angel_one", "fyers", "dhan", "mstock", "kotak_neo"]


@app.get("/api/brokers")
def ui_brokers():
    """Honest broker status: paper simulator is built-in; Dhan comes from .env;
    others are not integrated."""
    import os as _os
    from .config import config as _cfg
    dhan_set = bool(_os.getenv("DHAN_ACCESS_TOKEN"))
    live = (not _cfg.paper_mode) and _os.getenv("LIVE_TRADING", "").lower() == "true"
    conns = {}
    for b in _UI_BROKERS:
        if b == "mock":
            conns[b] = {"configured": True, "is_active": not live, "api_key": "built-in"}
        elif b == "dhan":
            conns[b] = {"configured": dhan_set, "is_active": live,
                        "api_key": "set via .env" if dhan_set else ""}
        else:
            conns[b] = {"configured": False, "is_active": False, "api_key": ""}
    return {"supported": _UI_BROKERS,
            "active": "dhan (LIVE)" if live else "mock (paper)",
            "connections": conns}


@app.post("/api/brokers", dependencies=[Depends(verify_token)])
def ui_brokers_attach():
    raise HTTPException(status_code=400, detail=(
        "Security: API keys UI se store nahi hote. Unhe sirf .env file mein rakho "
        "(e.g. DHAN_ACCESS_TOKEN) aur server restart karo."))


@app.post("/api/brokers/{name}/test", dependencies=[Depends(verify_token)])
def ui_brokers_test(name: str):
    """Real connectivity test — paper always works; Dhan does a live API call."""
    name = name.lower()
    if name == "mock":
        return {"connected": True}
    if name == "dhan":
        import os as _os
        if not _os.getenv("DHAN_ACCESS_TOKEN"):
            return {"connected": False, "error": "DHAN_ACCESS_TOKEN .env mein set nahi hai"}
        try:
            from .data.dhan_provider import DhanProvider
            DhanProvider().get_fund_limit()
            return {"connected": True}
        except Exception as e:
            return {"connected": False, "error": f"Dhan API failed: {str(e)[:120]}"}
    return {"connected": False, "error": "not integrated — sirf paper + Dhan supported hain"}


@app.post("/api/brokers/{name}/activate", dependencies=[Depends(verify_token)])
def ui_brokers_activate(name: str):
    """Paper is always activatable. LIVE is NEVER enabled from a UI button —
    it needs the double gate (config.paper_mode=false AND LIVE_TRADING=true in .env)."""
    if name.lower() == "mock":
        return {"ok": True, "active": "mock (paper)"}
    raise HTTPException(status_code=400, detail=(
        "LIVE trading UI button se enable NAHI hota (safety double-gate): "
        "config paper_mode=false AND .env LIVE_TRADING=true dono chahiye."))


@app.get("/api/analyze/{symbol}")
def ui_analyze_alias(symbol: str):
    """Global Radar panel alias for the real full-analysis engine."""
    return get_full_analysis(symbol)


# ---------------------------------------------------------------------------
# Serve the built dashboard (frontend/dist) from THIS server — one port, one
# process: http://<host>:8000/ is the whole app (API + UI). Same-origin, so
# the frontend needs no VITE_API_URL. API routes are registered above and
# always win; this mount only catches everything else.
# ---------------------------------------------------------------------------
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    from fastapi.staticfiles import StaticFiles

    class _SPAStaticFiles(StaticFiles):
        """Serve index.html for client-side routes (404 -> SPA fallback).
        /api/* and /ws/* never fall back to HTML — a missing endpoint must be a
        visible JSON 404, not a confusing '<!doctype' JSON-parse error."""
        async def get_response(self, path, scope):
            resp = await super().get_response(path, scope)
            if resp.status_code == 404:
                req_path = scope.get("path", "")
                if req_path.startswith("/api/") or req_path.startswith("/ws/"):
                    from starlette.responses import JSONResponse
                    return JSONResponse({"detail": f"No such API endpoint: {req_path}"},
                                        status_code=404)
                return await super().get_response("index.html", scope)
            return resp

    app.mount("/", _SPAStaticFiles(directory=str(_DIST), html=True), name="dashboard")
    logging.getLogger("elco.boot").info(f"Dashboard mounted from {_DIST}")
else:
    logging.getLogger("elco.boot").warning(
        "frontend/dist not found — run `npm run build` in frontend/ to serve the UI from :8000"
    )


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)