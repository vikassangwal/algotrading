import logging
import os
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

from .config import config
from .engine import FusedSignal
from .risk_manager import risk_manager
from .data.provider import DataProvider
from .db import SessionLocal, TradeRecord as DBTradeRecord
import json

logger = logging.getLogger("elco.execution")


def live_trading_enabled() -> bool:
    """Real broker orders require BOTH: paper_mode off AND the explicit
    LIVE_TRADING=true env flag. This double gate prevents accidental
    real-money orders — flipping paper_mode alone is not enough."""
    env_flag = os.getenv("LIVE_TRADING", "false").strip().lower() == "true"
    return (not config.paper_mode) and env_flag

@dataclass
class TradeRecord:
    trade_id: str
    symbol: str
    action: str # BUY or SELL
    qty: int
    entry_price: float
    timestamp: str
    reasons: List[str]
    status: str = "OPEN"
    exit_price: float = 0.0
    pnl: float = 0.0
    # Mandatory risk plan (R3): attached at entry — no naked positions, ever.
    stop_loss: float = 0.0
    target: float = 0.0
    # Broker order id (live mode) — lets us VERIFY the order actually traded.
    broker_order_id: str = ""
    # Exit discipline (D1/D2): original 1R distance + best price seen so far.
    initial_risk: float = 0.0
    peak_price: float = 0.0

