"""
Consumer login: user_id + password -> opaque bearer session token, all persisted in the database.

Accounts are seeded for every dataset user with SEED_USER_PASSWORD (default "altcredit123") so the demo
works out of the box; override it via env. Passwords are PBKDF2-hashed; only a hash of each session token is stored.
"""
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import Header, HTTPException
from sqlalchemy import func

from database.db import session_scope
from database.models import Account, UserSession

SESSION_TTL_SECONDS = 8 * 3600
_ITERATIONS = 200_000


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _ITERATIONS)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except ValueError:
        return False


_DUMMY_HASH = hash_password("not-a-real-password")   # keeps unknown-user logins as slow as real ones


def seed_accounts(user_ids) -> int:
    """Create an account for each user_id that lacks one. Returns how many were created."""
    default = hash_password(os.environ.get("SEED_USER_PASSWORD", "altcredit123"))
    created = 0
    with session_scope() as s:
        existing = {a for (a,) in s.query(Account.user_id)}
        for uid in user_ids:
            if uid not in existing:
                s.add(Account(user_id=uid, password_hash=default, created_at=datetime.now(timezone.utc).isoformat()))
                created += 1
    return created


def is_taken(user_id: str) -> bool:
    """Case-insensitive, so 'Priya' and 'priya' can't both exist."""
    with session_scope() as s:
        return s.query(Account).filter(func.lower(Account.user_id) == user_id.strip().lower()).first() is not None


def create_account(user_id: str, password: str) -> bool:
    """Returns False if the user_id is already taken."""
    with session_scope() as s:
        if s.query(Account).filter(func.lower(Account.user_id) == user_id.lower()).first() is not None:
            return False
        s.add(Account(user_id=user_id, password_hash=hash_password(password),
                      created_at=datetime.now(timezone.utc).isoformat()))
        return True


def issue_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with session_scope() as s:
        s.add(UserSession(token_hash=_token_hash(token), user_id=user_id,
                          expires_at=time.time() + SESSION_TTL_SECONDS))
    return token


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login(user_id: str, password: str) -> Optional[str]:
    """Returns a new session token, or None for bad credentials."""
    with session_scope() as s:
        account = s.get(Account, user_id.strip())
        ok = verify_password(password, account.password_hash if account else _DUMMY_HASH)
        if not (account and ok):
            return None
        token = secrets.token_urlsafe(32)
        s.query(UserSession).filter(UserSession.expires_at < time.time()).delete()
        s.add(UserSession(token_hash=_token_hash(token), user_id=account.user_id,
                          expires_at=time.time() + SESSION_TTL_SECONDS))
        return token


def logout(token: str) -> None:
    with session_scope() as s:
        s.query(UserSession).filter(UserSession.token_hash == _token_hash(token)).delete()


def bearer_token(authorization: Optional[str]) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    return token if scheme.lower() == "bearer" else ""


def require_user(authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency: the logged-in user_id, or 401."""
    token = bearer_token(authorization)
    if token:
        with session_scope() as s:
            row = s.get(UserSession, _token_hash(token))
            if row and row.expires_at >= time.time():
                return row.user_id
    raise HTTPException(status_code=401, detail="Login required", headers={"WWW-Authenticate": "Bearer"})
