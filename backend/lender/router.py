"""
Lender (business user) portal API — a separate, authenticated surface from the consumer API.

  POST /lender/login                 -> bearer token (mock credentials from env, see below)
  GET  /lender/candidates            -> filterable candidate list (user_id, score, band)   [auth]
  GET  /lender/candidates/{id}       -> full score analysis (same as the consumer dashboard);
                                        contact PII ONLY after acceptance                     [auth]
  POST /lender/offers                -> push a product offer to candidate(s)       [auth]
  GET  /lender/offers                -> this lender's offers and their status      [auth]

Lenders identify candidates by their platform `user_id` (also accepted: the HMAC `candidate_ref`).
Personal contact details — name, address, phone — are withheld server-side: they are never in
list/detail responses until the candidate has accepted an offer from *this* lender. The detail view
shows the same score analysis the consumer sees (breakdown, explanation, ML cross-check, products).

Credentials (MVP mock; override via env): LENDER_USERNAME=lender, LENDER_PASSWORD=lender123,
LENDER_REF_SECRET=dev-ref-secret.
"""
import hashlib
import hmac
import os
import secrets
import time
from typing import Callable, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from backend.lender.pii import get_pii
from backend.lender.store import OfferStore
from common.schemas import LenderLoginRequest, Product, PushOffersRequest, ScoreResult

TOKEN_TTL_SECONDS = 8 * 3600


def candidate_ref(user_id: str) -> str:
    secret = os.environ.get("LENDER_REF_SECRET", "dev-ref-secret").encode()
    return "C-" + hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()[:10]


def build_lender_router(
    get_demographics: Callable[[], list[dict]],
    get_scores: Callable[[], dict[str, ScoreResult]],
    get_products: Callable[[], list[Product]],
    get_analysis: Callable[[str], Optional[dict]],
    store: OfferStore,
) -> APIRouter:
    router = APIRouter(prefix="/lender", tags=["lender"])
    tokens: dict[str, tuple[str, float]] = {}   # token -> (username, expiry)

    def require_lender(authorization: Optional[str] = Header(default=None)) -> str:
        scheme, _, token = (authorization or "").partition(" ")
        entry = tokens.get(token) if scheme.lower() == "bearer" else None
        if entry is None or entry[1] < time.time():
            tokens.pop(token, None)
            raise HTTPException(status_code=401, detail="Lender login required",
                                headers={"WWW-Authenticate": "Bearer"})
        return entry[0]

    def _index() -> dict[str, dict]:
        """Resolve either a user_id or a candidate_ref to the demographics record."""
        index = {}
        for d in get_demographics():
            index[d["user_id"]] = d
            index[candidate_ref(d["user_id"])] = d
        return index

    @router.post("/login")
    def login(body: LenderLoginRequest):
        user_ok = hmac.compare_digest(body.username.strip().lower(), os.environ.get("LENDER_USERNAME", "lender").lower())
        pass_ok = hmac.compare_digest(body.password, os.environ.get("LENDER_PASSWORD", "lender123"))
        if not (user_ok and pass_ok):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = secrets.token_urlsafe(32)
        tokens[token] = (body.username, time.time() + TOKEN_TTL_SECONDS)
        return {"token": token, "token_type": "bearer", "expires_in": TOKEN_TTL_SECONDS}

    def _latest_status(user_id: str, lender: str) -> Optional[str]:
        mine = [o for o in store.for_lender(lender) if o["user_id"] == user_id]
        return mine[-1]["status"] if mine else None

    @router.get("/candidates")
    def candidates(
        min_score: int = Query(0, ge=0, le=1000),
        max_score: int = Query(1000, ge=0, le=1000),
        city_tier: Optional[str] = Query(None),
        risk_category: Optional[str] = Query(None),
        lender: str = Depends(require_lender),
    ):
        scores = get_scores()
        out = []
        for demo in get_demographics():
            uid = demo["user_id"]
            score = scores.get(uid)
            if score is None or not (min_score <= score.total_score <= max_score):
                continue
            if city_tier and demo.get("city_tier") != city_tier:
                continue
            if risk_category and score.risk_category.lower() != risk_category.lower():
                continue
            # explicit allow-list: name/address/phone can never leak through here
            out.append({
                "user_id": uid,
                "candidate_ref": candidate_ref(uid),
                "score": score.total_score,
                "risk_category": score.risk_category,
                "city_tier": demo.get("city_tier", "unknown"),
                "offer_status": _latest_status(uid, lender),
                "pii_unlocked": store.has_accepted(uid, lender),
            })
        out.sort(key=lambda c: -c["score"])
        return out

    @router.get("/candidates/{ref}")
    def candidate_detail(ref: str, lender: str = Depends(require_lender)):
        demo = _index().get(ref)
        if demo is None:
            raise HTTPException(status_code=404, detail="Unknown candidate")
        uid = demo["user_id"]
        analysis = get_analysis(uid)   # score, ml_score, explanation, recommendations, features
        if analysis is None:
            raise HTTPException(status_code=404, detail="No score available for this candidate")
        detail = {
            **analysis,
            "user_id": uid,
            "candidate_ref": candidate_ref(uid),
            # non-contact profile facts a lender needs; NO name / address / phone
            "profile": {k: demo.get(k) for k in ("age", "employment_status", "education_level",
                                                  "monthly_income", "city_tier") if k in demo},
            "offer_status": _latest_status(uid, lender),
            "pii_unlocked": False,
        }
        if store.has_accepted(uid, lender):
            detail["pii_unlocked"] = True
            detail["contact"] = get_pii(uid)
        return detail

    @router.post("/offers")
    def push_offers(body: PushOffersRequest, lender: str = Depends(require_lender)):
        product = next((p for p in get_products() if p.product_id == body.product_id), None)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Unknown product {body.product_id}")
        targets = [*body.user_ids, *body.candidate_refs]
        if not targets:
            raise HTTPException(status_code=422, detail="user_ids must not be empty")
        index, scores = _index(), get_scores()
        results = []
        for target in targets:
            demo = index.get(target)
            if demo is None:
                results.append({"user_id": target, "status": "unknown_candidate"})
                continue
            uid = demo["user_id"]
            score = scores.get(uid)
            if score is None or score.total_score < product.min_score_required:
                results.append({"user_id": uid, "status": "ineligible",
                                "detail": f"Score below product minimum {product.min_score_required}"})
                continue
            offer = store.create(user_id=uid, candidate_ref=candidate_ref(uid), lender=lender,
                                 product=product.model_dump(), message=body.message)
            if offer is None:
                results.append({"user_id": uid, "status": "duplicate"})
            else:
                results.append({"user_id": uid, "status": "pushed", "offer_id": offer["offer_id"]})
        return {"product_id": product.product_id, "results": results}

    @router.get("/offers")
    def my_offers(lender: str = Depends(require_lender)):
        return [{k: v for k, v in o.items() if k != "lender"} for o in store.for_lender(lender)]

    return router
