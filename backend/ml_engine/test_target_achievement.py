"""
Tests + demo for find_min_change().

Run from the repo root:
    python -m pytest backend/ml_engine/test_target_achievement.py -v
    python -m backend.ml_engine.test_target_achievement        # tests + demo on real users
"""

from pathlib import Path

from common.schemas import ScoreBreakdown, ScoreResult, UserFeatures
from backend.ml_engine.target_achievement import find_min_change


# =====================================================================================
# TEMPORARY STUB — DELETE AFTER MERGE.
# Stand-in for backend/scoring_engine's compute_score(), so find_min_change() can be
# tested before that module exists. Once the team merges, delete _stub_compute_score and
# its helpers and use:
#     from backend.scoring_engine.engine import compute_score
# (use whatever path/name the scoring_engine owner actually ships).
#
# Implements the point table EXACTLY as given. Bonus/penalty are NOT included (they
# weren't in the table), so real-engine scores may be up to +/-50 different.
# =====================================================================================

def _stub_employment(m):   return 150 if m >= 24 else 100 if m >= 12 else 50 if m >= 6 else 0
def _stub_digital(p):      return 70 if p >= 95 else 45 if p >= 80 else 20 if p >= 60 else 0
def _stub_spend(r):        return 120 if r <= 0.30 else 80 if r <= 0.50 else 40 if r <= 0.70 else 0
def _stub_essential(p):    return 80 if p >= 70 else 45 if p >= 55 else 20 if p >= 40 else 0
def _stub_volatility(p):   return 70 if p <= 5 else 40 if p <= 10 else 15 if p <= 20 else 0
def _stub_savings(d):      return 80 if d >= 180 else 50 if d >= 90 else 20 if d >= 30 else 0
def _stub_ontime(p):       return 200 if p >= 98 else 150 if p >= 95 else 100 if p >= 90 else 50 if p >= 80 else 0
def _stub_dti(r):          return 120 if r <= 0.20 else 80 if r <= 0.35 else 40 if r <= 0.50 else 0
def _stub_util(p):         return 100 if p <= 10 else 70 if p <= 30 else 30 if p <= 50 else 0


def _stub_housing(status, months):
    if status == "own":
        return 80
    if status == "rent":
        return 60 if months >= 12 else 30
    return 0


def _stub_education(level):
    return {"masters": 50, "phd": 50, "bachelor": 40, "certification": 30, "high_school": 20}.get(level, 0)


def _stub_delinquency(flags):
    if not flags:
        return 150
    if len(flags) > 1 or any("90" in f for f in flags):
        return 0
    if "60" in flags[0]:
        return 50
    if "30" in flags[0]:
        return 100
    return 0


def _stub_compute_score(features: UserFeatures) -> ScoreResult:
    b = ScoreBreakdown(
        employment_stability=_stub_employment(features.months_employed),
        housing_status=_stub_housing(features.housing_status, features.housing_months),
        digital_footprint=_stub_digital(features.digital_bill_ontime_pct),
        education=_stub_education(features.education_level),
        spend_to_income=_stub_spend(features.spend_to_income_ratio),
        expense_diversity=_stub_essential(features.essential_spend_pct),
        cashflow_volatility=_stub_volatility(features.cashflow_volatility_pct),
        savings=_stub_savings(features.savings_days),
        on_time_payment=_stub_ontime(features.on_time_payment_pct),
        debt_to_income=_stub_dti(features.debt_to_income_ratio),
        credit_utilization=_stub_util(features.credit_utilization_pct),
        delinquency=_stub_delinquency(features.delinquency_flags),
    )
    total = max(0, min(1000, sum(b.model_dump().values())))
    band = "Excellent" if total >= 800 else "Good" if total >= 600 else "Fair" if total >= 400 else "Poor"
    return ScoreResult(user_id=features.user_id, total_score=total, risk_category=band, breakdown=b)

# ============================ END OF TEMPORARY STUB ==================================


def _profile(**overrides) -> UserFeatures:
    """Stub score 930: everything maxed except education (HS), housing (none), on-time (85%), savings (25d)."""
    base = dict(
        user_id="T1", months_employed=30, housing_status="none", housing_months=0,
        digital_bill_ontime_pct=97, education_level="high_school", spend_to_income_ratio=0.25,
        essential_spend_pct=75, cashflow_volatility_pct=4, savings_days=25, on_time_payment_pct=85,
        debt_to_income_ratio=0.15, credit_utilization_pct=5, delinquency_flags=[],
    )
    base.update(overrides)
    return UserFeatures(**base)


def _rescore_with(features, change):
    updated = features.model_copy(update={change["feature_field"]: change["target_raw"]})
    return _stub_compute_score(updated).total_score


def test_stub_sanity():
    assert _stub_compute_score(_profile()).total_score == 930


def test_already_qualifies():
    out = find_min_change(_profile(), 900, _stub_compute_score)
    assert out["gap_closed"] and out["suggested_change"] is None and out["score_gap"] == 0


