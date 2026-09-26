"""
AltCredit FastAPI Backend — MVP with CSV upload for instant credit scoring.
"""

import sys
import os
import json
import logging
import hashlib
import csv
import io
from datetime import datetime
from typing import Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from common.schemas import (
    ScoreResult, ExplainResult, Recommendation, Product, UserFeatures,
    SimulationRequest, SimulationResult, CandidateSummary, Factor,
    Demographic,
)
from backend.scoring_engine.engine import compute_score, simulate_change
from backend.explainability.explainer import explain_breakdown
from backend.recommendations.recommender import recommend_products
from data.feature_engineering import get_all_user_features, load_products, load_demographics


# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("altcredit")

# ---------- App ----------
app = FastAPI(
    title="AltCredit API",
    description="Alternative Credit Scoring for users with no formal credit history",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Data store ----------
REAL_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "Datasets_AltCredit")
SYNTHETIC_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")
DB_PATH = os.path.join(PROJECT_ROOT, "database", "altcredit.db")

# Global caches
_user_features: dict[str, UserFeatures] = {}
_products: list[Product] = []
_demographics: list[dict] = []
_scores: dict[str, ScoreResult] = {}


def _normalize_city_tier(val) -> str:
    if isinstance(val, int):
        return f"tier-{val}"
    s = str(val).strip().lower()
    if s in ("1", "2", "3"):
        return f"tier-{s}"
    if s.startswith("tier"):
        return s
    return "tier-1"


def _get_data_dir() -> str:
    """Use local merged data when available; otherwise use the bundled synthetic dataset."""
    merged_data_path = os.path.join(REAL_DATA_DIR, "merged_data.json")
    return REAL_DATA_DIR if os.path.isfile(merged_data_path) else SYNTHETIC_DATA_DIR


# ---------- Startup ----------
@app.on_event("startup")
def startup():
    global _user_features, _products, _demographics, _scores

    data_dir = _get_data_dir()
    logger.info("Starting AltCredit API v2.0 ...")
    logger.info(f"Using data directory: {data_dir}")

    # Load data
    logger.info("Loading data and computing features...")
    _user_features = get_all_user_features(data_dir)
    _products = [Product(**p) for p in load_products(os.path.join(data_dir, "product_catalog.json"))]

    merged_path = os.path.join(data_dir, "merged_data.json")
    demo_path = os.path.join(data_dir, "demographic_data.json")
    if os.path.exists(merged_path):
        _demographics = load_demographics(merged_path)
    elif os.path.exists(demo_path):
        _demographics = load_demographics(demo_path)
    else:
        _demographics = []

    for demo in _demographics:
        if "city_tier" in demo:
            demo["city_tier"] = _normalize_city_tier(demo["city_tier"])

    # Pre-compute scores for all users
    for uid, features in _user_features.items():
        result = compute_score(features)
        _scores[uid] = result

    logger.info(f"Ready — {len(_user_features)} users loaded, {len(_products)} products available")


# ---------- Health ----------
@app.get("/")
def health():
    return {"status": "ok", "service": "AltCredit API", "version": "2.0.0", "users_loaded": len(_user_features)}


# ---------- CSV Upload & Instant Scoring ----------

# Expected CSV columns mapping to UserFeatures
CSV_COLUMN_ALIASES = {
    # field_name: [possible csv header names]
    "months_employed": ["months_employed", "months_at_job", "employment_months", "job_months"],
    "housing_status": ["housing_status", "housing", "residence_type", "home_status"],
    "housing_months": ["housing_months", "rent_on_time_months", "months_at_address"],
    "digital_bill_ontime_pct": ["digital_bill_ontime_pct", "digital_payment_rate", "bill_payment_rate", "on_time_bills_pct"],
    "education_level": ["education_level", "education", "edu_level"],
    "monthly_income": ["monthly_income", "income", "monthly_salary"],
    "monthly_spend": ["monthly_spend", "spending", "monthly_expenses", "expenses"],
    "essential_spend_pct": ["essential_spend_pct", "essential_pct", "essential_spending_pct"],
    "cashflow_volatility_pct": ["cashflow_volatility_pct", "cashflow_volatility", "cash_flow_volatility"],
    "savings_days": ["savings_days", "savings_buffer_days"],
    "on_time_payment_pct": ["on_time_payment_pct", "on_time_rate", "payment_on_time_pct"],
    "debt_to_income_ratio": ["debt_to_income_ratio", "dti", "debt_to_income"],
    "credit_utilization_pct": ["credit_utilization_pct", "credit_util", "credit_utilization"],
    "delinq_30plus": ["delinq_30plus", "late_30_days", "30_day_late"],
    "delinq_60plus": ["delinq_60plus", "late_60_days", "60_day_late"],
    "delinq_90plus": ["delinq_90plus", "late_90_days", "90_day_late"],
    "positive_habits_count": ["positive_habits_count", "positive_habits"],
    "risk_flags_count": ["risk_flags_count", "risk_flags"],
}

