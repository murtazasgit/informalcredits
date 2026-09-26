"""
Score-accuracy tests against a ground truth that is written independently from the spec's
point table (NOT by calling the engine's own helper functions).

  * every threshold boundary of every sub-factor is asserted;
  * 300 seeded synthetic profiles are scored by both the engine and a table-driven oracle;
  * a few hand-computed profiles pin exact totals and risk tiers.
"""
import random

import pytest

from backend.scoring_engine.engine import compute_score
from common.schemas import UserFeatures


def make(**kw) -> UserFeatures:
    base = dict(
        user_id="GT", months_employed=0, housing_status="none", housing_months=0,
        digital_bill_ontime_pct=0, education_level="none", spend_to_income_ratio=0.9,
        essential_spend_pct=0, cashflow_volatility_pct=50, savings_days=0,
        on_time_payment_pct=0, debt_to_income_ratio=0.9, credit_utilization_pct=90,
        delinquency_flags=["90_day_late"], positive_habits_count=0, risk_flags_count=0,
    )
    base.update(kw)
    return UserFeatures(**base)


def bd(**kw):
    return compute_score(make(**kw)).breakdown


# (field overrides, breakdown attribute, expected points) — straight from the spec table
BOUNDARY_CASES = [
    # Employment stability
    ({"months_employed": 24}, "employment_stability", 150),
    ({"months_employed": 23}, "employment_stability", 100),
    ({"months_employed": 12}, "employment_stability", 100),
    ({"months_employed": 11}, "employment_stability", 50),
    ({"months_employed": 6}, "employment_stability", 50),
    ({"months_employed": 5}, "employment_stability", 0),
    # Housing
    ({"housing_status": "own"}, "housing_status", 80),
    ({"housing_status": "rent", "housing_months": 12}, "housing_status", 60),
    ({"housing_status": "rent", "housing_months": 11}, "housing_status", 30),
    ({"housing_status": "none"}, "housing_status", 0),
    # Digital footprint
    ({"digital_bill_ontime_pct": 95}, "digital_footprint", 70),
    ({"digital_bill_ontime_pct": 94}, "digital_footprint", 45),
    ({"digital_bill_ontime_pct": 80}, "digital_footprint", 45),
    ({"digital_bill_ontime_pct": 79}, "digital_footprint", 20),
    ({"digital_bill_ontime_pct": 60}, "digital_footprint", 20),
    ({"digital_bill_ontime_pct": 59}, "digital_footprint", 0),
    # Education
    ({"education_level": "masters"}, "education", 50),
    ({"education_level": "phd"}, "education", 50),
    ({"education_level": "bachelor"}, "education", 40),
    ({"education_level": "certification"}, "education", 30),
    ({"education_level": "high_school"}, "education", 20),
    ({"education_level": "none"}, "education", 0),
    # Spend-to-income
    ({"spend_to_income_ratio": 0.30}, "spend_to_income", 120),
    ({"spend_to_income_ratio": 0.31}, "spend_to_income", 80),
    ({"spend_to_income_ratio": 0.50}, "spend_to_income", 80),
    ({"spend_to_income_ratio": 0.51}, "spend_to_income", 40),
    ({"spend_to_income_ratio": 0.70}, "spend_to_income", 40),
    ({"spend_to_income_ratio": 0.71}, "spend_to_income", 0),
    # Expense diversity (essentials %)
    ({"essential_spend_pct": 70}, "expense_diversity", 80),
    ({"essential_spend_pct": 69}, "expense_diversity", 45),
    ({"essential_spend_pct": 55}, "expense_diversity", 45),
    ({"essential_spend_pct": 54}, "expense_diversity", 20),
    ({"essential_spend_pct": 40}, "expense_diversity", 20),
    ({"essential_spend_pct": 39}, "expense_diversity", 0),
    # Cash-flow volatility
    ({"cashflow_volatility_pct": 5}, "cashflow_volatility", 70),
    ({"cashflow_volatility_pct": 5.1}, "cashflow_volatility", 40),
    ({"cashflow_volatility_pct": 10}, "cashflow_volatility", 40),
    ({"cashflow_volatility_pct": 10.1}, "cashflow_volatility", 15),
    ({"cashflow_volatility_pct": 20}, "cashflow_volatility", 15),
    ({"cashflow_volatility_pct": 20.1}, "cashflow_volatility", 0),
    # Savings days
    ({"savings_days": 180}, "savings", 80),
    ({"savings_days": 179}, "savings", 50),
    ({"savings_days": 90}, "savings", 50),
    ({"savings_days": 89}, "savings", 20),
    ({"savings_days": 30}, "savings", 20),
    ({"savings_days": 29}, "savings", 0),
    # On-time payment rate
    ({"on_time_payment_pct": 98}, "on_time_payment", 200),
    ({"on_time_payment_pct": 97}, "on_time_payment", 150),
    ({"on_time_payment_pct": 95}, "on_time_payment", 150),
    ({"on_time_payment_pct": 94}, "on_time_payment", 100),
    ({"on_time_payment_pct": 90}, "on_time_payment", 100),
    ({"on_time_payment_pct": 89}, "on_time_payment", 50),
    ({"on_time_payment_pct": 80}, "on_time_payment", 50),
    ({"on_time_payment_pct": 79}, "on_time_payment", 0),
    # Debt-to-income
    ({"debt_to_income_ratio": 0.20}, "debt_to_income", 120),
    ({"debt_to_income_ratio": 0.21}, "debt_to_income", 80),
    ({"debt_to_income_ratio": 0.35}, "debt_to_income", 80),
    ({"debt_to_income_ratio": 0.36}, "debt_to_income", 40),
    ({"debt_to_income_ratio": 0.50}, "debt_to_income", 40),
    ({"debt_to_income_ratio": 0.51}, "debt_to_income", 0),
    # Credit utilisation
    ({"credit_utilization_pct": 10}, "credit_utilization", 100),
    ({"credit_utilization_pct": 11}, "credit_utilization", 70),
    ({"credit_utilization_pct": 30}, "credit_utilization", 70),
    ({"credit_utilization_pct": 31}, "credit_utilization", 30),
    ({"credit_utilization_pct": 50}, "credit_utilization", 30),
    ({"credit_utilization_pct": 51}, "credit_utilization", 0),
    # Delinquency severity
    ({"delinquency_flags": []}, "delinquency", 150),
    ({"delinquency_flags": ["30_day_late"]}, "delinquency", 100),
    ({"delinquency_flags": ["60_day_late"]}, "delinquency", 50),
    ({"delinquency_flags": ["90_day_late"]}, "delinquency", 0),
    ({"delinquency_flags": ["multiple_late"]}, "delinquency", 0),
    ({"delinquency_flags": ["30_day_late", "60_day_late"]}, "delinquency", 0),
    # Bonus / penalty
    ({"positive_habits_count": 0}, "bonus", 0),
    ({"positive_habits_count": 1}, "bonus", 20),
    ({"positive_habits_count": 2}, "bonus", 40),
    ({"positive_habits_count": 3}, "bonus", 50),   # 3 x 20 = 60, capped at +50
    ({"positive_habits_count": 9}, "bonus", 50),
    ({"risk_flags_count": 0}, "penalty", 0),
    ({"risk_flags_count": 1}, "penalty", -20),
    ({"risk_flags_count": 2}, "penalty", -40),
    ({"risk_flags_count": 3}, "penalty", -50),     # 3 x -20 = -60, capped at -50
    ({"risk_flags_count": 9}, "penalty", -50),
]


