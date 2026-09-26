"""
Rule-Based Scoring Engine — implements the exact point rules from the spec.
Turns UserFeatures into a 0-1000 score with full breakdown.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.schemas import UserFeatures, ScoreBreakdown, ScoreResult, SimulationResult


# ---------- Lifestyle (max 350) ----------

def score_employment(months: int) -> int:
    """Employment stability: >=24mo → 150, 12-23 → 100, 6-11 → 50, else 0"""
    if months >= 24: return 150
    if months >= 12: return 100
    if months >= 6: return 50
    return 0


def score_housing(status: str, months: int) -> int:
    """Housing: own → 80, rent >=12mo → 60, rent <12mo → 30, none → 0"""
    if status == "own": return 80
    if status == "rent" and months >= 12: return 60
    if status == "rent": return 30
    return 0


def score_digital_footprint(pct: float) -> int:
    """Digital footprint (on-time %): >=95 → 70, 80-94 → 45, 60-79 → 20, <60 → 0
    """
    if pct >= 95: return 70
    if pct >= 80: return 45
    if pct >= 60: return 20
    return 0


def score_education(level: str) -> int:
    """Education: Masters/PhD → 50, Bachelor → 40, Cert → 30, HS → 20, <HS → 0"""
    return {"masters": 50, "phd": 50, "bachelor": 40, "certification": 30, "high_school": 20}.get(level.lower(), 0)


# ---------- Spending Behavior (max 350) ----------

def score_spend_to_income(ratio: float) -> int:
    """Spend/income: <=30% → 120, 30-50 → 80, 50-70 → 40, >70 → 0"""
    if ratio <= 0.30: return 120
    if ratio <= 0.50: return 80
    if ratio <= 0.70: return 40
    return 0


def score_expense_diversity(essential_pct: float) -> int:
    """Essential spend %: >=70 → 80, 55-69 → 45, 40-54 → 20, <40 → 0"""
    if essential_pct >= 70: return 80
    if essential_pct >= 55: return 45
    if essential_pct >= 40: return 20
    return 0


def score_cashflow_volatility(volatility_pct: float) -> int:
    """Cash-flow volatility: <=5% → 70, 5-10 → 40, 10-20 → 15, >20 → 0"""
    if volatility_pct <= 5: return 70
    if volatility_pct <= 10: return 40
    if volatility_pct <= 20: return 15
    return 0


def score_savings(savings_days: int) -> int:
    """Savings days: >=180 → 80, 90-179 → 50, 30-89 → 20, <30 → 0"""
    if savings_days >= 180: return 80
    if savings_days >= 90: return 50
    if savings_days >= 30: return 20
    return 0


# ---------- Repayment Discipline (max 570) ----------

def score_on_time_payment(pct: float) -> int:
    """On-time payment %: >=98 → 200, 95-97 → 150, 90-94 → 100, 80-89 → 50, <80 → 0"""
    if pct >= 98: return 200
    if pct >= 95: return 150
    if pct >= 90: return 100
    if pct >= 80: return 50
    return 0


def score_debt_to_income(ratio: float) -> int:
    """Debt/income: <=20% → 120, 21-35 → 80, 36-50 → 40, >50 → 0"""
    if ratio <= 0.20: return 120
    if ratio <= 0.35: return 80
    if ratio <= 0.50: return 40
    return 0


def score_credit_utilization(pct: float) -> int:
    """Credit utilization: <=10% → 100, 11-30 → 70, 31-50 → 30, >50 → 0"""
    if pct <= 10: return 100
    if pct <= 30: return 70
    if pct <= 50: return 30
    return 0


def score_delinquency(flags: list[str]) -> int:
    """Delinquency: none → 150, 1×30-day → 100, 1×60-day → 50, 90+/multiple → 0"""
    if not flags:
        return 150
    if len(flags) == 1 and flags[0] == "30_day_late":
        return 100
    if len(flags) == 1 and flags[0] == "60_day_late":
        return 50
    return 0


# ---------- Bonus / Penalty ----------

def score_bonus(positive_habits_count: int) -> int:
    """+20 per positive habit, max +50"""
    return min(positive_habits_count * 20, 50)


def score_penalty(risk_flags_count: int) -> int:
    """-20 per risk flag, max -50 (returned as negative)"""
    return -min(risk_flags_count * 20, 50)


# ---------- Main scoring function ----------

def compute_score(features: UserFeatures) -> ScoreResult:
    """
    Compute the full credit score from user features using rule-based point system.
    Returns a ScoreResult with total_score (0-1000), risk_category, and breakdown.
    """
    breakdown = ScoreBreakdown(
        employment_stability=score_employment(features.months_employed),
        housing_status=score_housing(features.housing_status, features.housing_months),
        digital_footprint=score_digital_footprint(features.digital_bill_ontime_pct),
        education=score_education(features.education_level),
        spend_to_income=score_spend_to_income(features.spend_to_income_ratio),
        expense_diversity=score_expense_diversity(features.essential_spend_pct),
        cashflow_volatility=score_cashflow_volatility(features.cashflow_volatility_pct),
        savings=score_savings(features.savings_days),
        on_time_payment=score_on_time_payment(features.on_time_payment_pct),
        debt_to_income=score_debt_to_income(features.debt_to_income_ratio),
        credit_utilization=score_credit_utilization(features.credit_utilization_pct),
        delinquency=score_delinquency(features.delinquency_flags),
        bonus=score_bonus(features.positive_habits_count),
        penalty=score_penalty(features.risk_flags_count),
    )

    total = sum(breakdown.model_dump().values())
    total = max(0, min(1000, total))

    if total >= 800:
        risk_category = "Excellent"
    elif total >= 600:
        risk_category = "Good"
    elif total >= 400:
        risk_category = "Fair"
    else:
        risk_category = "Poor"

    return ScoreResult(
        user_id=features.user_id,
        total_score=total,
        risk_category=risk_category,
        breakdown=breakdown,
        method="rule_based",
    )


def simulate_change(features: UserFeatures, hypothetical_changes: dict) -> SimulationResult:
    """
    Re-run compute_score() with hypothetical changes to see score impact.
    """
    old_result = compute_score(features)
    updated_data = features.model_dump()
    updated_data.update(hypothetical_changes)
    updated_features = UserFeatures(**updated_data)
    new_result = compute_score(updated_features)
    delta = new_result.total_score - old_result.total_score

    if delta > 0:
        message = f"Score increases by {delta} points (from {old_result.total_score} to {new_result.total_score})."
    elif delta < 0:
        message = f"Score drops by {abs(delta)} points (from {old_result.total_score} to {new_result.total_score})."
    else:
        message = f"No change — score stays at {old_result.total_score}."

    return SimulationResult(
        user_id=features.user_id,
        old_score=old_result.total_score,
        new_score=new_result.total_score,
        delta=delta,
        message=message,
    )
