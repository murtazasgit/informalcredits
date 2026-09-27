"""
predictor.py - Case 1 inference. Loads the saved model ONCE at import time.

    from backend.ml_engine.predictor import predict_score
    result = predict_score(user_features)   # -> ScoreResult(method="ml_pd")

Raw score = 1000 x (1 - PD); a score head (score_head.pkl) maps it onto the rule engine's scale so the ML and
rule-based scores agree to within ~50 points for most users. probability_of_default is always the PD model's own.
Risk bands match backend/scoring_engine/README.md:
Poor <400, Fair 400-599, Good 600-799, Excellent 800+.
`breakdown` is left at zeros: an ML score is not a sum of rule points
(per-feature drivers are in saved_models/model_metadata.json -> "coefficients").
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd

from backend.ml_engine.feature_mapping import MODEL_FEATURES, score_head_matrix, user_features_to_model_row
from common.schemas import ScoreBreakdown, ScoreResult, UserFeatures

MODEL_DIR = Path(__file__).resolve().parent / "saved_models"

try:
    _PREPROCESSOR = joblib.load(MODEL_DIR / "preprocessor.pkl")
    _MODEL = joblib.load(MODEL_DIR / "pd_model.pkl")
    _HEAD = joblib.load(MODEL_DIR / "score_head.pkl") if (MODEL_DIR / "score_head.pkl").exists() else None
except FileNotFoundError as exc:
    raise FileNotFoundError(
        f"PD model files not found in {MODEL_DIR}. "
        "Run: python backend/ml_engine/train_predictor.py") from exc


def _risk_category(score: int) -> str:
    if score >= 800:
        return "Excellent"
    if score >= 600:
        return "Good"
    if score >= 400:
        return "Fair"
    return "Poor"


def predict_score(features: UserFeatures) -> ScoreResult:
    row = pd.DataFrame([user_features_to_model_row(features)], columns=MODEL_FEATURES)
    x = _PREPROCESSOR.transform(row)
    pd_prob = float(_MODEL.predict_proba(x)[0, 1])
    score = 1000 * (1 - pd_prob)
    if _HEAD is not None:
        score = float(_HEAD.predict(score_head_matrix(x, [pd_prob]))[0])
    score = max(0, min(1000, round(score)))
    return ScoreResult(
        user_id=features.user_id,
        total_score=score,
        risk_category=_risk_category(score),
        breakdown=ScoreBreakdown(),
        method="ml_pd",
        probability_of_default=round(pd_prob, 4),
    )


def _mean_coefficients():
    """Average the linear coefficients across the calibration folds."""
    import numpy as np
    coefs = [c.estimator.coef_[0] for c in _MODEL.calibrated_classifiers_]
    return np.mean(coefs, axis=0)


def explain_ml(features: UserFeatures, top_n: int = 6) -> list[dict]:
    """Per-feature drivers of the ML score: coefficient x standardized value.
    Positive log-odds contribution = pushes default risk up (hurts the score)."""
    row = pd.DataFrame([user_features_to_model_row(features)], columns=MODEL_FEATURES)
    x = _PREPROCESSOR.transform(row)
    x = x.toarray()[0] if hasattr(x, "toarray") else x[0]
    contrib = _mean_coefficients() * x
    names = _PREPROCESSOR.get_feature_names_out()
    drivers = []
    for name, c in zip(names, contrib):
        label = name.split("__", 1)[1].replace("_", " ")
        drivers.append({"feature": label, "impact": round(float(c), 3),
                        "direction": "hurts" if c > 0 else "helps"})
    drivers.sort(key=lambda d: abs(d["impact"]), reverse=True)
    return [d for d in drivers if abs(d["impact"]) >= 0.005][:top_n]
