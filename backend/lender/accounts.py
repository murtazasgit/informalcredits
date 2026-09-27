"""Lender registration/login, persisted in the database. Passwords use the same PBKDF2 hashing as consumers."""
import os
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func

from backend.auth import hash_password, verify_password
from database.db import session_scope
from database.models import Lender

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
_DUMMY_HASH = hash_password("not-a-real-password")


def register(bank_name: str, username: str, password: str) -> Optional[dict]:
    """Returns the new lender, or None if that username or bank name is already registered."""
    bank_name, username = bank_name.strip(), username.strip()
    with session_scope() as s:
        if s.query(Lender).filter(func.lower(Lender.username) == username.lower()).first() is not None:
            return None
        if s.query(Lender).filter(func.lower(Lender.bank_name) == bank_name.lower()).first() is not None:
            return None
        s.add(Lender(lender_id=username, username=username, bank_name=bank_name,
                     password_hash=hash_password(password), created_at=datetime.now(timezone.utc).isoformat()))
    return {"username": username, "bank_name": bank_name}


def authenticate(username: str, password: str) -> Optional[dict]:
    with session_scope() as s:
        row = s.query(Lender).filter(func.lower(Lender.username) == username.strip().lower()).first()
        ok = verify_password(password, row.password_hash if row else _DUMMY_HASH)
        return {"username": row.username, "bank_name": row.bank_name} if (row and ok) else None


def list_lenders() -> list[dict]:
    with session_scope() as s:
        return [{"lender_id": r.username, "bank_name": r.bank_name}
                for r in s.query(Lender).order_by(Lender.bank_name)]


def bank_names() -> dict[str, str]:
    return {l["lender_id"]: l["bank_name"] for l in list_lenders()}


def ensure_demo_lender() -> None:
    """Keep the MVP demo lender (env credentials) available so the portal works out of the box."""
    username = os.environ.get("LENDER_USERNAME", "lender")
    with session_scope() as s:
        exists = s.query(Lender).filter(func.lower(Lender.username) == username.lower()).first()
    if exists is None:
        register("Demo Bank", username, os.environ.get("LENDER_PASSWORD", "lender123"))
