"""
Bank Partner API — a deliberately separate mock "bank" service the AltCredit app calls to
pre-approve a recommended product. It has its own process, port and folder; the only coupling
is the HTTP contract below and a shared API key.

Run:   uvicorn app:app --app-dir bank-partner-api --port 8100
Auth:  every endpoint except GET / requires the header `X-API-Key: <BANK_API_KEY>`
       (env BANK_API_KEY, default "dev-bank-key" — MVP mock, never use in production).

Endpoints
  POST /preapprove                 -> pre-approval decision for (applicant_ref, score, product)
  GET  /offer-status/{application_id}
The decision logic is a simple mock: score margin over the product minimum drives the outcome.
No PII is ever sent to or stored by this service — only an opaque applicant_ref and the score.
"""
import hmac
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Bank Partner API (mock)", version="1.0.0")

_lock = threading.Lock()
_applications: dict[str, dict] = {}


def _api_key() -> str:
    return os.environ.get("BANK_API_KEY", "dev-bank-key")


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if not x_api_key or not hmac.compare_digest(x_api_key, _api_key()):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


class PreapproveIn(BaseModel):
    applicant_ref: str = Field(min_length=1)
    score: int = Field(ge=0, le=1000)
    risk_category: str
    product_id: str
    product_name: str
    min_score_required: int = Field(ge=0, le=1000)
    interest_rate: float = 0


class PreapproveOut(BaseModel):
    application_id: str
    decision: Literal["pre_approved", "manual_review", "declined"]
    credit_limit: int
    apr: float
    reason: str
    valid_until: str


class OfferStatusOut(BaseModel):
    application_id: str
    status: Literal["pre_approved", "manual_review", "declined"]
    product_id: str
    credit_limit: int
    created_at: str
    valid_until: str


def _decide(body: PreapproveIn) -> tuple[str, int, str]:
    margin = body.score - body.min_score_required
    if margin < 0:
        return "declined", 0, f"Score {body.score} is {-margin} points below the {body.min_score_required} required."
    if margin < 25:
        return "manual_review", 0, "Score is only marginally above the minimum; an underwriter will review."
    limit = int(round(body.score * 10 / 500.0)) * 500   # e.g. score 750 -> 7,500
    return "pre_approved", limit, f"Score {body.score} clears the {body.min_score_required} minimum by {margin} points."


@app.get("/")
def health():
    return {"status": "ok", "service": "bank-partner-api"}


@app.post("/preapprove", response_model=PreapproveOut, dependencies=[Depends(require_api_key)])
def preapprove(body: PreapproveIn):
    decision, limit, reason = _decide(body)
    now = datetime.now(timezone.utc)
    valid_until = (now + timedelta(days=30)).isoformat()
    application_id = "APP-" + uuid.uuid4().hex[:10].upper()
    with _lock:
        _applications[application_id] = {
            "application_id": application_id, "status": decision, "product_id": body.product_id,
            "credit_limit": limit, "created_at": now.isoformat(), "valid_until": valid_until,
        }
    return PreapproveOut(application_id=application_id, decision=decision, credit_limit=limit,
                         apr=body.interest_rate, reason=reason, valid_until=valid_until)


@app.get("/offer-status/{application_id}", response_model=OfferStatusOut, dependencies=[Depends(require_api_key)])
def offer_status(application_id: str):
    with _lock:
        record = _applications.get(application_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Unknown application_id")
    return OfferStatusOut(**record)