class ExecutionEngine:
    def __init__(self, provider: DataProvider):
        self.provider = provider
        self.journal: List[TradeRecord] = []
        self.open_positions: Dict[str, TradeRecord] = {}
        self._trade_counter = 1

    def _current_atr(self, symbol: str, period: int = 14) -> float:
        """ATR(14) from recent daily candles — used for the mandatory SL/target
        (R3). Returns 0.0 on any failure; compute_mandatory_stops then falls
        back to a 2%-of-price stop so the trade is still never naked."""
        try:
            candles = self.provider.get_candles(symbol, timeframe="1d", count=period + 10)
            if not candles or len(candles) < period + 1:
                return 0.0
            trs = []
            for prev, cur in zip(candles, candles[1:]):
                trs.append(max(
                    cur.high - cur.low,
                    abs(cur.high - prev.close),
                    abs(cur.low - prev.close),
                ))
            recent = trs[-period:]
            return float(sum(recent) / len(recent)) if recent else 0.0
        except Exception as e:
            logger.warning(f"ATR fetch failed for {symbol}: {e}")
            return 0.0

    def get_journal(self) -> List[Dict[str, Any]]:
        return [trade.__dict__ for trade in reversed(self.journal)]

    def get_pnl_summary(self) -> Dict[str, float]:
        realized_pnl = sum(t.pnl for t in self.journal if t.status == "CLOSED")
        unrealized_pnl = 0.0
        
        for symbol, trade in self.open_positions.items():
            try:
                ltp = self.provider.get_quote(symbol).ltp
                if trade.action == "BUY":
                    unrealized_pnl += (ltp - trade.entry_price) * trade.qty
                else:
                    unrealized_pnl += (trade.entry_price - ltp) * trade.qty
            except Exception:
                pass
                
        return {
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(realized_pnl + unrealized_pnl, 2)
        }

    def execute_signal(self, signal: FusedSignal, requested_allocation: float) -> bool:
        """
        Executes a trade if it's safe and there is a strong signal.
        Paper mode records a simulated trade; live mode routes a real order
        to the broker ONLY when live_trading_enabled() is true.
        """
        if signal.action == "NEUTRAL":
            logger.info(f"Signal for {signal.symbol} is NEUTRAL. No execution.")
            return False

        if signal.symbol in self.open_positions:
            logger.info(f"Position already open for {signal.symbol}. Skipping entry.")
            return False

        # MANDATORY RULES (R1/R2/R5/R6/R7) — checked for EVERY trade, every
        # caller, no bypass. A rejected trade never reaches sizing or a broker.
        from .trading_rules import check_entry_rules
        is_live = (not config.paper_mode) and live_trading_enabled()
        verdict = check_entry_rules(
            signal.symbol, is_live=is_live,
            open_positions_count=len(self.open_positions),
        )
        if not verdict.allowed:
            logger.warning(f"TRADE BLOCKED by rules: {verdict.reason}")
            return False

        # Determine execution price and size FIRST, so live and paper agree.
        try:
            current_price = self.provider.get_quote(signal.symbol).ltp
        except Exception as e:
            logger.error(f"Failed to get quote for execution: {e}")
            return False

        if not current_price or current_price <= 0:
            logger.error(f"Invalid price for {signal.symbol}: {current_price}")
            return False

        qty = int(requested_allocation // current_price)
        if qty <= 0:
            logger.warning("Requested allocation too small for 1 qty.")
            return False

        actual_allocation = qty * current_price

        broker_order_id = ""
        # 1. LIVE Trading Logic (Dhan Broker) — gated behind explicit flag
        if not config.paper_mode:
            if not live_trading_enabled():
                logger.warning(
                    "paper_mode is off but LIVE_TRADING env flag is not 'true' — "
                    "refusing to place a real order. Set LIVE_TRADING=true to enable."
                )
                return False

            logger.info("Executing LIVE trade via Dhan Broker API...")
            try:
                if hasattr(self.provider, 'rest_client') and self.provider.rest_client is not None:
                    rest_client = self.provider.rest_client

                    # Place a Market Order with the ACTUAL computed quantity
                    order_id = rest_client.place_order(
                        symbol=signal.symbol,
                        quantity=qty,
                        transaction_type=signal.action
                    )

                    if not order_id:
                        logger.error("Dhan API rejected the live order or failed to return order_id.")
                        return False

                    broker_order_id = str(order_id)
                    logger.info(f"LIVE TRADE EXECUTED on Dhan: {signal.action} {qty} {signal.symbol}. Order ID: {order_id}")
                else:
                    logger.error("Dhan API is not initialized. Cannot execute LIVE trade.")
                    return False
            except Exception as e:
                logger.error(f"Live trade execution failed: {e}")
                return False

        # 2. Update Risk Manager exposure
        risk_manager.portfolio_exposure += actual_allocation

        trade_id = f"TRD-{datetime.now().strftime('%Y%m%d')}-{self._trade_counter:04d}"
        self._trade_counter += 1

        # R3/R4 — mandatory stop-loss + target attached at entry (ATR-based).
        from .trading_rules import compute_mandatory_stops, record_entry
        atr = self._current_atr(signal.symbol)
        stops = compute_mandatory_stops(signal.action, current_price, atr)

        trade = TradeRecord(
            trade_id=trade_id,
            symbol=signal.symbol,
            action=signal.action,
            qty=qty,
            entry_price=current_price,
            timestamp=datetime.now().isoformat(),
            reasons=signal.reasons + [
                f"Mandatory SL {stops['stop_loss']} / target {stops['target']} (R3)"
            ],
            stop_loss=stops["stop_loss"],
            target=stops["target"],
            broker_order_id=broker_order_id,
            initial_risk=round(abs(current_price - stops["stop_loss"]), 2),
            peak_price=current_price,
        )

        self.open_positions[signal.symbol] = trade
        self.journal.append(trade)
        record_entry()  # feeds the max-trades/day brake (R5)

        # Derive analytics dimensions from the signal: the highest-|score|
        # contributing module is the strategy/setup that drove the entry.
        strategy = None
        setup = None
        try:
            contribs = getattr(signal, "contributions", {}) or {}
            if contribs:
                top = max(contribs.items(), key=lambda kv: abs(getattr(kv[1], "score", 0) or 0))
                strategy = top[0]
                setup = f"{top[0]}:{'bull' if (getattr(top[1], 'score', 0) or 0) >= 0 else 'bear'}"
        except Exception:
            pass
        timeframe = getattr(getattr(signal, "style", None), "value", None)

        # Write to Database
        try:
            db = SessionLocal()
            db_trade = DBTradeRecord(
                symbol=trade.symbol,
                action=trade.action,
                quantity=trade.qty,
                price=trade.entry_price,
                status=trade.status,
                pnl=trade.pnl,
                reason=json.dumps(trade.reasons),
                strategy=strategy,
                timeframe=timeframe,
                setup=setup,
            )
            db.add(db_trade)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to write trade to database: {e}")

        mode = "LIVE" if not config.paper_mode else "PAPER"
        logger.info(f"{mode} TRADE EXECUTED: {signal.action} {qty} {signal.symbol} @ {current_price}")
        return True

    def close_position(self, symbol: str, exit_price: float = None) -> bool:
        """Close an open position: realize PnL, release exposure, mark CLOSED,
        and feed the realized PnL back into the risk manager's daily tally so
        the daily-loss hard stop can actually fire."""
        trade = self.open_positions.get(symbol)
        if trade is None:
            logger.warning(f"No open position to close for {symbol}.")
            return False

        if exit_price is None:
            try:
                exit_price = self.provider.get_quote(symbol).ltp
            except Exception as e:
                logger.error(f"Failed to get quote to close {symbol}: {e}")
                return False

        if trade.action == "BUY":
            pnl = (exit_price - trade.entry_price) * trade.qty
        else:  # SELL / short
            pnl = (trade.entry_price - exit_price) * trade.qty

        trade.exit_price = exit_price
        trade.pnl = round(pnl, 2)
        trade.status = "CLOSED"

        # Release exposure that this position was holding
        risk_manager.portfolio_exposure = max(
            0.0, risk_manager.portfolio_exposure - trade.qty * trade.entry_price
        )
        # Feed realized PnL into the daily tally (drives the daily-loss stop)
        risk_manager.daily_pnl += trade.pnl

        del self.open_positions[symbol]

        # Feed the rules engine (R6 cooldown / R7 consecutive-loss breaker).
        # A stop-loss exit = price at or beyond the mandatory SL level.
        try:
            from .trading_rules import record_exit
            sl = getattr(trade, "stop_loss", 0.0) or 0.0
            was_sl = bool(sl) and (
                (trade.action == "BUY" and exit_price <= sl)
                or (trade.action != "BUY" and exit_price >= sl)
            )
            record_exit(symbol, trade.pnl, was_stop_loss=was_sl)
        except Exception as e:
            logger.error(f"Rules exit-tracking failed for {symbol}: {e}")

        # Persist the close to the DB
        try:
            db = SessionLocal()
            db_trade = (
                db.query(DBTradeRecord)
                .filter(DBTradeRecord.symbol == symbol, DBTradeRecord.status == "OPEN")
                .order_by(DBTradeRecord.id.desc())
                .first()
            )
            if db_trade is not None:
                db_trade.status = "CLOSED"
                db_trade.pnl = trade.pnl
                db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to persist position close for {symbol}: {e}")

        logger.info(f"POSITION CLOSED: {symbol} @ {exit_price} | realized PnL {trade.pnl}")
        return True