@pytest.mark.parametrize("overrides,attr,expected", BOUNDARY_CASES,
                         ids=[f"{a}-{list(o.values())}" for o, a, _ in BOUNDARY_CASES])
def test_sub_factor_boundaries_match_spec(overrides, attr, expected):
    assert getattr(bd(**overrides), attr) == expected


# ---------- independent oracle (threshold tables, deliberately not the engine's if-chains) ----------

def _band(value, table, default=0):
    """table: [(min_inclusive, points), ...] sorted descending by min."""
    for lo, pts in table:
        if value >= lo:
            return pts
    return default


def _band_le(value, table, default=0):
    """table: [(max_inclusive, points), ...] sorted ascending by max."""
    for hi, pts in table:
        if value <= hi:
            return pts
    return default


EDU = {"masters": 50, "phd": 50, "bachelor": 40, "certification": 30, "high_school": 20}


def oracle_total(f: UserFeatures) -> int:
    total = 0
    total += _band(f.months_employed, [(24, 150), (12, 100), (6, 50)])
    total += 80 if f.housing_status == "own" else (
        (60 if f.housing_months >= 12 else 30) if f.housing_status == "rent" else 0)
    total += _band(f.digital_bill_ontime_pct, [(95, 70), (80, 45), (60, 20)])
    total += EDU.get(f.education_level, 0)
    total += _band_le(f.spend_to_income_ratio, [(0.30, 120), (0.50, 80), (0.70, 40)])
    total += _band(f.essential_spend_pct, [(70, 80), (55, 45), (40, 20)])
    total += _band_le(f.cashflow_volatility_pct, [(5, 70), (10, 40), (20, 15)])
    total += _band(f.savings_days, [(180, 80), (90, 50), (30, 20)])
    total += _band(f.on_time_payment_pct, [(98, 200), (95, 150), (90, 100), (80, 50)])
    total += _band_le(f.debt_to_income_ratio, [(0.20, 120), (0.35, 80), (0.50, 40)])
    total += _band_le(f.credit_utilization_pct, [(10, 100), (30, 70), (50, 30)])
    flags = f.delinquency_flags
    total += 150 if not flags else (100 if flags == ["30_day_late"] else 50 if flags == ["60_day_late"] else 0)
    total += min(20 * f.positive_habits_count, 50)
    total -= min(20 * f.risk_flags_count, 50)
    return max(0, min(1000, total))


