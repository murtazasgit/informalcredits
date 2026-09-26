"""
Explainability module — converts score breakdown into human-readable factor analysis.
Template-based (no LLM/AI), deterministic and auditable.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.schemas import ScoreBreakdown, Factor, ExplainResult


# Friendly labels for each scoring sub-factor
LABELS = {
    "employment_stability": "Employment stability",
    "housing_status": "Housing / rent history",
    "digital_footprint": "Utility & bill payment consistency",
    "education": "Education level",
    "spend_to_income": "Spending-to-income ratio",
    "expense_diversity": "Essential vs. discretionary spending",
    "cashflow_volatility": "Monthly cash-flow stability",
    "savings": "Savings buffer",
    "on_time_payment": "On-time payment track record",
    "debt_to_income": "Debt-to-income ratio",
    "credit_utilization": "Credit utilization",
    "delinquency": "Payment delinquency record",
    "bonus": "Positive financial habits",
    "penalty": "Risk flags detected",
}

# Max points for each sub-factor (used to determine "good" vs "needs improvement")
MAX_POINTS = {
    "employment_stability": 150,
    "housing_status": 80,
    "digital_footprint": 70,
    "education": 50,
    "spend_to_income": 120,
    "expense_diversity": 80,
    "cashflow_volatility": 70,
    "savings": 80,
    "on_time_payment": 200,
    "debt_to_income": 120,
    "credit_utilization": 100,
    "delinquency": 150,
    "bonus": 50,
    "penalty": 0,
}


def explain_breakdown(breakdown: ScoreBreakdown, user_id: str = "") -> ExplainResult:
    """
    Convert a ScoreBreakdown into a list of Factor objects sorted by impact,
    plus a human-readable summary sentence.
    """
    breakdown_dict = breakdown.model_dump()
    factors = []

    for key, points in breakdown_dict.items():
        label = LABELS.get(key, key.replace("_", " ").title())
        direction = "positive" if points >= 0 else "negative"
        factors.append(Factor(label=label, points=points, direction=direction))

    # Sort by absolute impact (most impactful first)
    factors.sort(key=lambda f: abs(f.points), reverse=True)

    # Generate summary
    summary = generate_summary(factors)

    return ExplainResult(
        user_id=user_id,
        factors=factors,
        summary_text=summary,
    )


def generate_summary(factors: list[Factor]) -> str:
    """Generate a plain-English summary sentence from factor list."""
    top_positive = [f for f in factors if f.direction == "positive" and f.points > 0][:3]
    top_negative = [f for f in factors if f.direction == "negative"][:2]

    parts = []
    if top_positive:
        labels = " and ".join(f.label.lower() for f in top_positive)
        parts.append(f"Your score is strong mainly due to {labels}.")

    if top_negative:
        labels = " and ".join(f.label.lower() for f in top_negative)
        parts.append(f"{labels.capitalize()} slightly reduced your score.")

    if not parts:
        return "Your financial profile is well-balanced across all factors."

    return " ".join(parts)
