"""
train_score_head.py - align the ML score with the rule engine's 0-1000 scale.

Run from the repo root (after train_predictor.py has produced the PD model):
    python backend/ml_engine/train_score_head.py

The PD model gives 1000 x (1 - PD), which runs ~100 points above the rule-based score on average. This trains a small
second stage (Huber gradient boosting on the same features + the PD score) whose target is the rule engine's score.
It needs no default labels, only the saved PD model and the dataset. Saved to saved_models/score_head.pkl; the
predictor uses it automatically, and probability_of_default is still the PD model's own output.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_predict

from backend.api.main import _get_data_dir
from backend.ml_engine.feature_mapping import MODEL_FEATURES, score_head_matrix, user_features_to_model_row
from backend.scoring_engine.engine import compute_score
from data.feature_engineering import get_all_user_features

MODEL_DIR = Path(__file__).resolve().parent / "saved_models"
RANDOM_STATE = 42


def new_head():
    return GradientBoostingRegressor(loss="huber", n_estimators=800, max_depth=3, learning_rate=0.05,
                                     subsample=0.8, random_state=RANDOM_STATE)


def main():
    preprocessor = joblib.load(MODEL_DIR / "preprocessor.pkl")
    pd_model = joblib.load(MODEL_DIR / "pd_model.pkl")

    users = list(get_all_user_features(_get_data_dir()).values())
    X = pd.DataFrame([user_features_to_model_row(u) for u in users], columns=MODEL_FEATURES)
    rule = np.array([compute_score(u).total_score for u in users])
    xt = preprocessor.transform(X)
    pd_prob = pd_model.predict_proba(xt)[:, 1]
    Z = score_head_matrix(xt, pd_prob)

    raw_gap = np.abs(1000 * (1 - pd_prob) - rule)
    aligned = np.clip(cross_val_predict(new_head(), Z, rule, cv=KFold(5, shuffle=True, random_state=RANDOM_STATE)), 0, 1000)
    gap = np.abs(aligned - rule)
    print(f"{len(users)} users")
    print(f"raw 1000x(1-PD):  mean gap {raw_gap.mean():5.1f}, within 50 points of rule score: {(raw_gap <= 50).mean():.0%}")
    print(f"with score head:  mean gap {gap.mean():5.1f}, within 50 points of rule score: {(gap <= 50).mean():.0%}  (5-fold out-of-sample)")

    joblib.dump(new_head().fit(Z, rule), MODEL_DIR / "score_head.pkl")

    meta_path = MODEL_DIR / "model_metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["score_head"] = {"model": "GradientBoostingRegressor(huber)", "target": "rule-based score",
                          "cv_mean_gap": round(float(gap.mean()), 1),
                          "cv_within_50": round(float((gap <= 50).mean()), 3)}
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"Saved {MODEL_DIR / 'score_head.pkl'}")


if __name__ == "__main__":
    main()