HOUSING_MAP = {"owner": "own", "own": "own", "renter": "rent", "rent": "rent", "none": "none", "no home": "none"}
EDUCATION_MAP = {
    "master": "masters", "master's": "masters", "masters": "masters",
    "phd": "phd", "doctorate": "phd",
    "bachelor": "bachelor", "bachelor's": "bachelor", "bachelors": "bachelor",
    "certification": "certification", "cert": "certification",
    "high_school": "high_school", "high school": "high_school", "hs": "high_school",
}


def _find_column(row_keys: list[str], field: str) -> Optional[str]:
    """Find the actual CSV column name for a field using aliases."""
    aliases = CSV_COLUMN_ALIASES.get(field, [field])
    lower_keys = {k.lower().strip(): k for k in row_keys}
    for alias in aliases:
        if alias.lower() in lower_keys:
            return lower_keys[alias.lower()]
    return None


def _parse_csv_row_to_features(row: dict, user_id: str) -> tuple[UserFeatures, list[str]]:
    """
    Parse a CSV row into UserFeatures. Returns (features, warnings).
    Handles all the column aliases, unit conversions (0-1 → 0-100), and field mappings.
    """
    warnings = []
    keys = list(row.keys())

    def get(field: str, default=None):
        col = _find_column(keys, field)
        return row[col] if col else default

    def get_float(field: str, default: float = 0.0) -> float:
        val = get(field)
        if val is None or str(val).strip() == "":
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def get_int(field: str, default: int = 0) -> int:
        return int(get_float(field, default))

    # --- Employment ---
    months_employed = get_int("months_employed", 0)

    # --- Housing ---
    housing_raw = str(get("housing_status") or "none").strip().lower()
    housing_status = HOUSING_MAP.get(housing_raw, "none")
    housing_months = get_int("housing_months", 0)

    # --- Education ---
    edu_raw = str(get("education_level") or "high_school").strip().lower()
    education_level = EDUCATION_MAP.get(edu_raw, "high_school")

    # --- Digital bill on-time % ---
    # The dataset stores this as 0-1 fraction (e.g. 0.32 = 32%)
    digital_raw = get_float("digital_bill_ontime_pct", 0.0)
    digital_bill_ontime_pct = digital_raw * 100 if digital_raw <= 1.0 else digital_raw

    # --- Spend-to-income ratio ---
    # Try to compute from monthly_income + monthly_spend if the ratio isn't direct
    monthly_income = get_float("monthly_income", 0.0)
    monthly_spend = get_float("monthly_spend", 0.0)
    if monthly_income > 0 and monthly_spend > 0:
        spend_to_income = round(monthly_spend / monthly_income, 2)
    else:
        # Try dti or a precomputed ratio column
        spend_col = _find_column(keys, "monthly_spend")
        if not spend_col:
            # Use a fallback or 0.5
            spend_to_income = 0.5
            warnings.append("Could not determine spend-to-income ratio; defaulting to 0.5")
        else:
            spend_to_income = 0.5

    # --- Essential spend % ---
    essential_raw = get_float("essential_spend_pct", 0.0)
    essential_spend_pct = essential_raw * 100 if essential_raw <= 1.0 else essential_raw

    # --- Cashflow volatility % ---
    cf_raw = get_float("cashflow_volatility_pct", 0.0)
    cashflow_volatility_pct = cf_raw * 100 if cf_raw <= 1.0 else cf_raw

    # --- Savings ---
    savings_days = get_int("savings_days", 0)

    # --- On-time payment % ---
    otp_raw = get_float("on_time_payment_pct", 0.0)
    on_time_payment_pct = otp_raw * 100 if otp_raw <= 1.0 else otp_raw

    # --- Debt-to-income ratio ---
    dti_raw = get_float("debt_to_income_ratio", 0.0)
    debt_to_income_ratio = dti_raw  # kept as fraction (e.g. 0.35)

    # --- Credit utilization % ---
    cu_raw = get_float("credit_utilization_pct", 0.0)
    credit_utilization_pct = cu_raw * 100 if cu_raw <= 1.0 else cu_raw

    # --- Delinquency flags ---
    delinquency_flags = []
    if get_int("delinq_90plus", 0) > 0:
        delinquency_flags.append("90_day_late")
    if get_int("delinq_60plus", 0) > 0:
        delinquency_flags.append("60_day_late")
    if get_int("delinq_30plus", 0) > 0:
        delinquency_flags.append("30_day_late")
    if len(delinquency_flags) >= 2:
        delinquency_flags = ["multiple_late"]

    # --- Bonus / Penalty ---
    positive_habits_count = get_int("positive_habits_count", 0)
    risk_flags_count = get_int("risk_flags_count", 0)

    features = UserFeatures(
        user_id=user_id,
        months_employed=months_employed,
        housing_status=housing_status,
        housing_months=housing_months,
        digital_bill_ontime_pct=round(digital_bill_ontime_pct, 1),
        education_level=education_level,
        spend_to_income_ratio=spend_to_income,
        essential_spend_pct=round(essential_spend_pct, 1),
        cashflow_volatility_pct=round(cashflow_volatility_pct, 1),
        savings_days=savings_days,
        on_time_payment_pct=round(on_time_payment_pct, 1),
        debt_to_income_ratio=round(debt_to_income_ratio, 2),
        credit_utilization_pct=round(credit_utilization_pct, 1),
        delinquency_flags=delinquency_flags,
        positive_habits_count=positive_habits_count,
        risk_flags_count=risk_flags_count,
    )
    return features, warnings


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file containing one or more applicants' financial data.
    Returns credit scores for all rows.

    Expected CSV columns (flexible aliases supported):
      - months_employed / months_at_job
      - housing_status / housing
      - housing_months / rent_on_time_months
      - digital_bill_ontime_pct / digital_payment_rate (0–1 or 0–100)
      - education_level / education
      - monthly_income
      - monthly_spend / monthly_expenses
      - essential_spend_pct / essential_pct (0–1 or 0–100)
      - cashflow_volatility_pct / cashflow_volatility (0–1 or 0–100)
      - savings_days
      - on_time_payment_pct / on_time_rate (0–1 or 0–100)
      - debt_to_income_ratio / dti (0–1 fraction)
      - credit_utilization_pct / credit_util (0–1 or 0–100)
      - delinq_30plus, delinq_60plus, delinq_90plus (count integers)
      - positive_habits_count / positive_habits
      - risk_flags_count / risk_flags
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no data rows.")

    results = []
    errors = []

    for i, row in enumerate(rows):
        # Determine user_id from CSV or generate one
        user_id_col = None
        for col_name in ["user_id", "applicant_id", "id", "name"]:
            if col_name in row:
                user_id_col = col_name
                break

        if user_id_col:
            user_id = str(row[user_id_col]).strip() or f"applicant_{i+1}"
        else:
            user_id = f"applicant_{i+1}"

        try:
            features, warnings = _parse_csv_row_to_features(row, user_id)
            score_result = compute_score(features)
            explanation = explain_breakdown(score_result.breakdown, user_id=user_id)
            recommendations = recommend_products(score_result.total_score, _products)

            results.append({
                "user_id": user_id,
                "row_number": i + 1,
                "score": score_result.model_dump(),
                "explanation": explanation.model_dump(),
                "recommendations": [r.model_dump() for r in recommendations],
                "features": features.model_dump(),
                "warnings": warnings,
            })
        except Exception as e:
            logger.error(f"Error processing row {i+1} ({user_id}): {e}")
            errors.append({"row_number": i + 1, "user_id": user_id, "error": str(e)})

    return {
        "filename": file.filename,
        "total_rows": len(rows),
        "processed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
        "processed_at": datetime.now().isoformat(),
    }


