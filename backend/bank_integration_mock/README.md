# Module: Mock Bank Integration (stretch — "Good to Have")

## Why this exists
The spec says: *"the system connects to the banking system via an API for the user to avail
the pre-approved loans/credit cards... you are expected to create another application and link
both the bank and Credit application via an API key."*

This means judges expect **two separate small services**, talking to each other via an API key —
not just one endpoint inside `backend/api/`. This module is that second service.

## Tech stack
A second, tiny **FastAPI** app (separate process/port) — reuse the same skills as the main API,
just a smaller surface area. Keep it dead simple; it's a mock, not a real bank integration.

## What it does
Simulates a bank's loan/card disbursal system. AltCredit's main API calls it (with an API key)
when a user clicks "accept offer" on a pre-approved product.

## Input (call from `backend/api/` → this mock bank service)
```
POST /bank/disburse
Headers: X-API-Key: <shared secret, from .env, never hardcoded>
Body:
{
  "user_id": "U1001",
  "product_id": "P001",
  "product_type": "Microloan",
  "amount_requested": 15000
}
```

## Output
```json
{
  "approval_status": "approved",
  "bank_reference_id": "BANKREF-88213",
  "disbursal_eta_days": 2
}
```

## Starter code
```python
# bank_mock/main.py
from fastapi import FastAPI, Header, HTTPException
import os, random, string

app = FastAPI(title="Mock Bank Service")
API_KEY = os.getenv("BANK_API_KEY", "dev-shared-secret")

@app.post("/bank/disburse")
def disburse(payload: dict, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    ref = "BANKREF-" + "".join(random.choices(string.digits, k=5))
    return {"approval_status": "approved", "bank_reference_id": ref, "disbursal_eta_days": 2}
```

```python
# in backend/api/ — calling the mock bank
import requests, os

def request_disbursal(user_id, product_id, product_type, amount):
    resp = requests.post(
        "http://bank_mock:9000/bank/disburse",
        headers={"X-API-Key": os.getenv("BANK_API_KEY")},
        json={"user_id": user_id, "product_id": product_id,
              "product_type": product_type, "amount_requested": amount}
    )
    return resp.json()
```

## Tasks checklist
- [ ] Build the mock bank FastAPI app (`bank_mock/main.py`) with `/bank/disburse`
- [ ] Add a `.env` entry `BANK_API_KEY=<random-string>` (never commit the real value)
- [ ] Add this service to `docker-compose.yml` as its own container (see `deployment/README.md`)
- [ ] Wire `backend/api/` to call it when a user accepts an offer
- [ ] Store `bank_reference_id` back in the `offers` table

## Priority
This is a **stretch goal** — build it only after all must-have flows work end-to-end. A single
mocked endpoint is enough to satisfy the requirement; don't over-engineer it.

## Handoff
Expose `POST /bank/disburse` for `backend/api/` to call.
