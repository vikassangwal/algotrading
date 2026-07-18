import logging
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone

logger = logging.getLogger("elco.db")

# Honor ELCO_DB_PATH (set in docker-compose to a persistent volume);
# fall back to a local file for dev.
_db_path = os.getenv("ELCO_DB_PATH", "elco.db")
DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TradeRecord(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String) # BUY or SELL
    quantity = Column(Integer)
    price = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String) # OPEN, CLOSED
    pnl = Column(Float, default=0.0)
    reason = Column(String)
    # Analytics dimensions — enable real GROUP BY reporting (strategy/style/setup).
    strategy = Column(String, index=True)   # e.g. the dominant module driving the trade
    timeframe = Column(String, index=True)  # trading style: scalping/intraday/swing/...
    setup = Column(String, index=True)      # the entry setup label (top contributor)

class PortfolioRecord(Base):
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    cash = Column(Float)
    total_value = Column(Float)

class WorkflowApproval(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, index=True) # e.g. REQ-1234
    type = Column(String)
    details = Column(String)
    initiator = Column(String)
    riskLevel = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="pending") # pending, approved, rejected

class OptionsPaperTrade(Base):
    """PAPER options positions priced off the REAL NSE option chain.
    Live options execution is deliberately absent — cash-equity live comes
    first, and only after the readiness scorecard says READY."""
    __tablename__ = "options_paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    underlying = Column(String, index=True)   # NIFTY / RELIANCE / ...
    strike = Column(Float)
    opt_type = Column(String)                 # CE / PE
    expiry = Column(String)                   # as NSE returns it (21-Jul-2026)
    qty = Column(Integer)                     # units (not lots)
    entry_ltp = Column(Float)
    exit_ltp = Column(Float, default=0.0)
    status = Column(String, default="OPEN")   # OPEN / CLOSED
    pnl = Column(Float, default=0.0)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)
    note = Column(String, default="")


class DeployedStrategy(Base):
    """A generator-VALIDATED strategy the user has chosen to run live/paper.
    Signals from these are routed through the SAME gated execution path
    (mandatory rules R1-R7 + risk manager) as every other trade."""
    __tablename__ = "deployed_strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)              # e.g. "MACD 8/21/5 [1:1.0]"
    symbol = Column(String, index=True)
    params = Column(String)            # JSON of template params + exits
    active = Column(Integer, default=1)  # 1=active, 0=paused
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)  # pbkdf2_sha256$... from app.auth.hash_password
    role = Column(String, default="user")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        _migrate_trade_analytics_columns()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


def _migrate_trade_analytics_columns():
    """Add analytics columns to an existing `trades` table if they're missing.

    SQLAlchemy's create_all won't ALTER existing tables, so for a pre-existing
    SQLite DB we add the strategy/timeframe/setup columns idempotently.
    """
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        if "trades" not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns("trades")}
        with engine.begin() as conn:
            for col in ("strategy", "timeframe", "setup"):
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE trades ADD COLUMN {col} VARCHAR"))
                    logger.info(f"Migrated trades table: added column '{col}'.")
    except Exception as e:
        logger.warning(f"Trade analytics column migration skipped: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
