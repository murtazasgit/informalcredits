# Bank Partner API (mock)

Separate FastAPI service the AltCredit backend calls to pre-approve a recommended product.

    uvicorn app:app --app-dir bank-partner-api --port 8100     # run from repo root
    export BANK_API_KEY=...                                     # default: dev-bank-key (mock)

| Endpoint | Purpose |
|---|---|
| `POST /preapprove` | `{applicant_ref, score, risk_category, product_id, product_name, min_score_required, interest_rate}` → decision (`pre_approved` / `manual_review` / `declined`), limit, APR |
| `GET /offer-status/{application_id}` | Status of a previous pre-approval |

All endpoints except `GET /` require an `X-API-Key` header. The credit app reads `BANK_API_URL` and
`BANK_API_KEY` from its environment (`backend/integrations/bank_client.py`). No PII is sent — only an
opaque applicant reference and the score. Decision logic is a mock: margin over the product minimum.