def test_low_savings_user_gets_savings_suggestion():
    # Gap 15. Savings 25->30 days (+20, tiny effort) beats on-time 85->90% (+50, big effort).
    out = find_min_change(_profile(), 945, _stub_compute_score, "Premium Card")
    s = out["suggested_change"]
    assert s["feature_field"] == "savings_days"
    assert s["target_raw"] == 30 and s["expected_point_gain"] == 20
    assert out["single_change_closes_gap"] and out["gap_closed"]
    assert "Premium Card" in out["message"]


def test_picks_cheapest_lever_that_closes_gap():
    # Volatility 10.5% -> 10% is a +25 pt, near-zero-effort fix.
    f = _profile(cashflow_volatility_pct=10.5, savings_days=200)
    base = _stub_compute_score(f).total_score
    out = find_min_change(f, base + 20, _stub_compute_score)
    assert out["suggested_change"]["feature_field"] == "cashflow_volatility_pct"
    assert out["suggested_change"]["target_raw"] == 10.0


def test_suggested_gain_is_reproducible():
    f = _profile()
    out = find_min_change(f, 945, _stub_compute_score)
    s = out["suggested_change"]
    assert _rescore_with(f, s) - out["current_score"] == s["expected_point_gain"]


def test_large_gap_builds_multi_step_plan():
    weak = UserFeatures(
        user_id="T2", months_employed=8, housing_status="rent", housing_months=6,
        digital_bill_ontime_pct=70, education_level="high_school", spend_to_income_ratio=0.65,
        essential_spend_pct=50, cashflow_volatility_pct=18, savings_days=10, on_time_payment_pct=82,
        debt_to_income_ratio=0.45, credit_utilization_pct=45, delinquency_flags=[],
    )
    base = _stub_compute_score(weak).total_score
    out = find_min_change(weak, base + 200, _stub_compute_score)  # max single-lever gain is +150
    assert not out["single_change_closes_gap"]
    assert len(out["plan"]) > 1
    assert out["projected_score"] > base
    assert sum(s["expected_point_gain"] for s in out["plan"]) == out["projected_score"] - base


def test_accepts_dict_style_compute_score():
    # scoring_engine/README says compute_score(dict) -> dict; make sure that also works.
    def dict_scorer(d: dict) -> dict:
        return _stub_compute_score(UserFeatures(**d)).model_dump()
    a = find_min_change(_profile(), 945, _stub_compute_score)
    b = find_min_change(_profile(), 945, dict_scorer)
    assert a["suggested_change"] == b["suggested_change"]


def test_bad_target_rejected():
    for bad in (-5, 1001):
        try:
            find_min_change(_profile(), bad, _stub_compute_score)
            assert False
        except ValueError:
            pass


# ------------------------------------------------------------------ demo on real data

def _demo():
    users_path, catalog_path = Path("data/merged_data.json"), Path("data/product_catalog.json")
    if not users_path.exists() or not catalog_path.exists():
        print(f"\n(skipped real-data demo: need {users_path} and {catalog_path})")
        return

    from backend.ml_engine.raw_user_mapping import load_user_features
    from backend.recommendations.catalog import load_product_catalog

    users = load_user_features(users_path)
    products = sorted(load_product_catalog(catalog_path), key=lambda p: p.min_score_required)
    scored = [(u, _stub_compute_score(u).total_score) for u in users]
    print(f"\nLoaded {len(users)} users; stub scores range {min(s for _, s in scored)}-{max(s for _, s in scored)}")

    def next_product(score):
        return next((p for p in products if p.min_score_required > score), None)

    # Pick: the lowest-savings user, the median-score user, and the lowest-score user —
    # each aiming for the next product they don't yet qualify for.
    candidates = [(u, s) for u, s in scored if next_product(s)]
    picks = {
        "lowest savings": min(candidates, key=lambda x: x[0].savings_days),
        "median score": sorted(candidates, key=lambda x: x[1])[len(candidates) // 2],
        "lowest score": min(candidates, key=lambda x: x[1]),
    }
    for why, (user, score) in picks.items():
        product = next_product(score)
        out = find_min_change(user, product.min_score_required, _stub_compute_score, product.name)
        s = out["suggested_change"]
        print(f"\n--- {why}: {user.user_id} | score {score} -> wants {product.name} ({product.min_score_required}) "
              f"| savings_days={user.savings_days}")
        if s:
            print(f"    best single change: {s['sub_factor']} {s['current_value']} -> {s['target_value']} "
                  f"(+{s['expected_point_gain']} pts, effort {s['effort']})")
            assert _rescore_with(user, s) - score == s["expected_point_gain"]
        for i, step in enumerate(out["plan"], 1):
            print(f"    plan {i}: {step['feature_field']:<24} {step['current_value']:>8} -> {step['target_value']:<9} +{step['expected_point_gain']}")
        print(f"    projected {out['projected_score']} | gap closed: {out['gap_closed']}")
        print(f"    message: {out['message']}")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS  {name}")
    _demo()