"""
Raw merged_data.json row -> common.schemas.UserFeatures.

This is the ONLY place that knows the raw file's field names. If the data/ owner ships an
official get_user_features(), switch callers to that and delete this file.

Raw field               -> UserFeatures field           Notes
----------------------------------------------------------------------------------------------
user_id                 -> user_id
months_at_job           -> months_employed
housing                 -> housing_status                lower-cased ("own" | "rent" | "none")
rent_on_time_months     -> housing_months                ASSUMPTION: closest match; see below
digital_payment_rate    -> digital_bill_ontime_pct       0-1 columns scaled to 0-100
education_level         -> education_level               normalised to schema vocabulary
monthly_spend /
  monthly_income        -> spend_to_income_ratio         computed
essential_pct           -> essential_spend_pct           0-1 columns scaled to 0-100
cashflow_volatility     -> cashflow_volatility_pct       0-1 columns scaled to 0-100
savings_days            -> savings_days
on_time_rate            -> on_time_payment_pct           0-1 columns scaled to 0-100
dti                     -> debt_to_income_ratio          percent columns (max > 5) /100
credit_util             -> credit_utilization_pct        0-1 columns scaled to 0-100
delinq_90plus/60plus/30plus (counts) -> delinquency_flags  ["90-day-miss", "60-day-miss", "30-day-miss"]
positive_habits         -> positive_habits_count         list -> len(list), number -> int
risk_flags              -> risk_flags_count              list -> len(list), number -> int
Unused: age, employment_status, city_tier (not UserFeatures fields).

ASSUMPTION on housing_months: the schema wants "months in current housing" but the raw file only
has "rent_on_time_months". For renters that's the best available proxy; confirm with data/ owner.
"""

from __future__ import annotations

import json
from pathlib import Path

from common.schemas import UserFeatures

# Delinquency flag strings — same vocabulary as backend/testing/README.md ("90-day-miss").
FLAG_30 = "30-day-miss"
FLAG_60 = "60-day-miss"
FLAG_90 = "90-day-miss"

_EDUCATION_ALIASES = {
    "phd": "phd", "ph.d": "phd", "doctorate": "phd",
    "masters": "masters", "master": "masters", "master's": "masters", "postgraduate": "masters",
    "bachelor": "bachelor", "bachelors": "bachelor", "bachelor's": "bachelor", "graduate": "bachelor",
    "certification": "certification", "certificate": "certification", "diploma": "certification",
    "high_school": "high_school", "high school": "high_school", "highschool": "high_school", "12th": "high_school",
}


# Raw columns that hold percentages. Some exports store them as 0-1 fractions, others as 0-100.
PERCENT_FIELDS = ("digital_payment_rate", "essential_pct", "cashflow_volatility", "on_time_rate", "credit_util")


def detect_scales(rows: list[dict]) -> dict:
    """Decide ONCE per column (not per value) how the file stores percents and dti.

    Per-value guessing is unsafe: a credit_util of 1 could mean 1% or 100%. Looking at the
    whole column removes the ambiguity: if every value is <= 1, the column is fractions.
    """
    def col(field):
        return [float(r.get(field) or 0) for r in rows]

    fraction_fields = {f for f in PERCENT_FIELDS if rows and max(col(f)) <= 1}
    dti_is_percent = bool(rows) and max(col("dti")) > 5
    return {"fraction_fields": fraction_fields, "dti_is_percent": dti_is_percent}


def _pct(raw: dict, field: str, scales: dict) -> float:
    v = float(raw.get(field) or 0)
    return round(v * 100, 2) if field in scales["fraction_fields"] else round(v, 2)


def _count(value) -> int:
    if isinstance(value, (list, tuple)):
        return len(value)
    return int(value or 0)


def _education(value) -> str:
    key = str(value or "").strip().lower().replace("-", "_")
    return _EDUCATION_ALIASES.get(key, _EDUCATION_ALIASES.get(key.replace("_", " "), key))


def raw_user_to_features(raw: dict, scales: dict | None = None) -> UserFeatures:
    """Map one raw row. Pass `scales` from detect_scales(all_rows); if omitted, the scale is
    guessed from this single row (fine for tests, less safe than whole-file detection)."""
    scales = scales or detect_scales([raw])
    income = float(raw.get("monthly_income") or 0)
    spend = float(raw.get("monthly_spend") or 0)
    flags = (
        [FLAG_90] * _count(raw.get("delinq_90plus"))
        + [FLAG_60] * _count(raw.get("delinq_60plus"))
        + [FLAG_30] * _count(raw.get("delinq_30plus"))
    )
    return UserFeatures(
        user_id=str(raw["user_id"]),
        months_employed=int(raw.get("months_at_job") or 0),
        housing_status=str(raw.get("housing") or "none").strip().lower(),
        housing_months=int(raw.get("rent_on_time_months") or 0),
        digital_bill_ontime_pct=_pct(raw, "digital_payment_rate", scales),
        education_level=_education(raw.get("education_level")),
        spend_to_income_ratio=round(spend / income, 4) if income > 0 else 1.0,  # no income = worst bracket
        essential_spend_pct=_pct(raw, "essential_pct", scales),
        cashflow_volatility_pct=_pct(raw, "cashflow_volatility", scales),
        savings_days=int(raw.get("savings_days") or 0),
        on_time_payment_pct=_pct(raw, "on_time_rate", scales),
        debt_to_income_ratio=round(float(raw.get("dti") or 0) / (100 if scales["dti_is_percent"] else 1), 4),
        credit_utilization_pct=_pct(raw, "credit_util", scales),
        delinquency_flags=flags,
        positive_habits_count=_count(raw.get("positive_habits")),
        risk_flags_count=_count(raw.get("risk_flags")),
    )


def load_raw_users(path: str | Path = "data/merged_data.json") -> list[dict]:
    """Read merged_data.json. Accepts a top-level list or {"users": [...]}."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if isinstance(raw, dict):
        raw = raw.get("users", [])
    return raw


def load_user_features(path: str | Path = "data/merged_data.json") -> list[UserFeatures]:
    """Load the whole file and map every row, with percent scales detected per column."""
    rows = load_raw_users(path)
    scales = detect_scales(rows)
    return [raw_user_to_features(r, scales) for r in rows]