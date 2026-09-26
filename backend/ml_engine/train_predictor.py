"""
train_predictor.py - Case 1: Probability of Default (PD) model.

Run from the repo root:  python backend/ml_engine/train_predictor.py

Model: Logistic Regression (class_weight="balanced") wrapped in sigmoid calibration.
 - Logistic Regression: interpretable (one weight per feature), follows the no-black-box guardrail.
 - class_weight="balanced": ~21% defaults, so the model is pushed to learn the minority class.
 - Calibration: "balanced" inflates probabilities (average PD ends up near 50%), which would
   drag every score down. Sigmoid calibration maps them back to real default rates, so a
   predicted 10% PD means ~10% actual defaults.
Score = 1000 x (1 - PD).  Labels in ground_truth.csv are simulated (no real outcome data exists).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.ml_engine.feature_mapping import (CATEGORICAL_FEATURES, MODEL_FEATURES, NUMERIC_FEATURES,
                                               raw_to_user_features, user_features_to_model_row)

DATA_DIR = ROOT / "data"
MODEL_DIR = Path(__file__).resolve().parent / "saved_models"
RANDOM_STATE = 42


def load_training_data():
    raw = json.loads((DATA_DIR / "merged_data.json").read_text(encoding="utf-8"))
    labels = pd.read_csv(DATA_DIR / "ground_truth.csv")
    label_map = dict(zip(labels["user_id"], labels["defaulted"]))

    rows, y = [], []
    for record in raw:
        if record.get("user_id") not in label_map:
            continue  # user without a label can't be used for training
        rows.append(user_features_to_model_row(raw_to_user_features(record)))
        y.append(int(label_map[record["user_id"]]))
    print(f"Loaded {len(rows)} labelled users ({sum(y)} defaults, {np.mean(y):.1%} default rate)")
    return pd.DataFrame(rows, columns=MODEL_FEATURES), np.array(y)


def main():
    X, y = load_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    Xtr = preprocessor.fit_transform(X_train)
    Xte = preprocessor.transform(X_test)

    # 1) plain balanced LR (used for coefficients / comparison)
    plain = LogisticRegression(class_weight="balanced", max_iter=1000)
    plain.fit(Xtr, y_train)
    p_plain = plain.predict_proba(Xte)[:, 1]

    # 2) calibrated LR (the model we save)
    model = CalibratedClassifierCV(LogisticRegression(class_weight="balanced", max_iter=1000),
                                   method="sigmoid", cv=5)
    model.fit(Xtr, y_train)
    p_test = model.predict_proba(Xte)[:, 1]

    auc = roc_auc_score(y_test, p_test)
    brier = brier_score_loss(y_test, p_test)
    print("\n=== Test-set results (20% hold-out) ===")
    print(f"{'':22}{'AUC':>8}{'Brier':>9}{'Avg PD':>9}")
    print(f"{'Uncalibrated LR':22}{roc_auc_score(y_test, p_plain):8.3f}"
          f"{brier_score_loss(y_test, p_plain):9.3f}{p_plain.mean():9.1%}")
    print(f"{'Calibrated LR (saved)':22}{auc:8.3f}{brier:9.3f}{p_test.mean():9.1%}")
    print(f"Actual default rate in test set: {y_test.mean():.1%}")

    frac_pos, mean_pred = calibration_curve(y_test, p_test, n_bins=5, strategy="quantile")
    print("\n=== Calibration (predicted PD vs actual default rate) ===")
    for pred, actual in zip(mean_pred, frac_pos):
        print(f"  predicted {pred:6.1%}  ->  actual {actual:6.1%}")

    names = preprocessor.get_feature_names_out()
    coefs = sorted(zip(names, plain.coef_[0]), key=lambda t: abs(t[1]), reverse=True)
    print("\n=== Top drivers (+ raises default risk, - lowers it) ===")
    for name, c in coefs[:8]:
        print(f"  {name:40} {c:+.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, MODEL_DIR / "preprocessor.pkl")
    joblib.dump(model, MODEL_DIR / "pd_model.pkl")
    (MODEL_DIR / "model_metadata.json").write_text(json.dumps({
        "model": "CalibratedClassifierCV(LogisticRegression(class_weight='balanced'), sigmoid, cv=5)",
        "features": MODEL_FEATURES,
        "test_auc": round(auc, 4),
        "test_brier": round(brier, 4),
        "train_rows": int(len(y_train)), "test_rows": int(len(y_test)),
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "coefficients": {n: round(float(c), 4) for n, c in coefs},
    }, indent=2))
    print(f"\nSaved preprocessor.pkl, pd_model.pkl, model_metadata.json to {MODEL_DIR}")


if __name__ == "__main__":
    main()
