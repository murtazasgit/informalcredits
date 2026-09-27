"""
train_challengers.py - Random Forest and XGBoost PD models, benchmarked against the production Logistic Regression.

Run from the repo root (after train_predictor.py):  python backend/ml_engine/train_challengers.py

Uses the same data, split, and preprocessor as train_predictor.py so AUC / Brier are directly comparable.
Both tree models are sigmoid-calibrated (cv=5) like the LR, so their PDs are real default rates.
Saves saved_models/rf_model.pkl and xgb_model.pkl and records the comparison in model_metadata.json under
"challengers". The production model stays the LR: it is the one that gives per-feature coefficients for explanations.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from backend.ml_engine.train_predictor import MODEL_DIR, RANDOM_STATE, load_training_data


def _candidates(scale_pos_weight: float) -> dict:
    return {
        "random_forest": RandomForestClassifier(
            n_estimators=400, max_depth=6, min_samples_leaf=5, class_weight="balanced",
            n_jobs=-1, random_state=RANDOM_STATE),
        "xgboost": XGBClassifier(
            n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight, eval_metric="logloss", random_state=RANDOM_STATE, n_jobs=1),
    }


def main():
    X, y = load_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)

    # Reuse the LR's fitted preprocessor so all three models see identical inputs.
    preprocessor = joblib.load(MODEL_DIR / "preprocessor.pkl")
    Xtr, Xte = preprocessor.transform(X_train), preprocessor.transform(X_test)

    lr = joblib.load(MODEL_DIR / "pd_model.pkl")
    results = {"logistic_regression (production)": _score(lr, Xte, y_test)}

    spw = float((y_train == 0).sum() / (y_train == 1).sum())
    for name, est in _candidates(spw).items():
        model = CalibratedClassifierCV(est, method="sigmoid", cv=5)
        model.fit(Xtr, y_train)
        joblib.dump(model, MODEL_DIR / ("rf_model.pkl" if name == "random_forest" else "xgb_model.pkl"))
        results[name] = _score(model, Xte, y_test)

    print("\n=== Test-set comparison (20% hold-out) ===")
    print(f"{'model':34}{'AUC':>8}{'Brier':>9}{'Avg PD':>9}")
    for name, r in results.items():
        print(f"{name:34}{r['test_auc']:8.3f}{r['test_brier']:9.3f}{r['avg_pd']:9.1%}")
    print(f"Actual default rate in test set: {y_test.mean():.1%}")

    meta_path = MODEL_DIR / "model_metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["challengers"] = results
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"\nSaved rf_model.pkl, xgb_model.pkl and updated model_metadata.json in {MODEL_DIR}")


def _score(model, X, y) -> dict:
    p = model.predict_proba(X)[:, 1]
    return {"test_auc": round(float(roc_auc_score(y, p)), 4),
            "test_brier": round(float(brier_score_loss(y, p)), 4),
            "avg_pd": round(float(p.mean()), 4)}


if __name__ == "__main__":
    main()
