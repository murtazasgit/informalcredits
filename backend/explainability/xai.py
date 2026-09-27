"""
Plain-language explanation of a score for the "Why this score" tab. No charts of raw numbers: every item is a
sentence a borrower can act on.

  headline      one sentence: the score, the band, and the main reason for it
  helping       the things working in the borrower's favour, each with the actual value that earned it
  holding_back  the things costing points, each with how many points are on the table
  actions       specific changes and the points each would add (rule engine, so the numbers are exact)
  second_opinion  what the independent ML model thinks, in one paragraph plus its top reasons in words
  fairness      what the scoring never looks at
"""
from typing import Optional

from backend.explainability.explainer import LABELS, MAX_POINTS
from backend.scoring_engine.engine import compute_score
from common.schemas import UserFeatures

# what the borrower's own value looks like, per rule factor
_FACT = {
    "employment_stability": lambda f: f"You have been in your current job for {f.months_employed} months",
    "housing_status": lambda f: f"Your housing record ({f.housing_status.replace('_', ' ')}, {f.housing_months} months of history)",
    "digital_footprint": lambda f: f"{f.digital_bill_ontime_pct:.0f}% of your utility and digital bills are paid on time",
    "education": lambda f: f"Your education level ({f.education_level.replace('_', ' ')})",
    "spend_to_income": lambda f: f"You spend about {f.spend_to_income_ratio * 100:.0f}% of your income",
    "expense_diversity": lambda f: f"{f.essential_spend_pct:.0f}% of your spending goes to essentials",
    "cashflow_volatility": lambda f: f"Your monthly cash flow swings by about {f.cashflow_volatility_pct:.0f}%",
    "savings": lambda f: f"You keep about {f.savings_days} days of expenses in savings",
    "on_time_payment": lambda f: f"{f.on_time_payment_pct:.0f}% of your payments are made on time",
    "debt_to_income": lambda f: f"Your debts equal about {f.debt_to_income_ratio * 100:.0f}% of your income",
    "credit_utilization": lambda f: f"You are using {f.credit_utilization_pct:.0f}% of your available credit",
    "delinquency": lambda f: ("You have missed payments on record: " + ", ".join(f.delinquency_flags)) if f.delinquency_flags
                             else "You have no missed payments on record",
    "bonus": lambda f: f"You show {f.positive_habits_count} positive money habit(s)",
    "penalty": lambda f: f"{f.risk_flags_count} risk flag(s) were detected in your activity",
}

# field -> (action sentence, strong value, weak value, watch-out sentence)
_ACTIONS = {
    "on_time_payment_pct": ("Pay every bill and EMI on time (100%)", 100, 70, "Paying only about 70% of bills on time"),
    "savings_days": ("Build savings to cover 45 days of expenses", 45, 0, "Having no savings cushion"),
    "debt_to_income_ratio": ("Bring your debts down to 15% of your income", 0.15, 0.6, "Letting debts reach 60% of income"),
    "credit_utilization_pct": ("Keep your credit use at 20% or less", 20, 90, "Using 90% of your available credit"),
    "spend_to_income_ratio": ("Spend no more than half of your income", 0.5, 1.0, "Spending all of your income"),
    "cashflow_volatility_pct": ("Keep your monthly cash flow steady", 10, 60, "Large swings in monthly cash flow"),
    "digital_bill_ontime_pct": ("Pay all utility and digital bills on time", 100, 50, "Paying only half of your bills on time"),
    "months_employed": ("Stay in your current job for three years", 36, 3, "Changing jobs so it resets to 3 months"),
}


def _plain(name: str) -> str:
    return name.replace("_", " ")


def _factors(features: UserFeatures, score) -> tuple[list, list]:
    """(helping, holding_back) built from the rule engine's points."""
    helping, holding = [], []
    for key, pts in score.breakdown.model_dump().items():
        top = MAX_POINTS.get(key, 0)
        fact = _FACT[key](features)
        if top and pts / top >= 0.6 or (key == "bonus" and pts > 0):
            helping.append({"label": LABELS[key], "text": fact, "points": pts, "ratio": pts / top if top else 1})
        elif pts < 0 or (top and pts / top < 0.6):
            lost = -pts if pts < 0 else top - pts
            holding.append({"label": LABELS[key], "text": fact, "points_lost": lost})
    helping.sort(key=lambda h: (h["ratio"], h["points"]), reverse=True)
    holding.sort(key=lambda h: h["points_lost"], reverse=True)
    for h in helping:
        h.pop("ratio")
    return helping[:4], holding[:4]


def _actions(features: UserFeatures, base: int) -> tuple[list, list]:
    data = features.model_dump()
    gains, risks = [], []
    for field, (do, strong, weak, watch) in _ACTIONS.items():
        def delta(value):
            return compute_score(UserFeatures(**{**data, field: value})).total_score - base

        gain, loss = delta(strong), delta(weak)
        if gain > 0:
            gains.append({"text": do, "points": gain})
        if loss < 0:
            risks.append({"text": watch, "points": loss})
    gains.sort(key=lambda a: a["points"], reverse=True)
    risks.sort(key=lambda a: a["points"])
    return gains[:4], risks[:3]


def _second_opinion(rule: int, ml: Optional[dict]) -> Optional[dict]:
    if not ml:
        return None
    gap = ml["total_score"] - rule
    if abs(gap) <= 40:
        verdict, tone = "agree", "The two methods agree, so you can trust this score."
    elif abs(gap) <= 100:
        verdict, tone = "close", "The two methods are fairly close; small differences are normal."
    else:
        verdict, tone = "differ", "The two methods differ noticeably, so treat this score with some caution."
    pd_pct = ml["probability_of_default"] * 100
    drivers = [{"text": f"Your {_plain(d['feature'])} is {'pushing your risk up' if d['direction'] == 'hurts' else 'keeping your risk down'}",
                "direction": d["direction"]} for d in ml.get("drivers", [])[:4]]
    return {
        "verdict": verdict,
        "text": (f"We also ask an independent statistical model, trained on past repayment outcomes. It estimates "
                 f"a {pd_pct:.0f}% chance of default, which equals a score of about {ml['total_score']} "
                 f"(the rules give {rule}). {tone}"),
        "drivers": drivers,
    }


def build_xai(features: UserFeatures, ml_score: Optional[dict]) -> dict:
    score = compute_score(features)
    helping, holding = _factors(features, score)
    actions, watch_outs = _actions(features, score.total_score)
    if holding:
        main = f"Your biggest drag is {holding[0]['label'].lower()}."
    else:
        main = "Nothing is holding your score back in a big way."
    return {
        "user_id": features.user_id,
        "score": score.total_score,
        "risk_category": score.risk_category,
        "headline": f"Your score is {score.total_score} out of 1000, which is rated {score.risk_category}. {main}",
        "helping": helping,
        "holding_back": holding,
        "actions": actions,
        "watch_outs": watch_outs,
        "second_opinion": _second_opinion(score.total_score, ml_score),
        "fairness": ("Your score uses only how you handle money. It never looks at your name, gender, religion, "
                     "caste, age, address or phone number, and everyone is scored with the same rules."),
    }
