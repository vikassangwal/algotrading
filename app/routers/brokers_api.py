"""Broker connection registry + admin API.

Lets the admin attach ANY broker (Zerodha / Upstox / Angel One / Fyers / Dhan /
mock) from the panel: save credentials, list connections, test a connection,
and mark one active. Credentials are persisted to the DB and masked on read.

Live order routing still respects the paper/live safety gate in execution.py.
"""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from ..config import config, BrokerName
from ..db import SessionLocal, Base, engine as db_engine
from sqlalchemy import Column, Integer, String, Boolean

logger = logging.getLogger("elco.brokers")

router = APIRouter(prefix="/api/brokers", tags=["brokers"])

# Brokers the panel can attach. api_secret meaning varies per broker
# (e.g. Dhan uses client_id/access_token) but the two-field shape is uniform.
SUPPORTED_BROKERS = [
    "mock", "zerodha", "upstox", "angel_one", "fyers", "dhan",
    "mstock", "kotak_neo",
]


class BrokerConnection(Base):
    __tablename__ = "broker_connections"
    id = Column(Integer, primary_key=True, index=True)
    broker = Column(String, unique=True, index=True)
    api_key = Column(String, default="")
    api_secret = Column(String, default="")
    is_active = Column(Boolean, default=False)


def _ensure_table():
    try:
        Base.metadata.create_all(bind=db_engine, tables=[BrokerConnection.__table__])
    except Exception as e:
        logger.error(f"Failed to ensure broker table: {e}")


_ensure_table()


def _mask(secret: str) -> str:
    if not secret:
        return ""
    return secret[:3] + "*" * max(len(secret) - 3, 4)


class BrokerCredsRequest(BaseModel):
    broker: str
    api_key: str = ""
    api_secret: str = ""


def _get_verify_token():
    # Imported lazily to avoid a circular import with main.py
    from ..main import verify_token
    return verify_token


@router.get("", dependencies=[])
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

    return {
        "supported": SUPPORTED_BROKERS,
        "active": config.broker.value if hasattr(config.broker, "value") else str(config.broker),
        "connections": [saved.get(b, {"broker": b, "configured": False, "is_active": False}) for b in SUPPORTED_BROKERS],
    }


@router.post("", dependencies=[Depends(_get_verify_token())])
def save_broker(req: BrokerCredsRequest):
    """Attach / update a broker's credentials."""
    broker = req.broker.lower().strip()
    if broker not in SUPPORTED_BROKERS:
        raise HTTPException(status_code=400, detail=f"Unsupported broker. Choose from {SUPPORTED_BROKERS}")
    db = SessionLocal()
    try:
        row = db.query(BrokerConnection).filter(BrokerConnection.broker == broker).first()
        if row is None:
            row = BrokerConnection(broker=broker)
            db.add(row)
        row.api_key = req.api_key
        row.api_secret = req.api_secret
        db.commit()
    finally:
        db.close()
    return {"saved": broker}


@router.post("/{broker}/test", dependencies=[Depends(_get_verify_token())])
def test_broker(broker: str):
    """Try to connect with the saved credentials via BrokerFactory."""
    broker = broker.lower().strip()
    db = SessionLocal()
    try:
        row = db.query(BrokerConnection).filter(BrokerConnection.broker == broker).first()
    finally:
        db.close()
    if row is None and broker != "mock":
        raise HTTPException(status_code=404, detail="No saved credentials for this broker")
    try:
        from ..brokers.factory import BrokerFactory
        b = BrokerFactory.get_broker(
            broker,
            api_key=(row.api_key if row else ""),
            api_secret=(row.api_secret if row else ""),
            capital=config.capital,
        )
        connected = b.connect()
        return {"broker": broker, "connected": bool(connected)}
    except Exception as e:
        return {"broker": broker, "connected": False, "error": str(e)}


@router.post("/{broker}/activate", dependencies=[Depends(_get_verify_token())])
def activate_broker(broker: str):
    """Mark a broker active (the one order routing will use)."""
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
    # Reflect into runtime config
    try:
        config.broker = BrokerName(broker)
    except ValueError:
        config.broker_name = broker
    return {"active": broker}
