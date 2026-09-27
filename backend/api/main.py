"""
AltCredit FastAPI Backend — MVP with CSV upload for instant credit scoring.
"""

import sys
import os
import json
import logging
import hashlib
import re
import csv
import io
from datetime import datetime
from typing import Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from common.schemas import (
    ScoreResult, ExplainResult, Recommendation, Product, UserFeatures,
    SimulationRequest, SimulationResult, CandidateSummary, Factor,
    Demographic, ExplainResult, ApplicationRequest,
)
from backend.scoring_engine.engine import compute_score, simulate_change
from backend.explainability.explainer import explain_breakdown
from backend.explainability.xai import build_xai
from backend.recommendations.recommender import recommend_products
from backend.ml_engine.predictor import predict_score, explain_ml
from backend.ml_engine.target_achievement import find_min_change
from data.feature_engineering import (
    get_all_user_features, load_products, load_demographics, normalize_transactions, features_from_upload,
)
from backend.lender.router import build_lender_router, candidate_ref
from backend.lender import accounts as lender_accounts
from backend.lender.store import ApplicationStore, OfferStore
from backend.reports.transparency_report import build_transparency_report
from backend import auth
from database import db as database


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

    database.init_db()
    for uid, feats, demo in database.load_all_user_data():   # registered users / users who uploaded newer data
        _install_user_data(uid, UserFeatures(**feats), demo)
    database.sync_reference_data(_demographics, _products, _scores)
    lender_accounts.ensure_demo_lender()
    created = auth.seed_accounts(_user_features.keys())
    if created:
        logger.info(f"Created {created} user accounts (default password from SEED_USER_PASSWORD)")

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

    # Missing data never crashes scoring, but silently scoring it as 0 would be misleading:
    # tell the user which inputs were absent.
    missing = [f for f in CSV_COLUMN_ALIASES if _find_column(keys, f) is None]
    if missing:
        warnings.append("Missing columns treated as 0/empty: " + ", ".join(missing))

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
    has_spend = _find_column(keys, "monthly_spend") and str(get("monthly_spend") or "").strip() != ""
    if monthly_income > 0 and has_spend:
        spend_to_income = round(monthly_spend / monthly_income, 2)
    else:
        spend_to_income = 0.5
        warnings.append("Could not determine spend-to-income ratio (needs monthly_income and monthly_spend); defaulting to 0.5")

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


def _score_bundle(features: UserFeatures, user_id: str, row_number: int, warnings: list[str]) -> dict:
    """Score one applicant end to end: rule score, explanation, recommendations, ML cross-check."""
    score_result = compute_score(features)
    explanation = explain_breakdown(score_result.breakdown, user_id=user_id)
    recommendations = recommend_products(score_result.total_score, _products)

    # ML explanation of the rule-based score: a second, independent numerical
    # estimate (probability of default -> equivalent score) from the trained
    # model. Wrapped in its own try/except so a model hiccup never blocks the
    # rule-based result, which stays the primary, must-have score.
    ml_score = None
    try:
        ml_score = predict_score(features).model_dump()
        ml_score["drivers"] = explain_ml(features)
    except Exception as ml_err:
        logger.warning(f"ML scoring failed for {user_id}: {ml_err}")

    return {
        "user_id": user_id,
        "row_number": row_number,
        "score": score_result.model_dump(),
        "ml_score": ml_score,
        "explanation": explanation.model_dump(),
        "recommendations": [r.model_dump() for r in recommendations],
        "features": features.model_dump(),
        "warnings": warnings,
    }


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
    headers = {h.lower().strip() for h in (reader.fieldnames or [])}
    if "transaction_id" in headers or {"amount", "category"} <= headers:
        raise HTTPException(
            status_code=400,
            detail="This looks like a bank-transactions file. Upload it together with a demographics JSON "
                   "(POST /upload-raw); /upload-csv expects one row of features per applicant.")
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
            results.append(_score_bundle(features, user_id, i + 1, warnings))
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