@app.get("/csv-template")
def get_csv_template():
    """Return the expected CSV column names for upload."""
    return {
        "description": "Upload a CSV with these columns (all are optional except where noted):",
        "columns": {
            "user_id": "Unique identifier (optional, auto-generated if missing)",
            "months_employed": "Months at current job (integer)",
            "housing_status": "own / rent / none",
            "housing_months": "Months at current address (integer)",
            "digital_payment_rate": "Digital bill on-time rate (0.0–1.0)",
            "education": "none / high_school / bachelor / master / phd / certification",
            "monthly_income": "Monthly income in currency units (number)",
            "monthly_spend": "Monthly spending in currency units (number)",
            "essential_pct": "Fraction of spend on essentials (0.0–1.0)",
            "cashflow_volatility": "Cashflow volatility (0.0–1.0)",
            "savings_days": "Days of savings buffer (integer)",
            "on_time_rate": "Bill/payment on-time rate (0.0–1.0)",
            "dti": "Debt-to-income ratio (0.0–1.0)",
            "credit_util": "Credit utilization ratio (0.0–1.0)",
            "delinq_30plus": "Number of 30+ day late payments (integer)",
            "delinq_60plus": "Number of 60+ day late payments (integer)",
            "delinq_90plus": "Number of 90+ day late payments (integer)",
            "positive_habits": "Count of positive financial habits (integer, 0–3)",
            "risk_flags": "Count of risk flags (integer, 0–3)",
        },
        "sample_row": {
            "user_id": "john_doe",
            "months_at_job": 24,
            "housing": "rent",
            "rent_on_time_months": 12,
            "digital_payment_rate": 0.85,
            "education": "bachelor",
            "monthly_income": 5000,
            "monthly_spend": 2000,
            "essential_pct": 0.65,
            "cashflow_volatility": 0.08,
            "savings_days": 90,
            "on_time_rate": 0.92,
            "dti": 0.25,
            "credit_util": 0.20,
            "delinq_30plus": 0,
            "delinq_60plus": 0,
            "delinq_90plus": 0,
            "positive_habits": 2,
            "risk_flags": 0,
        }
    }


