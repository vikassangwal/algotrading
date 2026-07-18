"""Telegram alerts — the system reaches your phone.

Setup (one-time, free):
  1. Telegram par @BotFather se bot banao -> token milega
  2. Bot ko ek message bhejo, phir https://api.telegram.org/bot<TOKEN>/getUpdates
     se apna chat_id nikalo
  3. .env me daalo:  TELEGRAM_BOT_TOKEN=...  TELEGRAM_CHAT_ID=...

Without credentials the module is HONESTLY disabled — send() returns False,
status() says why, and nothing pretends a message went out. Sends are
best-effort and never block or crash trading logic.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import List, Optional

import requests

logger = logging.getLogger("elco.alerts")

MAX_LOG = 30
_recent: List[dict] = []
_lock = threading.Lock()


def _creds():
    from dotenv import load_dotenv
    load_dotenv()
    return (os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            os.getenv("TELEGRAM_CHAT_ID", "").strip())


def enabled() -> bool:
    token, chat = _creds()
    return bool(token and chat)


def send(text: str, kind: str = "info") -> bool:
    """Send a Telegram message. Returns True only on confirmed HTTP 200."""
    token, chat = _creds()
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind,
             "text": text[:200], "sent": False, "detail": ""}
    if not token or not chat:
        entry["detail"] = "disabled (no TELEGRAM_BOT_TOKEN/CHAT_ID in .env)"
        _log(entry)
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        entry["sent"] = r.status_code == 200
        entry["detail"] = f"HTTP {r.status_code}"
        if r.status_code != 200:
            logger.warning(f"Telegram send failed: HTTP {r.status_code} {r.text[:100]}")
    except Exception as e:
        entry["detail"] = str(e)[:100]
        logger.warning(f"Telegram send failed: {e}")
    _log(entry)
    return entry["sent"]


def send_async(text: str, kind: str = "info") -> None:
    """Fire-and-forget — trading logic never waits on Telegram."""
    threading.Thread(target=send, args=(text, kind), daemon=True).start()


def _log(entry: dict) -> None:
    with _lock:
        _recent.append(entry)
        if len(_recent) > MAX_LOG:
            del _recent[:-MAX_LOG]


def status() -> dict:
    token, chat = _creds()
    return {
        "enabled": bool(token and chat),
        "setup_hint": None if (token and chat) else (
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env "
            "(create a bot via @BotFather)."
        ),
        "recent": list(_recent[-10:]),
    }


# --- formatted trade alerts ---------------------------------------------------

def alert_trade(action: dict) -> None:
    """Auto-trader executed (or tried) a trade."""
    v = action.get("verification") or {}
    emoji = "✅" if action.get("executed") else "🚫"
    send_async(
        f"{emoji} <b>{action.get('signal', '?')} {action.get('symbol', '?')}</b>\n"
        f"Strategy: {action.get('strategy', '?')}\n"
        f"Executed: {action.get('executed')}\n"
        f"Verification: {v.get('status', 'n/a')}\n"
        f"Reason: {str(action.get('reason', ''))[:120]}",
        kind="trade",
    )


def alert_halt(reason: str) -> None:
    send_async(f"🛑 <b>SYSTEM HALTED</b>\n{reason[:200]}", kind="halt")


def alert_exit(symbol: str, exit_price: float, reason: str) -> None:
    send_async(f"📤 <b>EXIT {symbol}</b> @ {exit_price} ({reason})", kind="exit")
