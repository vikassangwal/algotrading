from fastapi import APIRouter, Depends, HTTPException
from ..config import config, AppConfig, AutoTradeState
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("", response_model=AppConfig)
@router.get("/", response_model=AppConfig)
def get_config_api():
    """Retrieve runtime configuration for frontend Admin Panel."""
    return config

class ConfigUpdate(BaseModel):
    capital: Optional[float] = None
    auto_trade: Optional[str] = None
    paper_mode: Optional[bool] = None
    broker_name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    custom_strategies: Optional[List[Dict]] = None

@router.patch("", dependencies=[Depends(lambda: True)])
@router.patch("/", dependencies=[Depends(lambda: True)])
def update_config_api(update: ConfigUpdate):
    """Update runtime configuration dynamically from Admin Panel."""
    if update.capital is not None:
        config.capital = update.capital
    if update.auto_trade is not None:
        try:
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