# ---------- Dataset Users ----------

@app.get("/users")
def list_users():
    users = []
    for demo in _demographics:
        uid = demo["user_id"]
        score = _scores.get(uid)
        users.append({
            "user_id": uid,
            "age": demo.get("age"),
            "city_tier": demo.get("city_tier"),
            "employment_status": demo.get("employment_status"),
            "total_score": score.total_score if score else None,
            "risk_category": score.risk_category if score else None,
        })
    return users


@app.get("/users/{user_id}")
def get_user(user_id: str):
    for demo in _demographics:
        if demo["user_id"] == user_id:
            return demo
    raise HTTPException(status_code=404, detail=f"User {user_id} not found")


# ---------- Score Endpoints ----------

@app.get("/score/{user_id}", response_model=ScoreResult)
def get_user_score(user_id: str):
    if user_id not in _scores:
        if user_id in _user_features:
            result = compute_score(_user_features[user_id])
            _scores[user_id] = result
            return result
        raise HTTPException(status_code=404, detail=f"Score for {user_id} not found")
    return _scores[user_id]


# ---------- Dashboard ----------

@app.get("/dashboard/{user_id}")
def get_dashboard(user_id: str):
    if user_id not in _user_features:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    if user_id not in _scores:
        _scores[user_id] = compute_score(_user_features[user_id])

    score = _scores[user_id]
    explanation = explain_breakdown(score.breakdown, user_id=user_id)
    recs = recommend_products(score.total_score, _products)

    user_demo = None
    for demo in _demographics:
        if demo["user_id"] == user_id:
            user_demo = demo
            break

    return {
        "user": user_demo,
        "score": score.model_dump(),
        "explanation": explanation.model_dump(),
        "recommendations": [r.model_dump() for r in recs],
        "features": _user_features[user_id].model_dump(),
    }


# ---------- Simulate ----------

@app.post("/simulate", response_model=SimulationResult)
def simulate(request: SimulationRequest):
    if request.user_id not in _user_features:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
    try:
        return simulate_change(_user_features[request.user_id], request.hypothetical_changes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Products ----------

@app.get("/products")
def list_products():
    return [p.model_dump() for p in _products]


# ---------- Lender Candidates ----------

@app.get("/lender/candidates")
def get_candidates(
    min_score: int = Query(0, ge=0),
    max_score: int = Query(1000, le=1000),
    city_tier: str = Query(None),
):
    candidates = []
    for demo in _demographics:
        uid = demo["user_id"]
        if uid not in _scores:
            continue
        score = _scores[uid]
        if score.total_score < min_score or score.total_score > max_score:
            continue
        if city_tier and demo.get("city_tier") != city_tier:
            continue
        ref = "C-" + hashlib.md5(uid.encode()).hexdigest()[:6]
        candidates.append(CandidateSummary(
            candidate_ref=ref,
            score=score.total_score,
            risk_category=score.risk_category,
            city_tier=demo.get("city_tier", "unknown"),
        ).model_dump())
    return candidates
