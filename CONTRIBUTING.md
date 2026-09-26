# CONTRIBUTING — Git Workflow & Merge-Conflict Prevention

Read this once as a team before anyone starts coding (10 minutes, saves hours later).

## 1. Folder ownership — one person/pair per folder, no overlap
| Folder | Owner (assign a name) | Depends on |
|---|---|---|
| `data/` | ___ | `common/` |
| `backend/scoring_engine/` | ___ | `common/`, `data/` output |
| `backend/ml_engine/` (stretch) | ___ | `common/`, `data/` output |
| `backend/explainability/` | ___ | `common/`, `scoring_engine/` output |
| `backend/recommendations/` | ___ | `common/`, `scoring_engine/` output |
| `backend/reports/` | ___ | `common/`, `explainability/` output |
| `backend/bank_integration_mock/` (stretch) | ___ | `common/` |
| `backend/testing/` | ___ | everything above (writes tests against contracts) |
| `backend/api/` | ___ | imports every backend module |
| `database/` | ___ | `common/` |
| `frontend/user-dashboard/` | ___ | `backend/api/` endpoints |
| `frontend/lender-portal/` | ___ | `backend/api/` endpoints |
| `deployment/` | whoever finishes first | everything |

**Because folders don't overlap, two people editing at once almost never touch the same file.**
The only shared files are `common/schemas.py` and `backend/api/main.py` — treat those two as
"ask before editing something someone else just touched."

## 2. Branch naming
```
feature/<folder-name>-<short-description>
# e.g. feature/scoring-engine-point-table
# e.g. feature/api-lender-endpoints
```
Never commit directly to `main`. Always open a PR, even a 1-line one — it's a 30-second review
and it catches accidental schema drift before it merges.

## 3. Commit messages
```
<folder>: <what changed>
# e.g. "scoring_engine: implement all 12 sub-factor functions"
# e.g. "common: add positive_habits_count to UserFeatures"
```

## 4. The merge-conflict-prevention checklist (before opening a PR)
- [ ] Did I only touch files inside my owned folder (+ maybe `common/schemas.py`)?
- [ ] If I touched `common/schemas.py`, did I only **add** fields, never rename/remove ones
      someone else already depends on?
- [ ] Does my module's public function signature match exactly what my README's "Handoff"
      section promises?
- [ ] Did I run my own module's tests (if any) before pushing?

## 5. Integration cadence
Don't wait until the last day to wire everything together. Pick 2 checkpoints:
- **Midpoint check-in**: everyone pushes a working stub (even hardcoded return values that
  match the `common/schemas.py` shape) — `backend/api/` owner wires up the full flow once, so
  you catch integration mismatches early.
- **Final integration**: swap the stubs for real implementations one module at a time, re-test
  after each swap.

## 6. Code style (keep it loose, just be consistent)
- Python: `snake_case` for functions/variables, run `black .` before committing if you have time
- React: functional components, one component per file, `PascalCase` filenames
- Always type-hint Python function signatures with the `common/schemas.py` classes — it's free
  documentation and catches mismatches before runtime

## 7. Environment / secrets
- Never commit `.env` or API keys (see `.gitignore` — already excludes these)
- If you use any third-party API key anywhere (e.g. payment gateway, notification service), put
  it in `.env`
  and load with `os.getenv("API_KEY")` — never hardcode it in a `.py` file