@app.post("/upload-raw")
async def upload_raw(transactions: UploadFile = File(...), demographics: UploadFile = File(...)):
    """
    Upload the spec's raw inputs and score every applicant:
      transactions  CSV or JSON — transaction_id, user_id, date, amount, category, type, on_time
      demographics  JSON list   — user_id, age, employment_status, education_level, monthly_income,
                                  city_tier, months_employed, housing_status, housing_months and optional
                                  lifestyle fields (credit_util, delinq_30plus/60plus/90plus,
                                  positive_habits, risk_flags)
    Templates: data/upload_template/ (regenerate with data/generate_upload_template.py).
    """
    def decode(raw: bytes) -> str:
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    try:
        demo_data = json.loads(decode(await demographics.read()))
        if isinstance(demo_data, dict):
            demo_data = demo_data.get("users") or demo_data.get("demographics") or []
        if not isinstance(demo_data, list) or not demo_data:
            raise ValueError("expected a non-empty JSON list of user objects")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid demographics JSON: {e}")

    tx_text = decode(await transactions.read())
    try:
        if (transactions.filename or "").lower().endswith(".json"):
            parsed = json.loads(tx_text)
            tx_rows = parsed["transactions"] if isinstance(parsed, dict) else parsed
        else:
            tx_rows = list(csv.DictReader(io.StringIO(tx_text)))
        tx_all = normalize_transactions(tx_rows)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid transactions file: {e}")

    by_user: dict[str, list] = {}
    for t in tx_all:
        by_user.setdefault(str(t.get("user_id", "")), []).append(t)
    known = {str(d.get("user_id", "")) for d in demo_data if isinstance(d, dict)}

    results, errors = [], []
    for i, demo in enumerate(demo_data):
        user_id = str(demo.get("user_id", "")).strip() if isinstance(demo, dict) else ""
        if not user_id:
            errors.append({"row_number": i + 1, "user_id": "", "error": "demographics record has no user_id"})
            continue
        try:
            features, warnings = features_from_upload(demo, by_user.get(user_id, []))
            results.append(_score_bundle(features, user_id, i + 1, warnings))
        except Exception as e:
            logger.error(f"Error processing applicant {user_id}: {e}")
            errors.append({"row_number": i + 1, "user_id": user_id, "error": str(e)})
    for orphan in sorted(set(by_user) - known):
        errors.append({"row_number": 0, "user_id": orphan, "error": "transactions found but no demographics record"})

    return {
        "filename": f"{transactions.filename} + {demographics.filename}",
        "total_rows": len(demo_data),
        "processed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
        "processed_at": datetime.now().isoformat(),
    }


UPLOAD_TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "data", "upload_template")
UPLOAD_TEMPLATE_FILES = {"transactions.csv": "text/csv", "transactions.json": "application/json",
                         "demographics.json": "application/json"}


