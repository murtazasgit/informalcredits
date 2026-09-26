"""
Feature engineering module — transforms the real Datasets_AltCredit data into
the UserFeatures dict that the scoring engine consumes.

Supports two paths:
  1. Pre-computed features from merged_data.json (fast, recommended)
  2. Raw computation from demographics.json + transactional_data.csv (fallback)
"""

import json
import csv
import os
import statistics
from collections import defaultdict
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.schemas import UserFeatures


def load_demographics(path: str) -> list[dict]:
    """Load demographics JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def load_transactions(path: str) -> list[dict]:
    """Load transactions from a CSV or JSON (list of objects) file — handles both synthetic
    and real formats."""
    with open(path, "r", encoding="utf-8-sig") as f:
        if path.lower().endswith(".json"):
            data = json.load(f)
            rows = data["transactions"] if isinstance(data, dict) else data
        else:
            rows = list(csv.DictReader(f))
    return normalize_transactions(rows)


def normalize_transactions(rows) -> list[dict]:
    """Normalise raw transaction rows (dicts from CSV or JSON): numeric amount, Debit/Credit casing,
    standard category names, ISO dates, and an `on_time` bool/None for recurring bills."""
    transactions = []
    for row in rows:
        row = dict(row)
        row["amount"] = float(row["amount"])

        # Handle real dataset: status field → on_time bool
        if "status" in row and "on_time" not in row:
            if row["status"] in ("Completed", "Late"):
                row["on_time"] = row["status"] == "Completed"
            else:
                row["on_time"] = None
        elif "on_time" in row:
            val = row["on_time"]
            if isinstance(val, str):
                row["on_time"] = val.lower() == "true" if val and val != "" else None
        else:
            row["on_time"] = None

        # Normalize transaction type to title case
        if "type" in row:
            row["type"] = row["type"].strip().title()  # DEBIT→Debit, CREDIT→Credit

        # Normalize category names
        if "category" in row:
            cat = row["category"].strip()
            # Map real dataset categories to standard names
            cat_map = {
                "Utility Bill": "Utility",
                "Shopping": "Discretionary",
                "Other Income": "Salary",
                "Savings": "Savings",
            }
            row["category"] = cat_map.get(cat, cat)

        # Normalize date to YYYY-MM-DD
        if "date" in row and "/" in str(row["date"]):
            try:
                dt = datetime.strptime(row["date"], "%m/%d/%Y")
                row["date"] = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        transactions.append(row)
    return transactions


def load_products(path: str) -> list[dict]:
    """Load product catalog JSON file — handles both synthetic and real formats."""
    with open(path, "r") as f:
        raw = json.load(f)

    products = []
    for p in raw:
        # Normalize field names from real dataset
        product = {
            "product_id": p.get("product_id", ""),
            "name": p.get("name") or p.get("product_name", ""),
            "type": p.get("type", ""),
            "min_score_required": p.get("min_score_required") or p.get("min_score", 0),
            "interest_rate": _parse_interest_rate(p.get("interest_rate", "0")),
        }
        products.append(product)
    return products


def _parse_interest_rate(rate_str) -> float:
    """Parse interest rate from strings like '12% APR' or '17.00% PA' or raw float."""
    if isinstance(rate_str, (int, float)):
        return float(rate_str)
    # Extract numeric part from strings like "12% APR", "17.00% PA"
    import re
    match = re.search(r"([\d.]+)", str(rate_str))
    return float(match.group(1)) if match else 0.0


def load_merged_data(path: str) -> list[dict]:
    """Load merged_data.json which has demographics + pre-computed features."""
    with open(path, "r") as f:
        return json.load(f)


def load_new_age_data(path: str) -> list[dict]:
    """Load new_age_sample_data.json with pre-computed features by applicant_id."""
    with open(path, "r") as f:
        return json.load(f)


def load_id_mapping(path: str) -> dict:
    """Load id_mapping.json → dict of user_id → applicant_id."""
    with open(path, "r") as f:
        data = json.load(f)
    return {item["user_id"]: item["applicant_id"] for item in data}


def _map_housing(housing_val: str) -> str:
    """Map real dataset housing values to schema values."""
    housing_map = {
        "owner": "own",
        "own": "own",
        "renter": "rent",
        "rent": "rent",
        "none": "none",
    }
    return housing_map.get(str(housing_val).lower(), "none")


def _map_education(edu_val: str) -> str:
    """Map real dataset education values to schema values."""
    edu_map = {
        "master": "masters",
        "master's": "masters",
        "masters": "masters",
        "phd": "phd",
        "bachelor": "bachelor",
        "bachelor's": "bachelor",
        "certification": "certification",
        "high_school": "high_school",
        "high school": "high_school",
    }
    return edu_map.get(str(edu_val).lower(), "high_school")


def _build_delinquency_flags(record: dict) -> list[str]:
    """Build delinquency flags from real dataset fields."""
    flags = []
    total_events = 0
    for key, flag in (("delinq_90plus", "90_day_late"), ("delinq_60plus", "60_day_late"),
                      ("delinq_30plus", "30_day_late")):
        count = record.get(key) or 0
        if count > 0:
            flags.append(flag)
            total_events += count
    # Several delinquency events (of one or several kinds) => "multiple_late" (scores 0)
    if len(flags) >= 2 or total_events >= 2:
        flags = ["multiple_late"]
    return flags


def features_from_merged(record: dict) -> UserFeatures:
    """
    Build UserFeatures from a merged_data.json record which has both
    demographic and pre-computed feature fields.
    """
    user_id = record.get("user_id", "")
    housing = _map_housing(record.get("housing", "none"))

    # Education: merged data has both 'education_level' (demographic) and 'education' (feature)
    education = _map_education(
        record.get("education") or record.get("education_level", "high_school")
    )

    delinquency_flags = _build_delinquency_flags(record)

    return UserFeatures(
        user_id=user_id,
        months_employed=record.get("months_at_job", 0),
        housing_status=housing,
        housing_months=record.get("rent_on_time_months", 0) if housing == "rent" else (24 if housing == "own" else 0),
        digital_bill_ontime_pct=round(record.get("digital_payment_rate", 0) * 100, 1),
        education_level=education,
        spend_to_income_ratio=round(
            record.get("monthly_spend", 0) / max(record.get("monthly_income", 1), 1), 2
        ),
        essential_spend_pct=round(record.get("essential_pct", 0) * 100, 1),
        cashflow_volatility_pct=round(record.get("cashflow_volatility", 0) * 100, 1),
        savings_days=record.get("savings_days", 0),
        on_time_payment_pct=round(record.get("on_time_rate", 0) * 100, 1),
        debt_to_income_ratio=round(record.get("dti", 0), 2),
        credit_utilization_pct=round(record.get("credit_util", 0) * 100, 1),
        delinquency_flags=delinquency_flags,
        positive_habits_count=min(record.get("positive_habits", 0), 3),
        risk_flags_count=min(record.get("risk_flags", 0), 3),
    )


def compute_user_features(user_id: str, demo: dict, user_txns: list[dict]) -> UserFeatures:
    """
    Engineer features for a single user from their demographics + transactions.
    Fallback path when merged_data.json is not available.
    """
    # Missing / zero / non-numeric income must not crash scoring: fall back to 1 so
    # ratios saturate (worst-case buckets) instead of raising ZeroDivisionError.
    try:
        monthly_income = float(demo.get("monthly_income") or 0)
    except (TypeError, ValueError):
        monthly_income = 0.0
    if monthly_income <= 0:
        monthly_income = 1.0

    # Separate debits and credits
    debits = [t for t in user_txns if t["type"] == "Debit"]
    credits = [t for t in user_txns if t["type"] == "Credit"]

    # Group transactions by month
    monthly_debits = defaultdict(float)
    for t in debits:
        month_key = str(t.get("date", ""))[:7]  # YYYY-MM
        monthly_debits[month_key] += t["amount"]
    num_months = max(len(monthly_debits), 1)

    # 1. spend_to_income_ratio
    avg_monthly_spend = sum(monthly_debits.values()) / num_months
    spend_to_income_ratio = round(min(avg_monthly_spend / monthly_income, 2.0), 2)

    # 2. essential_spend_pct
    essential_categories = {"Rent", "Utility", "Food", "Insurance", "EMI"}
    total_debit = sum(t["amount"] for t in debits) or 1
    essential_total = sum(t["amount"] for t in debits if t["category"] in essential_categories)
    essential_spend_pct = round(100 * essential_total / total_debit, 1)

    # 3. cashflow_volatility_pct
    if len(monthly_debits) >= 2:
        monthly_amounts = list(monthly_debits.values())
        mean_spend = statistics.mean(monthly_amounts)
        std_spend = statistics.stdev(monthly_amounts)
        cashflow_volatility_pct = round(100 * std_spend / mean_spend, 1) if mean_spend > 0 else 0
    else:
        cashflow_volatility_pct = 0.0

    # 4. savings_days — estimate from surplus income
    total_credits = sum(t["amount"] for t in credits)
    total_debits_amount = sum(t["amount"] for t in debits)
    net_savings = total_credits - total_debits_amount
    savings_days = max(0, int(net_savings / (monthly_income / 30))) if monthly_income > 0 else 0
    savings_days = min(savings_days, 365)

    # 5. digital_bill_ontime_pct
    bill_categories = {"Utility", "Rent", "Insurance", "EMI"}
    bill_txns = [t for t in user_txns if t["category"] in bill_categories and t["on_time"] is not None]
    if bill_txns:
        digital_bill_ontime_pct = round(100 * sum(1 for t in bill_txns if t["on_time"]) / len(bill_txns), 1)
    else:
        digital_bill_ontime_pct = 0.0

    # 6. on_time_payment_pct (all recurring payments)
    recurring_txns = [t for t in user_txns if t["on_time"] is not None]
    if recurring_txns:
        on_time_payment_pct = round(100 * sum(1 for t in recurring_txns if t["on_time"]) / len(recurring_txns), 1)
    else:
        on_time_payment_pct = 0.0

    # 7. debt_to_income_ratio
    emi_total = sum(t["amount"] for t in debits if t["category"] in {"EMI", "Insurance"})
    monthly_emi = emi_total / num_months
    debt_to_income_ratio = round(monthly_emi / monthly_income, 2) if monthly_income > 0 else 0.0

    # 8. credit_utilization_pct
    credit_utilization_pct = 0.0

    # 9. delinquency_flags
    delinquency_flags = []
    late_bills = [t for t in bill_txns if not t["on_time"]]
    if len(late_bills) >= 3:
        delinquency_flags.append("multiple_late")
    elif len(late_bills) >= 1:
        delinquency_flags.append("30_day_late")

    # 10. positive_habits_count
    positive_habits = 0
    if essential_spend_pct >= 60:
        positive_habits += 1
    if on_time_payment_pct >= 90:
        positive_habits += 1
    if savings_days >= 30:
        positive_habits += 1
    positive_habits = min(positive_habits, 3)

    # 11. risk_flags_count
    risk_flags = 0
    if spend_to_income_ratio > 0.7:
        risk_flags += 1
    if cashflow_volatility_pct > 20:
        risk_flags += 1
    if len(delinquency_flags) > 0:
        risk_flags += 1
    risk_flags = min(risk_flags, 3)

    housing_status = _map_housing(demo.get("housing_status") or demo.get("housing", "none"))
    education = _map_education(demo.get("education_level") or demo.get("education", "high_school"))

    return UserFeatures(
        user_id=user_id,
        months_employed=demo.get("months_employed") or demo.get("months_at_job", 0),
        housing_status=housing_status,
        housing_months=demo.get("housing_months") or demo.get("rent_on_time_months", 0),
        digital_bill_ontime_pct=digital_bill_ontime_pct,
        education_level=education,
        spend_to_income_ratio=spend_to_income_ratio,
        essential_spend_pct=essential_spend_pct,
        cashflow_volatility_pct=cashflow_volatility_pct,
        savings_days=savings_days,
        on_time_payment_pct=on_time_payment_pct,
        debt_to_income_ratio=debt_to_income_ratio,
        credit_utilization_pct=credit_utilization_pct,
        delinquency_flags=delinquency_flags,
        positive_habits_count=positive_habits,
        risk_flags_count=risk_flags,
    )


def get_all_user_features(data_dir: str) -> dict[str, UserFeatures]:
    """
    Load all data and compute features for every user.
    Prefers merged_data.json (pre-computed) when available,
    falls back to raw computation from demographics + transactions.
    """
    merged_path = os.path.join(data_dir, "merged_data.json")
    if os.path.exists(merged_path):
        # Fast path: use pre-computed merged data
        merged = load_merged_data(merged_path)
        features = {}
        for record in merged:
            uid = record.get("user_id", "")
            if uid:
                features[uid] = features_from_merged(record)
        return features

    # Fallback: compute from raw files
    demographics = load_demographics(os.path.join(data_dir, "demographics.json"))
    transactions = load_transactions(os.path.join(data_dir, "transactions.csv"))

    # Group transactions by user
    user_txns = defaultdict(list)
    for t in transactions:
        user_txns[t["user_id"]].append(t)

    features = {}
    for demo in demographics:
        uid = demo["user_id"]
        features[uid] = compute_user_features(uid, demo, user_txns.get(uid, []))

    return features


def get_user_features(user_id: str, data_dir: str) -> UserFeatures:
    """Get features for a single user."""
    all_features = get_all_user_features(data_dir)
    if user_id not in all_features:
        raise ValueError(f"User {user_id} not found")
    return all_features[user_id]


# ---------- Upload path: raw transactions + demographics (+ lifestyle fields) ----------

def _pct(value) -> float:
    """Lifestyle ratios may arrive as 0-1 fractions or 0-100 percentages."""
    v = float(value)
    return v * 100 if v <= 1.0 else v


def features_from_upload(demo: dict, user_txns: list[dict]) -> tuple[UserFeatures, list[str]]:
    """
    Features for one uploaded applicant. Everything derivable from the bank statement is computed
    from the transactions (spending, essentials share, volatility, savings, bill timeliness, DTI);
    lifestyle fields in the demographics record that a statement cannot reveal — credit_util,
    delinq_30plus/60plus/90plus, positive_habits, risk_flags — are taken as given when present.
    Returns (features, warnings).
    """
    warnings = []
    if not user_txns:
        warnings.append("No transactions found for this applicant; spending and payment factors default to 0")
    features = compute_user_features(demo.get("user_id", ""), demo, user_txns)
    data = features.model_dump()

    if demo.get("credit_util") is not None or demo.get("credit_utilization_pct") is not None:
        data["credit_utilization_pct"] = round(_pct(demo.get("credit_util", demo.get("credit_utilization_pct"))), 1)
    if any(k in demo for k in ("delinq_30plus", "delinq_60plus", "delinq_90plus")):
        data["delinquency_flags"] = _build_delinquency_flags(
            {k: int(demo.get(k) or 0) for k in ("delinq_30plus", "delinq_60plus", "delinq_90plus")})
    if demo.get("positive_habits") is not None:
        data["positive_habits_count"] = min(int(demo["positive_habits"]), 3)
    if demo.get("risk_flags") is not None:
        data["risk_flags_count"] = min(int(demo["risk_flags"]), 3)
    return UserFeatures(**data), warnings
