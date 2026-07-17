"""ELCO runtime configuration.

Everything here is admin-togglable at runtime via the Admin API.
Defaults are conservative: paper mode only, auto-trade OFF.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Dict, List

from pydantic import BaseModel, Field, SecretStr

DISCLAIMER = (
    "ELCO is a decision-support tool, not financial advice. Signals are "
    "probabilistic estimates with confidence ranges — no signal is guaranteed "
    "or 100% accurate. Trading involves risk of loss."
)


class TradingStyle(str, Enum):
    SCALPING = "scalping"
    INTRADAY = "intraday"
    SWING = "swing"
    POSITIONAL = "positional"
    OPTIONS = "options"
    LONG_TERM = "long_term"


class AssetClass(str, Enum):
    EQUITY = "equity"
    FNO = "fno"
    COMMODITY = "commodity"
    CURRENCY = "currency"


class AutoTradeState(str, Enum):
    OFF = "off"
    ACTIVE = "active"
    HALTED = "halted"  # tripped by risk manager / crash-risk radar


class BrokerName(str, Enum):
    MOCK = "mock"
    ZERODHA = "zerodha"
    UPSTOX = "upstox"
    ANGEL_ONE = "angel_one"
    FYERS = "fyers"
    DHAN = "dhan"
    MSTOCK = "mstock"
    KOTAK_NEO = "kotak_neo"


class RiskSettings(BaseModel):
    max_position_pct: float = Field(5.0, ge=0.1, le=100, description="Max % of capital per position")
    max_portfolio_exposure_pct: float = Field(60.0, ge=1, le=100)
    stop_loss_pct: float = Field(2.0, ge=0.1, le=50)
    daily_loss_limit_pct: float = Field(3.0, ge=0.1, le=50, description="Hard auto-stop for the day")
    crash_risk_halt_threshold: float = Field(75.0, ge=0, le=100, description="Auto-halt when radar score exceeds this")


class ApiKeyEntry(BaseModel):
    provider: str
    api_key: SecretStr
    api_secret: Optional[SecretStr] = None

    def masked(self) -> dict:
        def mask(s: Optional[SecretStr]) -> Optional[str]:
            if s is None:
                return None
            raw = s.get_secret_value()
            return raw[:3] + "*" * max(len(raw) - 3, 4)
        return {"provider": self.provider, "api_key": mask(self.api_key), "api_secret": mask(self.api_secret)}


class AppConfig(BaseModel):
    """Mutable runtime config — single source of truth for the Admin Panel."""

    broker: BrokerName = BrokerName.MOCK
    capital: float = 1_000_000.0  # INR, paper capital

    # module name -> enabled
    modules_enabled: Dict[str, bool] = Field(default_factory=lambda: {
        # Core
        "technical": True,
        "fundamental": True,
        "quant": True,
        "sentiment": True,
        "sector": True,
        "macro": True,
        "intermarket": True,
        "derivatives": True,
        "ratio": True,
        "news_risk": True,
        "options_flow": True,
        # Institutional (full 24-category coverage)
        "company": True,
        "financial_statement": True,
        "valuation": True,
        "credit": True,
        "volume": True,
        "order_flow": True,
        "smart_money": True,
        "behavioral": True,
        "event_driven": True,
        "cycle": True,
        "risk_analysis": True,
        "industry": True,
        "esg": True,
        "alternative_data": True,
        "portfolio_analysis": True,
    })
    asset_classes_enabled: Dict[AssetClass, bool] = Field(default_factory=lambda: {
        AssetClass.EQUITY: True,
        AssetClass.FNO: True,
        AssetClass.COMMODITY: False,
        AssetClass.CURRENCY: False,
    })
    styles_enabled: Dict[TradingStyle, bool] = Field(default_factory=lambda: {s: True for s in TradingStyle})

    risk: RiskSettings = Field(default_factory=RiskSettings)
    auto_trade: AutoTradeState = AutoTradeState.OFF
    # Execution
    paper_mode: bool = True
    
    # Broker API Credentials
    broker_name: str = "mock" # options: mock, zerodha, upstox, angelone, fyers
    api_key: str = ""
    api_secret: str = ""

    api_keys: List[ApiKeyEntry] = Field(default_factory=list)
    
    # Custom Strategies defined by the user via frontend Strategy Builder
    custom_strategies: List[Dict] = Field(default_factory=list)


# process-wide singleton (swap for DB-backed store later)
config = AppConfig()
