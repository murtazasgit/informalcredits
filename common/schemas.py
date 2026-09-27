"""
COMMON SCHEMAS — the single source of truth for every data shape that crosses a module boundary.

RULE: every module (data/, scoring_engine/, ml_engine/, explainability/, reports/,
recommendations/, api/) MUST import these classes instead of redefining its own dict shape.
This is what prevents merge conflicts and integration bugs — if two people independently
invent slightly different field names for "the same thing", the API layer breaks and nobody
can tell whose version is right. Import from here, always.

If you need a new field: add it here in a PR, message the team, do NOT quietly add an extra
key in your own module's dict and hope it lines up.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date
from enum import Enum


# ---------- Enums ----------

class TransactionType(str, Enum):
    DEBIT = "Debit"
    CREDIT = "Credit"


class RiskCategory(str, Enum):
    POOR = "Poor"
    FAIR = "Fair"
    GOOD = "Good"
    EXCELLENT = "Excellent"


class FactorDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class Priority(str, Enum):
    MUST_HAVE = "must_have"
    GOOD_TO_HAVE = "good_to_have"
    STRETCH = "stretch"


# ---------- 1. Raw input schemas (owned by: data/) ----------

class Transaction(BaseModel):
    transaction_id: str
    user_id: str
    date: date
    amount: float
    category: str          # "Rent" | "Utility" | "Salary" | "Food" | "Discretionary" | ...
    type: Literal["Debit", "Credit"]
    on_time: Optional[bool] = None   # for recurring bills only


class Demographic(BaseModel):
    user_id: str
    age: int
    employment_status: str
    months_employed: int
    education_level: str            # "high_school" | "bachelor" | "masters" | "phd" | "certification"
    monthly_income: float
    city_tier: str                  # "tier-1" | "tier-2" | "tier-3"
    housing_status: str             # "own" | "rent" | "none"
    housing_months: int
    existing_credit_lines: int = 0


class Product(BaseModel):
    product_id: str
    name: str
    type: str                       # "Starter Card" | "Microloan" | "Premium Card" | ...
    min_score_required: int
    interest_rate: float


# ---------- 2. Engineered features (data/ → scoring_engine/, ml_engine/) ----------

class UserFeatures(BaseModel):
    user_id: str
    months_employed: int
    housing_status: str
    housing_months: int
    digital_bill_ontime_pct: float
    education_level: str
    spend_to_income_ratio: float
    essential_spend_pct: float
    cashflow_volatility_pct: float
    savings_days: int
    on_time_payment_pct: float
    debt_to_income_ratio: float
    credit_utilization_pct: float = 0
    delinquency_flags: list[str] = Field(default_factory=list)
    positive_habits_count: int = 0    # for bonus points (max 3 counted)
    risk_flags_count: int = 0         # for penalty points (max 3 counted, -20 each)


# ---------- 3. Score result (scoring_engine/ or ml_engine/ → explainability/, api/, reports/) ----------

class ScoreBreakdown(BaseModel):
    employment_stability: int = 0
    housing_status: int = 0
    digital_footprint: int = 0
    education: int = 0
    spend_to_income: int = 0
    expense_diversity: int = 0
    cashflow_volatility: int = 0
    savings: int = 0
    on_time_payment: int = 0
    debt_to_income: int = 0
    credit_utilization: int = 0
    delinquency: int = 0
    bonus: int = 0
    penalty: int = 0


class ScoreResult(BaseModel):
    user_id: str
    total_score: int                 # 0-1000, clamped
    risk_category: Literal["Poor", "Fair", "Good", "Excellent"]
    breakdown: ScoreBreakdown
    method: Literal["rule_based", "ml_pd"] = "rule_based"
    probability_of_default: Optional[float] = None   # only set when method == "ml_pd"


# ---------- 4. Explainability output (explainability/ → api/, reports/, frontend) ----------

class Factor(BaseModel):
    label: str
    points: int
    direction: Literal["positive", "negative"]
    text: str = ""   # natural-language line, e.g. "Utility & bill payment consistency: +45 pts (out of 70)"


class ExplainResult(BaseModel):
    user_id: str
    factors: list[Factor]
    summary_text: str


# ---------- 5. Recommendation output (recommendations/ → api/, frontend) ----------

class Recommendation(BaseModel):
    product_id: str
    name: str
    interest_rate: float
    eligible: bool
    reason: str            # e.g. "Score 742 meets minimum 650 for Starter Card"
    min_score_required: int = 0   # needed by the frontend to call /target-achievement

# ---------- 6. What-If simulator (scoring_engine/ → api/, frontend) ----------

class SimulationRequest(BaseModel):
    user_id: str
    hypothetical_changes: dict     # e.g. {"savings_days": 30} — see scoring_engine/README.md


class SimulationResult(BaseModel):
    user_id: str
    old_score: int
    new_score: int
    delta: int
    message: str


# ---------- 7. Lender / Business mode (api/ → frontend/lender-portal) ----------

class CandidateSummary(BaseModel):
    candidate_ref: str      # anonymized reference, NEVER the real user_id or name
    score: int
    risk_category: str
    city_tier: str


class OfferRequest(BaseModel):
    candidate_ref: str
    product_id: str


class OfferResult(BaseModel):
    offer_id: int
    status: Literal["pushed", "accepted", "rejected"]


class PushOffersRequest(BaseModel):
    """Lender pushes one product to one or more candidates, named by user_id (or candidate_ref)."""
    user_ids: list[str] = Field(default_factory=list)
    candidate_refs: list[str] = Field(default_factory=list)   # alternative to user_ids
    product_id: str
    message: str = ""


class LenderLoginRequest(BaseModel):
    username: str
    password: str


# ---------- 8. Lender registration and pre-approval applications ----------

class LenderRegisterRequest(BaseModel):
    bank_name: str
    username: str
    password: str


class ApplicationRequest(BaseModel):
    """Consumer -> a chosen lender. The score is always read server-side, never taken from the client."""
    lender_id: str
    product_id: str
    requested_amount: float
    tenure_months: int
    purpose: str = ""
    full_name: str
    phone: str


class ApplicationDecision(BaseModel):
    decision: str   # "approve" | "decline"
    note: str = ""
