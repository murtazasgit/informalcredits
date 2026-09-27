"""
feature_mapping.py - converts raw merged_data.json rows into common.schemas.UserFeatures,
and UserFeatures into the flat row the PD model uses.

Raw field (merged_data.json)  ->  UserFeatures field              conversion
months_at_job                 ->  months_employed                 int
housing                       ->  housing_status                  owner->own, rent->rent, none->none
rent_on_time_months           ->  housing_months                  int
digital_payment_rate (0-1)    ->  digital_bill_ontime_pct (0-100) x100
education                     ->  education_level                 master->masters, cert->certification,
                                                                  highschool->high_school, bachelor, phd, none
monthly_spend / monthly_income->  spend_to_income_ratio (0-1)     division
essential_pct (0-1)           ->  essential_spend_pct (0-100)     x100
cashflow_volatility (0-1)     ->  cashflow_volatility_pct (0-100) x100
savings_days                  ->  savings_days                    int
on_time_rate (0-1)            ->  on_time_payment_pct (0-100)     x100
dti                           ->  debt_to_income_ratio (0-1)      as is
credit_util (0-1)             ->  credit_utilization_pct (0-100)  x100
delinq_30plus/60plus/90plus   ->  delinquency_flags               ["30-day-miss", "60-day-miss", "90-day-miss"] per count
positive_habits               ->  positive_habits_count           int
risk_flags                    ->  risk_flags_count                int
"""
from common.schemas import UserFeatures

EDUCATION_MAP = {"master": "masters", "phd": "phd", "bachelor": "bachelor",
                 "cert": "certification", "highschool": "high_school", "none": "none"}
HOUSING_MAP = {"owner": "own", "rent": "rent", "none": "none"}


def _num(value, default=0.0):
    """Missing or invalid numbers become the default instead of crashing."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def raw_to_user_features(raw: dict) -> UserFeatures:
    """One row of merged_data.json -> UserFeatures (the shared schema)."""
    income = _num(raw.get("monthly_income"))
    spend = _num(raw.get("monthly_spend"))
    flags = (["30-day-miss"] * int(_num(raw.get("delinq_30plus")))
             + ["60-day-miss"] * int(_num(raw.get("delinq_60plus")))
             + ["90-day-miss"] * int(_num(raw.get("delinq_90plus"))))
    return UserFeatures(
        user_id=str(raw["user_id"]),
        months_employed=int(_num(raw.get("months_at_job"))),
        housing_status=HOUSING_MAP.get(str(raw.get("housing")).lower(), "none"),
        housing_months=int(_num(raw.get("rent_on_time_months"))),
        digital_bill_ontime_pct=round(_num(raw.get("digital_payment_rate")) * 100, 2),
        education_level=EDUCATION_MAP.get(str(raw.get("education")).lower(), "none"),
        spend_to_income_ratio=round(spend / income, 4) if income > 0 else 0.0,
        essential_spend_pct=round(_num(raw.get("essential_pct")) * 100, 2),
        cashflow_volatility_pct=round(_num(raw.get("cashflow_volatility")) * 100, 2),
        savings_days=int(_num(raw.get("savings_days"))),
        on_time_payment_pct=round(_num(raw.get("on_time_rate")) * 100, 2),
        debt_to_income_ratio=_num(raw.get("dti")),
        credit_utilization_pct=round(_num(raw.get("credit_util")) * 100, 2),
        delinquency_flags=flags,
        positive_habits_count=int(_num(raw.get("positive_habits"))),
        risk_flags_count=int(_num(raw.get("risk_flags"))),
    )


# ---- UserFeatures -> model input row (column order is fixed here, used by train + predict) ----
NUMERIC_FEATURES = [
    "months_employed", "housing_months", "digital_bill_ontime_pct", "spend_to_income_ratio",
    "essential_spend_pct", "cashflow_volatility_pct", "savings_days", "on_time_payment_pct",
    "debt_to_income_ratio", "credit_utilization_pct", "delinq_30", "delinq_60", "delinq_90",
    "positive_habits_count", "risk_flags_count",
]
CATEGORICAL_FEATURES = ["housing_status", "education_level"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def user_features_to_model_row(f: UserFeatures) -> dict:
    row = {name: getattr(f, name) for name in NUMERIC_FEATURES if hasattr(f, name)}
    row["delinq_30"] = sum("30" in flag for flag in f.delinquency_flags)
    row["delinq_60"] = sum("60" in flag for flag in f.delinquency_flags)
    row["delinq_90"] = sum("90" in flag for flag in f.delinquency_flags)
    row["housing_status"] = f.housing_status
    row["education_level"] = f.education_level
    return {name: row[name] for name in MODEL_FEATURES}


def score_head_matrix(preprocessed, pd_prob):
    """Input for the score head: the preprocessed features plus the PD-based score (1000 x (1 - PD))."""
    import numpy as np
    x = preprocessed.toarray() if hasattr(preprocessed, "toarray") else np.asarray(preprocessed)
    return np.column_stack([x, 1000 * (1 - np.asarray(pd_prob))])
