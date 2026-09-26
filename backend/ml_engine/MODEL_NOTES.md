# Case 1 — Probability of Default (PD) model

**Files:** `feature_mapping.py` (raw data → `UserFeatures`), `train_predictor.py` (training),
`predictor.py` (`predict_score(features: UserFeatures) -> ScoreResult`), `check_predictor.py` (smoke test).

## Feature mapping
`merged_data.json` uses different names and units from `common/schemas.py`. `raw_to_user_features()`
converts them (full table in the `feature_mapping.py` docstring). Key conversions:
- Rates stored as 0–1 (`on_time_rate`, `essential_pct`, `credit_util`, …) → `*_pct` fields on a 0–100 scale,
  matching `data/README.md`
- `months_at_job` → `months_employed`, `rent_on_time_months` → `housing_months`
- `housing`: owner → own; `education`: master → masters, cert → certification, highschool → high_school
- `spend_to_income_ratio` = monthly_spend / monthly_income
- `delinq_30plus/60plus/90plus` counts → `delinquency_flags` list, e.g. `["30-day-miss"]`

The model only uses fields that exist in `UserFeatures`, so inference needs nothing else.

## Model choice
Logistic Regression with `class_weight="balanced"`, wrapped in `CalibratedClassifierCV(method="sigmoid")`.
- **Interpretable:** one weight per feature (saved in `saved_models/model_metadata.json`), which respects the no-black-box guardrail.
- **Imbalance:** about 21% of users defaulted; balanced class weights stop the model from ignoring them.
- **Calibration:** balanced weights inflate the average PD to ~45%, which would unfairly lower every score. Sigmoid calibration brings it back to ~25% (actual rate is 21%), and the Brier score improves from 0.203 to 0.132.

## Results (20% stratified hold-out, random_state=42)
- **Test AUC: 0.797**
- Strongest risk drivers: debt-to-income (↑ risk), on-time payment % (↓ risk), risk flags (↑), cash-flow volatility (↑)

## Notes
- `ground_truth.csv` is a **simulated** label, since no real historical outcome data exists for this dataset.
- Only about 6 users have 90-day misses, so that coefficient is noisy.
- `breakdown` in `ScoreResult` is left at zeros, because an ML score is not a sum of rule points.
- Risk bands match the rule engine: Poor < 400, Fair 400–599, Good 600–799, Excellent 800+.
