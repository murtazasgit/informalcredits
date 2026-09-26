from pathlib import Path

from backend.explainability.explainer import explain_breakdown
from backend.recommendations.recommender import recommend_products
from backend.scoring_engine.engine import compute_score, simulate_change
from common.schemas import Product, ScoreBreakdown, UserFeatures
from data.feature_engineering import get_all_user_features, load_products


def make_features(**overrides):
    values = {
        "user_id": "TEST1",
        "months_employed": 30,
        "housing_status": "own",
        "housing_months": 24,
        "digital_bill_ontime_pct": 98,
        "education_level": "masters",
        "spend_to_income_ratio": 0.25,
        "essential_spend_pct": 75,
        "cashflow_volatility_pct": 3,
        "savings_days": 200,
        "on_time_payment_pct": 99,
        "debt_to_income_ratio": 0.15,
        "credit_utilization_pct": 5,
        "delinquency_flags": [],
    }
    values.update(overrides)
    return UserFeatures(**values)


def test_scoring_and_simulation_return_consistent_results():
    features = make_features(
        savings_days=29, months_employed=0, housing_status="none", housing_months=0
    )

    score = compute_score(features)
    simulation = simulate_change(features, {"savings_days": 30})

    assert score.total_score == 960
    assert score.risk_category == "Excellent"
    assert score.method == "rule_based"
    assert simulation.old_score == score.total_score
    assert simulation.new_score == 980
    assert simulation.delta == 20


def test_explanation_covers_breakdown_and_marks_negative_factors():
    explanation = explain_breakdown(
        ScoreBreakdown(employment_stability=100, penalty=-20), user_id="TEST1"
    )

    assert explanation.user_id == "TEST1"
    assert len(explanation.factors) == len(ScoreBreakdown().model_dump())
    assert explanation.factors[0].label == "Employment stability"
    penalty = next(factor for factor in explanation.factors if factor.label == "Risk flags detected")
    assert penalty.points == -20
    assert penalty.direction == "negative"


def test_recommendations_prioritize_eligible_products_by_rate():
    products = [
        Product(product_id="P3", name="Premium", type="card", min_score_required=800, interest_rate=12),
        Product(product_id="P2", name="Basic B", type="card", min_score_required=600, interest_rate=18),
        Product(product_id="P1", name="Basic A", type="card", min_score_required=500, interest_rate=15),
    ]

    recommendations = recommend_products(650, products)

    assert [item.product_id for item in recommendations] == ["P1", "P2", "P3"]
    assert [item.eligible for item in recommendations] == [True, True, False]
    assert "50 points below" in recommendations[-1].reason


def test_bundled_users_run_through_all_mvp_models():
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data" / "Datasets_AltCredit"
    features_by_user = get_all_user_features(str(data_dir))
    products = [
        Product(**product)
        for product in load_products(str(data_dir / "product_catalog.json"))
    ]

    assert features_by_user
    assert products

    for features in features_by_user.values():
        score = compute_score(features)
        explanation = explain_breakdown(score.breakdown, user_id=features.user_id)
        recommendations = recommend_products(score.total_score, products)
        simulation = simulate_change(features, {"savings_days": features.savings_days + 30})

        assert 0 <= score.total_score <= 1000
        assert len(explanation.factors) == len(ScoreBreakdown().model_dump())
        assert len(recommendations) == len(products)
        assert simulation.user_id == features.user_id