@app.get("/upload-template/{name}")
def download_upload_template(name: str):
    """Serve the raw-upload template files (whitelisted; single source of truth is data/upload_template/)."""
    if name not in UPLOAD_TEMPLATE_FILES:
        raise HTTPException(status_code=404, detail="Unknown template file")
    path = os.path.join(UPLOAD_TEMPLATE_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Template not generated; run python data/generate_upload_template.py")
    return FileResponse(path, media_type=UPLOAD_TEMPLATE_FILES[name], filename=name)


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

@app.get("/score/{user_id}/ml", response_model=ScoreResult)
def get_user_score_ml(user_id: str):
    """Same as /score/{user_id}, but scored with the trained Probability-of-Default
    model instead of the rule engine (method='ml_pd', includes probability_of_default)."""
    if user_id not in _user_features:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return predict_score(_user_features[user_id])


# ---------- Target Achievement (counterfactual "what do I need to change") ----------

class TargetAchievementRequest(BaseModel):
    target_score: int
    target_product_name: Optional[str] = None
    user_id: Optional[str] = None    # looks up a pre-loaded dataset user
    features: Optional[dict] = None  # OR pass a UserFeatures dict directly — this is what
                                      # the frontend sends for CSV-uploaded applicants, since
                                      # those aren't cached server-side (use result.features)


@app.post("/target-achievement")
def target_achievement(request: TargetAchievementRequest):
    if request.features:
        try:
            features = UserFeatures(**request.features)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid features: {e}")
    elif request.user_id and request.user_id in _user_features:
        features = _user_features[request.user_id]
    else:
        raise HTTPException(status_code=404, detail="Provide `features` (from your score result) or a known `user_id`.")
    try:
        return find_min_change(
            features,
            request.target_score,
            compute_score,
            target_product_name=request.target_product_name,
        )
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
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


# ---------- Lender portal (separate, authenticated router) ----------

offer_store = OfferStore()
application_store = ApplicationStore()
app.include_router(build_lender_router(
    get_demographics=lambda: _demographics,
    get_scores=lambda: _scores,
    get_products=lambda: _products,
    get_analysis=lambda uid: _score_bundle(_user_features[uid], uid, 0, []) if uid in _user_features else None,
    store=offer_store,
    applications=application_store,
))


# ---------- Registration and data updates (users submit their own data) ----------

USER_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")


def _install_user_data(user_id: str, features: UserFeatures, demo: dict) -> ScoreResult:
    """Put a user's data into the in-memory caches (features, score, demographics record); returns the score."""
    global _demographics
    _user_features[user_id] = features
    _scores[user_id] = compute_score(features)
    record = {**{k: v for k, v in demo.items() if v is not None}, "user_id": user_id}
    if "city_tier" in record:
        record["city_tier"] = _normalize_city_tier(record["city_tier"])
    _demographics = [d for d in _demographics if d["user_id"] != user_id] + [record]
    return _scores[user_id]


async def _read_text(upload: UploadFile) -> str:
    raw = await upload.read()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


async def _features_from_submission(user_id: str, features_csv: Optional[UploadFile],
                                    transactions: Optional[UploadFile], demographics: Optional[UploadFile]):
    """Either a one-row features CSV, or transactions + demographics. Returns (features, demographics_dict)."""
    if features_csv is not None and features_csv.filename:
        rows = list(csv.DictReader(io.StringIO(await _read_text(features_csv))))
        if not rows:
            raise HTTPException(status_code=400, detail="The CSV has no data rows.")
        mine = next((r for r in rows if str(r.get("user_id", "")).strip() == user_id), rows[0])
        try:
            features, _ = _parse_csv_row_to_features(mine, user_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read the CSV: {e}")
        return features, {}
    if transactions is not None and transactions.filename and demographics is not None and demographics.filename:
        try:
            demo_data = json.loads(await _read_text(demographics))
            if isinstance(demo_data, dict) and "user_id" not in demo_data:
                demo_data = demo_data.get("users") or demo_data.get("demographics") or []
            demos = [demo_data] if isinstance(demo_data, dict) else demo_data
            demo = next((d for d in demos if str(d.get("user_id", "")) == user_id), demos[0])
        except (ValueError, IndexError, AttributeError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid demographics JSON: {e}")
        tx_text = await _read_text(transactions)
        try:
            if transactions.filename.lower().endswith(".json"):
                parsed = json.loads(tx_text)
                tx_rows = parsed["transactions"] if isinstance(parsed, dict) else parsed
            else:
                tx_rows = list(csv.DictReader(io.StringIO(tx_text)))
            tx_all = normalize_transactions(tx_rows)
        except (ValueError, KeyError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid transactions file: {e}")
        mine = [t for t in tx_all if str(t.get("user_id", "")) == user_id]
        if not mine and len({str(t.get("user_id", "")) for t in tx_all}) == 1:
            mine = tx_all   # a single-person statement, whatever ID it carries
        demo = {**demo, "user_id": user_id}
        try:
            features, _ = features_from_upload(demo, mine)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not score the uploaded data: {e}")
        return features, demo
    raise HTTPException(status_code=400,
                        detail="Upload either a features CSV, or both a transactions file and a demographics JSON.")


@app.get("/auth/check-id")
def check_user_id(user_id: str = Query(...)):
    """Lets the registration form flag a taken/invalid ID before any files are uploaded."""
    user_id = user_id.strip()
    if not USER_ID_RE.match(user_id):
        return {"available": False, "reason": "Use 3-40 characters: letters, digits, _ . -"}
    if user_id in _user_features or auth.is_taken(user_id):
        return {"available": False, "reason": "That user ID is already taken. Please choose a different one."}
    return {"available": True, "reason": None}


@app.post("/auth/register")
async def register(user_id: str = Form(...), password: str = Form(...),
                   features_csv: Optional[UploadFile] = File(None),
                   transactions: Optional[UploadFile] = File(None),
                   demographics: Optional[UploadFile] = File(None)):
    user_id = user_id.strip()
    if not USER_ID_RE.match(user_id):
        raise HTTPException(status_code=422, detail="User ID must be 3-40 characters: letters, digits, _ . -")
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    if user_id in _user_features or auth.is_taken(user_id):
        raise HTTPException(status_code=409, detail="That user ID is already taken. Please choose a different one.")
    features, demo = await _features_from_submission(user_id, features_csv, transactions, demographics)
    if not auth.create_account(user_id, password):
        raise HTTPException(status_code=409, detail="That user ID is already taken")
    score = _install_user_data(user_id, features, demo)
    database.save_user_data(user_id, features.model_dump(), demo, score)
    return {"token": auth.issue_token(user_id), "token_type": "bearer",
            "expires_in": auth.SESSION_TTL_SECONDS, "user_id": user_id}


@app.post("/me/data")
async def update_my_data(features_csv: Optional[UploadFile] = File(None),
                         transactions: Optional[UploadFile] = File(None),
                         demographics: Optional[UploadFile] = File(None),
                         user_id: str = Depends(auth.require_user)):
    """Replace the logged-in user's data with newer uploads and re-score. Returns the fresh dashboard bundle."""
    previous = _scores.get(user_id)
    features, demo = await _features_from_submission(user_id, features_csv, transactions, demographics)
    if not demo:   # a features-only CSV carries no profile; keep what we already know
        demo = next((d for d in _demographics if d["user_id"] == user_id), {})
    score = _install_user_data(user_id, features, demo)
    database.save_user_data(user_id, features.model_dump(), demo, score)
    return {**_score_bundle(features, user_id, 0, []), "previous_score": previous.total_score if previous else None}


# ---------- Consumer login ----------

class LoginRequest(BaseModel):
    user_id: str
    password: str


@app.post("/auth/login")
def user_login(body: LoginRequest):
    token = auth.login(body.user_id, body.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid user ID or password")
    uid = body.user_id.strip()
    return {"token": token, "token_type": "bearer", "expires_in": auth.SESSION_TTL_SECONDS, "user_id": uid}


@app.post("/auth/logout")
def user_logout(authorization: Optional[str] = Header(default=None)):
    auth.logout(auth.bearer_token(authorization))
    return {"status": "logged_out"}


@app.get("/auth/me")
def whoami(user_id: str = Depends(auth.require_user)):
    return {"user_id": user_id}


@app.get("/me/dashboard")
def my_dashboard(user_id: str = Depends(auth.require_user)):
    """The logged-in user's own score analysis (same shape as an /upload-csv result row)."""
    if user_id not in _user_features:
        raise HTTPException(status_code=404, detail=f"No score data for {user_id}")
    return _score_bundle(_user_features[user_id], user_id, 0, [])


# ---------- Consumer side of lender offers (login required; you can only see/answer your own) ----------

def _require_self(user_id: str, current: str) -> None:
    if user_id != current:
        raise HTTPException(status_code=403, detail="You can only access your own offers")


@app.get("/users/{user_id}/offers")
def get_user_offers(user_id: str, current: str = Depends(auth.require_user)):
    _require_self(user_id, current)
    banks = lender_accounts.bank_names()
    return [{**{k: v for k, v in o.items() if k not in ("user_id", "candidate_ref", "lender")},
             "bank_name": banks.get(o["lender"], o["lender"])}
            for o in offer_store.for_user(user_id)]


class OfferResponse(BaseModel):
    action: str   # "accept" | "reject"


@app.post("/users/{user_id}/offers/{offer_id}/respond")
def respond_to_offer(user_id: str, offer_id: int, body: OfferResponse, current: str = Depends(auth.require_user)):
    _require_self(user_id, current)
    if body.action not in ("accept", "reject"):
        raise HTTPException(status_code=422, detail="action must be 'accept' or 'reject'")
    offer = offer_store.respond(offer_id, user_id, accept=body.action == "accept")
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found for this user")
    if offer.pop("_already_answered", False):
        raise HTTPException(status_code=409, detail=f"Offer already {offer['status']}")
    return {"offer_id": offer_id, "status": offer["status"]}


# ---------- Pre-approval: apply to a specific registered lender ----------

@app.get("/lenders")
def list_lenders():
    """Registered banks/lenders a borrower can apply to."""
    return lender_accounts.list_lenders()


def _public_application(a: dict, banks: dict) -> dict:
    return {**{k: v for k, v in a.items() if k not in ("user_id", "lender")},
            "lender_id": a["lender"], "bank_name": banks.get(a["lender"], a["lender"])}


@app.get("/users/{user_id}/applications")
def get_user_applications(user_id: str, current: str = Depends(auth.require_user)):
    _require_self(user_id, current)
    banks = lender_accounts.bank_names()
    return [_public_application(a, banks) for a in application_store.for_user(user_id)]


@app.post("/users/{user_id}/applications", status_code=201)
def apply_to_lender(user_id: str, body: ApplicationRequest, current: str = Depends(auth.require_user)):
    _require_self(user_id, current)
    product = next((p for p in _products if p.product_id == body.product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Unknown product {body.product_id}")
    banks = lender_accounts.bank_names()
    if body.lender_id not in banks:
        raise HTTPException(status_code=404, detail="Unknown lender")
    if body.requested_amount <= 0 or body.tenure_months <= 0:
        raise HTTPException(status_code=422, detail="Amount and tenure must be positive")
    if not body.full_name.strip() or not body.phone.strip():
        raise HTTPException(status_code=422, detail="Name and phone are required")
    score = _scores.get(user_id)   # always the server's score, never a client-supplied one
    if score is None:
        raise HTTPException(status_code=404, detail="No score on file yet")
    if score.total_score < product.min_score_required:
        raise HTTPException(status_code=422, detail=f"Your score is below this product's minimum of {product.min_score_required}")
    row = application_store.create(
        user_id=user_id, lender=body.lender_id, product_id=product.product_id, product_name=product.name,
        interest_rate=product.interest_rate, requested_amount=body.requested_amount,
        tenure_months=body.tenure_months, purpose=body.purpose.strip(), applicant_name=body.full_name.strip(),
        phone=body.phone.strip(), score_at_submit=score.total_score)
    if row is None:
        raise HTTPException(status_code=409, detail="You already have an active application for this product with that lender")
    return _public_application(row, banks)


# ---------- Explainable-AI dashboard ----------

class XaiRequest(BaseModel):
    features: UserFeatures


@app.post("/xai")
def explain_dashboard(request: XaiRequest):
    """Everything the "Why this score" tab needs; recomputed server-side from the applicant's features."""
    ml_score = None
    try:
        ml_score = predict_score(request.features).model_dump()
        ml_score["drivers"] = explain_ml(request.features, top_n=8)
    except Exception as e:
        logger.warning(f"ML scoring failed for XAI view of {request.features.user_id}: {e}")
    return build_xai(request.features, ml_score)


# ---------- PDF Transparency Report ----------

class ReportRequest(BaseModel):
    """The exact objects the dashboard already holds (/upload-csv or /dashboard result) — nothing is recomputed."""
    score: ScoreResult
    explanation: ExplainResult
    recommendations: list[Recommendation]
    ml_score: Optional[dict] = None


def _pdf_response(pdf: bytes, user_id: str) -> Response:
    safe = "".join(c for c in user_id if c.isalnum() or c in "-_") or "applicant"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="transparency-report-{safe}.pdf"'})


@app.post("/report/pdf")
def report_pdf(body: ReportRequest):
    pdf = build_transparency_report(body.score, body.explanation, body.recommendations, body.ml_score)
    return _pdf_response(pdf, body.score.user_id)


@app.get("/report/{user_id}")
def report_for_user(user_id: str):
    d = get_dashboard(user_id)   # existing dashboard payload: score + explanation + recommendations
    pdf = build_transparency_report(
        ScoreResult(**d["score"]), ExplainResult(**d["explanation"]),
        [Recommendation(**r) for r in d["recommendations"]],
    )
    return _pdf_response(pdf, user_id)
