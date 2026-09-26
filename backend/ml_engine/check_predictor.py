"""Quick end-to-end check. Run from repo root: python backend/ml_engine/check_predictor.py"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.ml_engine.feature_mapping import raw_to_user_features
from backend.ml_engine.predictor import predict_score
from common.schemas import ScoreResult, UserFeatures

raw = json.loads((ROOT / "data" / "merged_data.json").read_text(encoding="utf-8"))

# 1. Normal user
features = raw_to_user_features(raw[0])
start = time.perf_counter()
result = predict_score(features)
ms = (time.perf_counter() - start) * 1000
print(result.model_dump_json(indent=2) if hasattr(result, "model_dump_json") else result.json(indent=2))
assert isinstance(result, ScoreResult) and result.method == "ml_pd"
assert 0 <= result.total_score <= 1000
assert 0 <= result.probability_of_default <= 1
print(f"PASS normal user ({ms:.1f} ms)")

# 2. Thin-file user: optional fields left at schema defaults, unseen category
thin = UserFeatures(user_id="NEW_USER", months_employed=3, housing_status="unknown", housing_months=0,
                    digital_bill_ontime_pct=0, education_level="diploma", spend_to_income_ratio=0.5,
                    essential_spend_pct=50, cashflow_volatility_pct=10, savings_days=0,
                    on_time_payment_pct=0, debt_to_income_ratio=0)
r = predict_score(thin)
assert 0 <= r.total_score <= 1000
print(f"PASS thin-file user -> score {r.total_score}, PD {r.probability_of_default}")

# 3. Score all users
scores = [predict_score(raw_to_user_features(u)).total_score for u in raw]
print(f"PASS all {len(scores)} users scored, range {min(scores)}-{max(scores)}")
