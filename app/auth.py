"""Lightweight authentication for ELCO.

Uses Python stdlib only (hmac / hashlib / secrets) — no extra dependencies.
Tokens are HMAC-signed and carry an expiry, so they cannot be forged without
the server secret and cannot be replayed forever.

Secrets come from the environment:
  ELCO_JWT_SECRET     - signing secret (REQUIRED in production)
  ELCO_ADMIN_PASSWORD - admin login password (REQUIRED in production)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

logger = logging.getLogger("elco.auth")

TOKEN_TTL_SECONDS = 12 * 3600  # 12 hours

# Dev fallbacks — a loud warning fires if these are used in a real deployment.
_DEV_SECRET = "dev-insecure-secret-change-me"
_DEV_PASSWORD = "admin123"


def _secret() -> str:
    s = os.getenv("ELCO_JWT_SECRET")
    if not s:
        logger.warning("ELCO_JWT_SECRET not set — using INSECURE dev secret. Set it in production.")
        return _DEV_SECRET
    return s


def _admin_password() -> str:
    p = os.getenv("ELCO_ADMIN_PASSWORD")
    if not p:
        logger.warning("ELCO_ADMIN_PASSWORD not set — using INSECURE dev password. Set it in production.")
        return _DEV_PASSWORD
    return p


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def verify_password(password: str) -> bool:
    """Constant-time comparison against the configured admin password."""
    return hmac.compare_digest(password.encode(), _admin_password().encode())


# --- Per-user password hashing (stdlib PBKDF2, no extra deps) ---------------
# Stored format: "pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>".

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Salt + PBKDF2-SHA256 hash a plaintext password for storage."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_user_password(password: str, stored: str) -> bool:
    """Constant-time verify a plaintext password against a stored hash."""
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def create_token(subject: str = "admin") -> str:
    """Create a signed token: base64(payload).base64(hmac_sha256(payload))."""
    payload = {"sub": subject, "exp": int(time.time()) + TOKEN_TTL_SECONDS, "nonce": secrets.token_hex(8)}
    payload_b = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_secret().encode(), payload_b, hashlib.sha256).digest()
    return f"{_b64(payload_b)}.{_b64(sig)}"


def verify_token(token: str) -> bool:
    """Return True iff the token is well-formed, correctly signed, and unexpired."""
    try:
        payload_part, sig_part = token.split(".")
        payload_b = _b64d(payload_part)
        expected = hmac.new(_secret().encode(), payload_b, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64d(sig_part), expected):
            return False
        payload = json.loads(payload_b)
        if int(payload.get("exp", 0)) < int(time.time()):
            return False
        return True
    except Exception:
        return False
