"""In-memory offer store (MVP: resets on restart). Thread-safe; one record per (candidate, product) push."""
import threading
from datetime import datetime, timezone
from typing import Optional


class OfferStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._offers: dict[int, dict] = {}
        self._next_id = 1

    def clear(self) -> None:
        with self._lock:
            self._offers.clear()
            self._next_id = 1

    def create(self, *, user_id: str, candidate_ref: str, lender: str, product: dict, message: str) -> Optional[dict]:
        """Returns the new offer, or None if this lender already has a live offer for the same candidate+product."""
        with self._lock:
            for o in self._offers.values():
                if (o["user_id"] == user_id and o["product_id"] == product["product_id"]
                        and o["lender"] == lender and o["status"] in ("pushed", "accepted")):
                    return None
            offer = {
                "offer_id": self._next_id, "user_id": user_id, "candidate_ref": candidate_ref,
                "lender": lender, "product_id": product["product_id"], "product_name": product["name"],
                "interest_rate": product["interest_rate"], "message": message, "status": "pushed",
                "created_at": datetime.now(timezone.utc).isoformat(), "responded_at": None,
            }
            self._offers[self._next_id] = offer
            self._next_id += 1
            return dict(offer)

    def for_user(self, user_id: str) -> list[dict]:
        with self._lock:
            return [dict(o) for o in self._offers.values() if o["user_id"] == user_id]

    def for_lender(self, lender: str) -> list[dict]:
        with self._lock:
            return [dict(o) for o in self._offers.values() if o["lender"] == lender]

    def respond(self, offer_id: int, user_id: str, accept: bool) -> Optional[dict]:
        """Consumer accepts/rejects. Returns None if no such offer for that user. Only 'pushed' offers can be answered."""
        with self._lock:
            offer = self._offers.get(offer_id)
            if offer is None or offer["user_id"] != user_id:
                return None
            if offer["status"] != "pushed":
                return dict(offer, _already_answered=True)
            offer["status"] = "accepted" if accept else "rejected"
            offer["responded_at"] = datetime.now(timezone.utc).isoformat()
            return dict(offer)

    def has_accepted(self, user_id: str, lender: str) -> bool:
        with self._lock:
            return any(o["user_id"] == user_id and o["lender"] == lender and o["status"] == "accepted"
                       for o in self._offers.values())