def synthetic_profiles(n=300, seed=42):
    rng = random.Random(seed)
    for i in range(n):
        yield UserFeatures(
            user_id=f"SYN{i}",
            months_employed=rng.randint(0, 60),
            housing_status=rng.choice(["own", "rent", "none"]),
            housing_months=rng.randint(0, 60),
            digital_bill_ontime_pct=round(rng.uniform(0, 100), 1),
            education_level=rng.choice(["masters", "phd", "bachelor", "certification", "high_school", "none"]),
            spend_to_income_ratio=round(rng.uniform(0, 1.2), 2),
            essential_spend_pct=round(rng.uniform(0, 100), 1),
            cashflow_volatility_pct=round(rng.uniform(0, 40), 1),
            savings_days=rng.randint(0, 365),
            on_time_payment_pct=round(rng.uniform(50, 100), 1),
            debt_to_income_ratio=round(rng.uniform(0, 0.8), 2),
            credit_utilization_pct=round(rng.uniform(0, 100), 1),
            delinquency_flags=rng.choice([[], ["30_day_late"], ["60_day_late"], ["90_day_late"], ["multiple_late"]]),
            positive_habits_count=rng.randint(0, 3),
            risk_flags_count=rng.randint(0, 3),
        )


def test_engine_matches_independent_oracle_on_300_synthetic_profiles():
    mismatches = [(f.user_id, compute_score(f).total_score, oracle_total(f))
                  for f in synthetic_profiles() if compute_score(f).total_score != oracle_total(f)]
    assert mismatches == []


def test_hand_computed_profiles_and_tiers():
    # Best possible: 1320 raw points, clamped to 1000 -> Excellent
    best = make(months_employed=36, housing_status="own", digital_bill_ontime_pct=99, education_level="phd",
                spend_to_income_ratio=0.2, essential_spend_pct=80, cashflow_volatility_pct=2, savings_days=200,
                on_time_payment_pct=99, debt_to_income_ratio=0.1, credit_utilization_pct=5,
                delinquency_flags=[], positive_habits_count=3)
    r = compute_score(best)
    assert (r.total_score, r.risk_category) == (1000, "Excellent")

    # Worst possible: all zeros, penalties push below zero -> clamped to 0 -> Poor
    worst = make(risk_flags_count=3)
    r = compute_score(worst)
    assert (r.total_score, r.risk_category) == (0, "Poor")

    # Mid profile, summed by hand:
    # emp 12mo=100, rent 12mo=60, digital 85=45, bachelor=40 -> lifestyle 245
    # spend .4=80, essentials 60=45, volatility 8=40, savings 90=50 -> 215
    # on-time 92=100, dti .3=80, util 25=70, one 30d late=100 -> 350
    # bonus 2 habits=+40, 1 risk flag=-20 -> 20      total = 830
    mid = make(months_employed=12, housing_status="rent", housing_months=12, digital_bill_ontime_pct=85,
               education_level="bachelor", spend_to_income_ratio=0.4, essential_spend_pct=60,
               cashflow_volatility_pct=8, savings_days=90, on_time_payment_pct=92,
               debt_to_income_ratio=0.3, credit_utilization_pct=25, delinquency_flags=["30_day_late"],
               positive_habits_count=2, risk_flags_count=1)
    r = compute_score(mid)
    assert r.total_score == 830
    assert r.risk_category == "Excellent"


def test_risk_tier_edges():
    # otp 98 (200) + emp 24 (150) + own (80) + dti .1 (120) + util 5 (100) = 650, delinquency 90d = 0
    core = dict(on_time_payment_pct=98, months_employed=24, housing_status="own",
                debt_to_income_ratio=0.1, credit_utilization_pct=5)
    cases = [
        (dict(core, delinquency_flags=[]), 800, "Excellent"),                        # 650 + 150
        (dict(core, risk_flags_count=3), 600, "Good"),                               # 650 - 50
        (dict(core), 650, "Good"),
        (dict(on_time_payment_pct=98, months_employed=12, housing_status="own",
              education_level="high_school"), 400, "Fair"),                         # 200+100+80+20
        (dict(on_time_payment_pct=98, months_employed=24, education_level="bachelor"), 390, "Poor"),
    ]
    for kw, total, tier in cases:
        r = compute_score(make(**kw))
        assert (r.total_score, r.risk_category) == (total, tier), kw
