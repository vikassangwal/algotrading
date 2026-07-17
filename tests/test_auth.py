"""Tests for the auth module — signed tokens must not be forgeable or eternal."""
import time

from app import auth


def test_password_verification():
    # Default dev password is "admin123" when env not set
    assert auth.verify_password(auth._admin_password())
    assert not auth.verify_password("wrong-password")


def test_token_roundtrip():
    token = auth.create_token("admin")
    assert auth.verify_token(token)


def test_tampered_token_rejected():
    token = auth.create_token("admin")
    # Flip a character in the payload -> signature must fail
    bad = ("X" if token[0] != "X" else "Y") + token[1:]
    assert not auth.verify_token(bad)


def test_garbage_token_rejected():
    assert not auth.verify_token("not-a-real-token")
    assert not auth.verify_token("")
    assert not auth.verify_token("admin-token-123")  # the OLD hardcoded token must NOT work


def test_expired_token_rejected(monkeypatch):
    token = auth.create_token("admin")
    # Jump past the TTL
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + auth.TOKEN_TTL_SECONDS + 10)
    assert not auth.verify_token(token)
