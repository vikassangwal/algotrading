from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
import os
from sqlalchemy import Column, String, Boolean
from ..db import Base, db_engine, SessionLocal
from ..config import config, BrokerName

logger = logging.getLogger("elco.api.brokers")

router = APIRouter(prefix="/api/brokers", tags=["brokers"])

SUPPORTED_BROKERS = [
    "mock", "dhan", "zerodha", "upstox", "angel_one",
    "fyers", "mstock", "kotak_neo"
]

class BrokerConnection(Base):
    __tablename__ = "broker_connections"
    broker = Column(String, primary_key=True)
    api_key = Column(String, default="")
    api_secret = Column(String, default="")
    is_active = Column(Boolean, default=False)

def _ensure_table_and_restore():
    try:
        Base.metadata.create_all(bind=db_engine, tables=[BrokerConnection.__table__])
        db = SessionLocal()
        try:
            active_row = db.query(BrokerConnection).filter(BrokerConnection.is_active == True).first()
            if not active_row:
                active_row = db.query(BrokerConnection).filter(BrokerConnection.broker == "dhan").first()

            if active_row:
                config.broker_name = active_row.broker
                if active_row.api_key:
                    config.api_key = active_row.api_key
                if active_row.api_secret:
                    config.api_secret = active_row.api_secret
                    
                if active_row.broker == "dhan":
                    os.environ["DHAN_CLIENT_ID"] = active_row.api_key or ""
                    os.environ["DHAN_ACCESS_TOKEN"] = active_row.api_secret or ""
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to ensure broker table / restore env: {e}")

_ensure_table_and_restore()

def _mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 6:
        return secret[:2] + "****"
    return secret[:3] + "..." + secret[-3:]

class BrokerCredsRequest(BaseModel):
    broker: str
    api_key: str = ""
    api_secret: str = ""

@router.get("")
def list_brokers():
    """List supported brokers + saved connections (secrets masked)."""
    db = SessionLocal()
    try:
        rows = db.query(BrokerConnection).all()
        saved = {
            r.broker: {
                "broker": r.broker,
                "api_key": _mask(r.api_key),
                "api_secret": _mask(r.api_secret),
                "is_active": r.is_active,
                "configured": bool(r.api_key or r.broker == "mock"),
            }
            for r in rows
        }
    finally:
        db.close()

    active_broker = config.broker_name if hasattr(config, "broker_name") else "dhan"
    return {
        "supported": SUPPORTED_BROKERS,
        "active": active_broker,
        "connections": [saved.get(b, {"broker": b, "configured": False, "is_active": False}) for b in SUPPORTED_BROKERS],
    }

@router.post("")
def save_broker(req: BrokerCredsRequest):
    """Attach / update a broker's credentials and save permanently."""
    broker = req.broker.lower().strip()
    if broker not in SUPPORTED_BROKERS:
        raise HTTPException(status_code=400, detail=f"Unsupported broker. Choose from {SUPPORTED_BROKERS}")

    db = SessionLocal()
    try:
        row = db.query(BrokerConnection).filter(BrokerConnection.broker == broker).first()
        if row is None:
            row = BrokerConnection(broker=broker)
            db.add(row)

        if req.api_key:
            row.api_key = req.api_key
        if req.api_secret:
            row.api_secret = req.api_secret

        row.is_active = True
        for r in db.query(BrokerConnection).all():
            if r.broker != broker:
                r.is_active = False

        db.commit()
    finally:
        db.close()

    # Sync runtime environment & config
    if req.api_key:
        config.api_key = req.api_key
    if req.api_secret:
        config.api_secret = req.api_secret

    if broker == "dhan":
        if req.api_key:
            os.environ["DHAN_CLIENT_ID"] = req.api_key
        if req.api_secret:
            os.environ["DHAN_ACCESS_TOKEN"] = req.api_secret

    config.broker_name = broker

    return {
        "status": "success",
        "saved": broker,
        "message": f"✓ {broker.upper()} API credentials attached & activated successfully!"
    }

@router.post("/{broker}/test")
def test_broker(broker: str):
    """Try to connect with the saved credentials via BrokerFactory."""
    broker = broker.lower().strip()
    db = SessionLocal()
    try:
        row = db.query(BrokerConnection).filter(BrokerConnection.broker == broker).first()
    finally:
        db.close()

    api_key = row.api_key if row else os.environ.get("DHAN_CLIENT_ID", "")
    api_secret = row.api_secret if row else os.environ.get("DHAN_ACCESS_TOKEN", "")

    if not api_key and not api_secret and broker != "mock":
        raise HTTPException(status_code=404, detail="No saved credentials found for this broker")

    try:
        from ..brokers.factory import BrokerFactory
        b = BrokerFactory.get_broker(
            broker,
            api_key=api_key,
            api_secret=api_secret,
            capital=getattr(config, "capital", 1000000.0),
        )
        connected = b.connect()
        return {"broker": broker, "connected": bool(connected), "message": "Connection verified" if connected else "Failed to connect with provided credentials"}
    except Exception as e:
        return {"broker": broker, "connected": False, "error": str(e)}

@router.post("/{broker}/activate")
def activate_broker(broker: str):
    """Mark a broker active for order execution."""
    broker = broker.lower().strip()
    if broker not in SUPPORTED_BROKERS:
        raise HTTPException(status_code=400, detail="Unsupported broker")

    db = SessionLocal()
    try:
        for r in db.query(BrokerConnection).all():
            r.is_active = (r.broker == broker)
        db.commit()
    finally:
        db.close()

    config.broker_name = broker
    return {"status": "success", "active": broker}
