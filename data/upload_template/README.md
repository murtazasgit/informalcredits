# Upload template

Sample applicant data in the spec's input format, for `POST /upload-raw` (or the "Upload raw applicant
data" panel in the dashboard).

| File | Contents |
|---|---|
| `transactions.csv` / `transactions.json` | Same 3,859 rows in two formats: `transaction_id, user_id, date, amount, category (Rent/Utility/Salary/Food/…), type (Debit/Credit), on_time` — `on_time` marks timely payment of recurring bills (Rent, Utility = electricity/internet, EMI) |
| `demographics.json` | `user_id, age, employment_status, education_level, monthly_income, city_tier` + stability markers `months_employed, housing_status, housing_months` + lifestyle fields `credit_util, delinq_30plus/60plus/90plus, positive_habits, risk_flags, existing_credit_lines` |

30 fictional applicants: 10 per tier (tier-1 / tier-2 / tier-3), each tier containing 4 Good, 2 Excellent,
2 Fair and 2 Poor profiles. Spending, essentials share, volatility, savings, bill timeliness and debt load
are *derived from the transactions*; the lifestyle fields are what a statement cannot show.
Vocabulary follows `data/synthetic/`; lifestyle field names follow `Datasets_AltCredit/new_age_sample_data.json`.
Regenerate (deterministic): `python data/generate_upload_template.py`.
