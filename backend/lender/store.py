"""Database-backed offer store: one row per (candidate, product) push, persisted in SQLite. Thread-safe."""
import threading
from datetime import datetime, timezone
from typing import Optional

from database.db import session_scope
from database.models import Application, Offer


def _to_dict(o: Offer) -> dict:
    return {
        "offer_id": o.offer_id, "user_id": o.user_id, "candidate_ref": o.candidate_ref,
        "lender": o.lender, "product_id": o.product_id, "product_name": o.product_name,
        "interest_rate": o.interest_rate, "message": o.message or "", "status": o.status,
        "created_at": o.pushed_at, "responded_at": o.responded_at,
    }


class OfferStore:
    def __init__(self):
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock, session_scope() as s:
            s.query(Offer).delete()

    def create(self, *, user_id: str, candidate_ref: str, lender: str, product: dict, message: str) -> Optional[dict]:
        """Returns the new offer, or None if this lender already has a live offer for the same candidate+product."""
        with self._lock, session_scope() as s:
            live = s.query(Offer).filter(
                Offer.user_id == user_id, Offer.product_id == product["product_id"], Offer.lender == lender,
                Offer.status.in_(("pushed", "accepted"))).first()
            if live is not None:
                return None
            offer = Offer(
                user_id=user_id, candidate_ref=candidate_ref, lender=lender, product_id=product["product_id"],
                product_name=product["name"], interest_rate=product["interest_rate"], message=message,
                status="pushed", pushed_at=datetime.now(timezone.utc).isoformat())
            s.add(offer)
            s.flush()
            return _to_dict(offer)

    def for_user(self, user_id: str) -> list[dict]:
        with session_scope() as s:
            return [_to_dict(o) for o in s.query(Offer).filter(Offer.user_id == user_id).order_by(Offer.offer_id)]

    def for_lender(self, lender: str) -> list[dict]:
        with session_scope() as s:
            return [_to_dict(o) for o in s.query(Offer).filter(Offer.lender == lender).order_by(Offer.offer_id)]

    def respond(self, offer_id: int, user_id: str, accept: bool) -> Optional[dict]:
        """Consumer accepts/rejects. Returns None if no such offer for that user. Only 'pushed' offers can be answered."""
        with self._lock, session_scope() as s:
            offer = s.get(Offer, offer_id)
            if offer is None or offer.user_id != user_id:
                return None
            if offer.status != "pushed":
                return dict(_to_dict(offer), _already_answered=True)
            offer.status = "accepted" if accept else "rejected"
            offer.responded_at = datetime.now(timezone.utc).isoformat()
            return _to_dict(offer)

    def has_accepted(self, user_id: str, lender: str) -> bool:
        with session_scope() as s:
            return s.query(Offer).filter(Offer.user_id == user_id, Offer.lender == lender,
                                         Offer.status == "accepted").first() is not None


def _app_dict(a: Application) -> dict:
    return {
        "application_id": a.application_id, "user_id": a.user_id, "lender": a.lender,
        "product_id": a.product_id, "product_name": a.product_name, "interest_rate": a.interest_rate,
        "requested_amount": a.requested_amount, "tenure_months": a.tenure_months, "purpose": a.purpose,
        "applicant_name": a.applicant_name, "phone": a.phone, "score_at_submit": a.score_at_submit,
        "status": a.status, "lender_note": a.lender_note or "", "created_at": a.created_at,
        "decided_at": a.decided_at,
    }


class ApplicationStore:
    """Pre-approval applications a consumer sends to one chosen lender."""

    def __init__(self):
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock, session_scope() as s:
            s.query(Application).delete()

    def create(self, **fields) -> Optional[dict]:
        """Returns the new application, or None if this user already has a live one for the same lender+product."""
        with self._lock, session_scope() as s:
            live = s.query(Application).filter(
                Application.user_id == fields["user_id"], Application.lender == fields["lender"],
                Application.product_id == fields["product_id"],
                Application.status.in_(("submitted", "approved"))).first()
            if live is not None:
                return None
            app = Application(status="submitted", created_at=datetime.now(timezone.utc).isoformat(), **fields)
            s.add(app)
            s.flush()
            return _app_dict(app)

    def for_user(self, user_id: str) -> list[dict]:
        with session_scope() as s:
            return [_app_dict(a) for a in s.query(Application).filter(Application.user_id == user_id)
                    .order_by(Application.application_id.desc())]

    def for_lender(self, lender: str) -> list[dict]:
        with session_scope() as s:
            return [_app_dict(a) for a in s.query(Application).filter(Application.lender == lender)
                    .order_by(Application.application_id.desc())]

    def decide(self, application_id: int, lender: str, approve: bool, note: str) -> Optional[dict]:
        """None if the application isn't this lender's; otherwise the row (with _already_decided when final)."""
        with self._lock, session_scope() as s:
            a = s.get(Application, application_id)
            if a is None or a.lender != lender:
                return None
            if a.status != "submitted":
                return dict(_app_dict(a), _already_decided=True)
            a.status = "approved" if approve else "declined"
            a.lender_note = note
            a.decided_at = datetime.now(timezone.utc).isoformat()
            return _app_dict(a)
