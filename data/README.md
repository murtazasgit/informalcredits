# Module: Data Ingestion & Synthetic Data

## Goal
Read, validate, and clean the three input data types. Turn raw CSV/JSON into engineered features
that the scoring engine can consume.

## Tech stack
- **pandas** — CSV/tabular processing
- **pydantic** — JSON schema validation for demographic/product data
- **Faker** (optional) — generate realistic synthetic data if the real dataset isn't ready yet

## Inputs (exact formats you must support)

### 1. Transactional Data (CSV or JSON)
| Field | Type | Example |
|---|---|---|
| transaction_id | string | "TXN00123" |
| user_id | string | "U1001" |
| date | date (YYYY-MM-DD) | "2026-03-15" |
| amount | float | 1450.00 |
| category | enum | Rent, Utility, Salary, Food, Discretionary, etc. |
| type | enum | Debit / Credit |
| on_time | bool (for recurring bills) | true/false |

### 2. Demographic Data (JSON)
```json
{
  "user_id": "U1001",
  "age": 27,
  "employment_status": "gig-platform",
  "months_employed": 18,
  "education_level": "bachelor",
  "monthly_income": 35000,
  "city_tier": "tier-1",
  "housing_status": "rent",
  "housing_months": 14,
  "existing_credit_lines": 0
}
```

### 3. Product Catalog (JSON)
```json
{
  "product_id": "P001",
  "name": "Starter Credit Card",
  "type": "Starter Card",
  "min_score_required": 550,
  "interest_rate": 24.0
}
```

## Output (what you hand to the scoring engine)
A single per-user **feature dict** — this is the contract with `backend/scoring_engine/`:
```json
{
  "user_id": "U1001",
  "months_employed": 18,
  "housing_status": "rent",
  "housing_months": 14,
  "digital_bill_ontime_pct": 92.0,
  "education_level": "bachelor",
  "spend_to_income_ratio": 0.42,
  "essential_spend_pct": 68.0,
  "cashflow_volatility_pct": 7.5,
  "savings_days": 45,
  "on_time_payment_pct": 96.0,
  "debt_to_income_ratio": 0.18,
  "credit_utilization_pct": 0,
  "delinquency_flags": []
}
```

## Tasks checklist
- [ ] Write pydantic models for demographic + product catalog JSON
- [ ] Write pandas loader for transaction CSV, with dtype validation
- [ ] Feature engineering functions: spend-to-income ratio, essential-spend %, cash-flow std-dev,
      savings days, on-time payment %, debt-to-income
- [ ] Handle missing data gracefully (e.g., no utility history → default to 0, don't crash)
- [ ] Synthetic data generator script (`generate_synthetic_data.py`) so other teams aren't blocked

## Starter code
```python
# schemas.py
from pydantic import BaseModel
from typing import Optional

class Demographic(BaseModel):
    user_id: str
    age: int
    employment_status: str
    months_employed: int
    education_level: str
    monthly_income: float
    city_tier: str
    housing_status: str
    housing_months: int
    existing_credit_lines: int = 0

# feature_engineering.py
import pandas as pd

def spend_to_income_ratio(transactions: pd.DataFrame, monthly_income: float) -> float:
    monthly_spend = transactions[transactions["type"] == "Debit"]["amount"].sum() / \
                    transactions["date"].dt.to_period("M").nunique()
    return round(monthly_spend / monthly_income, 2) if monthly_income else 0.0

def essential_spend_pct(transactions: pd.DataFrame) -> float:
    essential_categories = ["Rent", "Utility", "Food"]
    total = transactions[transactions["type"] == "Debit"]["amount"].sum()
    essential = transactions[transactions["category"].isin(essential_categories)]["amount"].sum()
    return round(100 * essential / total, 1) if total else 0.0
```

## Handoff
Push your output as a JSON file or a function `get_user_features(user_id) -> dict` that
`backend/scoring_engine/` imports directly. ML scoring is not part of the current MVP.

## OCR Integration (stretch — "Good to Have")

### Goal
Allow a user to upload a scanned/PDF bank statement instead of a clean CSV, and extract
transaction lines automatically.

### Tech stack
**Tesseract** via `pytesseract` + `pdf2image` (converts PDF pages to images for OCR).

### Input
A PDF bank statement (uploaded via the frontend onboarding page — see
`frontend/user-dashboard/README.md` §Onboarding).

### Output
A list of `Transaction` objects (same shape as CSV ingestion — feeds the same pipeline).

### Starter code
```python
import pytesseract
from pdf2image import convert_from_path
import re

def ocr_bank_statement(pdf_path: str) -> list[dict]:
    pages = convert_from_path(pdf_path)
    transactions = []
    for page in pages:
        text = pytesseract.image_to_string(page)
        # crude line pattern: DATE  DESCRIPTION  AMOUNT  DEBIT/CREDIT
        for line in text.splitlines():
            match = re.match(r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(DR|CR)", line)
            if match:
                date, desc, amount, dc = match.groups()
                transactions.append({
                    "date": date, "category": guess_category(desc),
                    "amount": float(amount.replace(",", "")),
                    "type": "Debit" if dc == "DR" else "Credit"
                })
    return transactions
```
Keep the regex simple and tune it against your synthetic sample statements — this is a stretch
feature, not worth over-engineering. If OCR extraction quality is poor, fall back to letting
the user paste/upload a CSV instead (already required as the must-have path).

### Tasks checklist
- [ ] Install `tesseract-ocr` in the backend Docker image (`apt-get install tesseract-ocr`)
- [ ] Implement `ocr_bank_statement(pdf_path) -> list[dict]`
- [ ] Wire into the `/transactions/upload` endpoint as an alternate path when file is PDF
