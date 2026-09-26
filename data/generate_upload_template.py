"""
Builds the applicant UPLOAD TEMPLATE in the exact input format of the spec:

  transactions.csv / transactions.json   Transaction ID, Date, Amount, Category, Type (Debit/Credit),
                                         + on_time marker for recurring bills (Rent / Utility / EMI / Insurance)
  demographics.json                      user_id, age, employment_status, education_level, monthly_income,
                                         city_tier, stability markers (months_employed, housing_status,
                                         housing_months) and "new-age" lifestyle fields (credit_util,
                                         delinq_30plus/60plus/90plus, positive_habits, risk_flags,
                                         existing_credit_lines)

The formats/vocabulary follow data/synthetic (transactions.csv, demographics.json) and the lifestyle
field names follow data/Datasets_AltCredit/new_age_sample_data.json. Transactions are generated to be
CONSISTENT with each profile (so the ingestion path recomputes sensible features), unlike the raw
Datasets_AltCredit transactions whose amounts do not reconcile with its pre-computed features.

30 fictional users: 10 in each of tier-1 / tier-2 / tier-3, spread over six credit archetypes so every
risk band (Poor..Excellent) appears in every tier. Deterministic (fixed seed). Run:
    python data/generate_upload_template.py
"""
import csv
import json
import os
import random
from datetime import date

SEED = 2025
MONTHS = 12
START = date(2024, 10, 1)

# name, spend/income, essentials share of spend, bill on-time prob, month-to-month jitter, EMI/income,
# months employed (lo, hi), housing choices, education choices, credit_util, (30d, 60d, 90d), habits, risks
ARCHETYPES = [
    ("excellent",   0.26, 0.74, 0.98, 0.04, 0.10, (24, 48), ["own", "rent"], ["masters", "phd", "bachelor"],
     0.08, (0, 0, 0), 2, 0),
    ("strong",      0.55, 0.56, 0.90, 0.11, 0.24, (8, 20), ["rent"], ["certification", "high_school"],
     0.34, (1, 0, 0), 1, 0),
    ("steady",      0.60, 0.50, 0.87, 0.14, 0.30, (6, 14), ["rent"], ["certification", "high_school"],
     0.42, (1, 0, 0), 1, 0),
    ("stretched",   0.66, 0.46, 0.84, 0.16, 0.34, (4, 12), ["rent"], ["high_school", "certification"],
     0.52, (1, 0, 0), 0, 1),
    ("new_to_credit", 0.45, 0.68, 0.96, 0.08, 0.05, (3, 10), ["rent", "none"], ["bachelor", "high_school"],
     0.0, (0, 0, 0), 1, 0),
    ("high_risk",   0.82, 0.35, 0.60, 0.28, 0.45, (0, 8), ["rent", "none"], ["high_school", "none"],
     0.85, (2, 1, 1), 0, 3),
]
ARCH = {a[0]: a for a in ARCHETYPES}
MIX = ["excellent", "strong", "strong", "steady", "steady", "stretched", "stretched", "new_to_credit",
       "high_risk", "high_risk"]
EMPLOYMENT = {"excellent": "full-time", "strong": "full-time", "steady": "full-time",
              "stretched": "part-time", "new_to_credit": "gig-platform", "high_risk": "freelance"}
TIER_INCOME = {"tier-1": (60000, 140000), "tier-2": (40000, 90000), "tier-3": (25000, 60000)}


ARCH_OF = {}   # user_id -> archetype name (generator diagnostics only; NOT written to the upload files)


def _split(rng, total, n):
    weights = [rng.uniform(0.5, 1.5) for _ in range(n)]
    s = sum(weights)
    return [round(total * w / s, 2) for w in weights]


def build(seed=SEED):
    rng = random.Random(seed)
    demographics, txns = [], []
    tid = 1

    def add(user, month, day, amount, category, typ, on_time=None):
        nonlocal tid
        y, m = divmod(START.month - 1 + month, 12)
        d = date(START.year + y, m + 1, min(day, 28))
        txns.append({"transaction_id": f"TXN{tid:06d}", "user_id": user, "date": d.isoformat(),
                     "amount": round(amount, 2), "category": category, "type": typ, "on_time": on_time})
        tid += 1

    uid = 0
    for tier in ("tier-1", "tier-2", "tier-3"):
        # fixed mix per tier (10 users) so every risk band shows up in every tier
        plan = [ARCH[n] for n in MIX]
        rng.shuffle(plan)
        for arch in plan:
            (name, spend_ratio, ess_share, on_time_p, jitter, emi_ratio, tenure, housing_ch, edu_ch,
             util, (d30, d60, d90), habits, risks) = arch
            uid += 1
            user = f"UPL_{uid:03d}"
            ARCH_OF[user] = name
            income = round(rng.uniform(*TIER_INCOME[tier]) * (1.15 if name in ("excellent", "strong") else 1.0), 2)
            housing = rng.choice(housing_ch)
            demographics.append({
                "user_id": user,
                "age": rng.randint(23, 58),
                "employment_status": EMPLOYMENT[name],
                "education_level": rng.choice(edu_ch),
                "monthly_income": income,
                "city_tier": tier,
                "months_employed": rng.randint(*tenure),
                "housing_status": housing,
                "housing_months": rng.randint(12, 60) if housing == "own" else (rng.randint(6, 40) if housing == "rent" else 0),
                "existing_credit_lines": 0 if name == "new_to_credit" else rng.randint(1, 3),
                "credit_util": round(util, 2),
                "delinq_30plus": d30, "delinq_60plus": d60, "delinq_90plus": d90,
                "positive_habits": habits, "risk_flags": risks,
            })

            for m in range(MONTHS):
                add(user, m, rng.randint(1, 3), income, "Salary", "Credit")
                month_spend = income * spend_ratio * rng.uniform(1 - jitter, 1 + jitter)
                essentials = month_spend * ess_share
                emi = income * emi_ratio if emi_ratio > 0.06 else 0.0
                emi = min(emi, essentials * 0.6)
                rest = essentials - emi
                if housing == "rent":
                    rent = rest * 0.45
                    add(user, m, rng.randint(1, 5), rent, "Rent", "Debit", rng.random() < on_time_p)
                    rest -= rent
                if emi:
                    add(user, m, rng.randint(5, 12), emi, "EMI", "Debit", rng.random() < on_time_p)
                util_amt = rest * 0.25                          # electricity + internet
                for amt in _split(rng, util_amt, 2):
                    add(user, m, rng.randint(8, 24), amt, "Utility", "Debit", rng.random() < on_time_p)
                for amt in _split(rng, rest - util_amt, 3):
                    add(user, m, rng.randint(1, 28), amt, "Food", "Debit")
                for amt in _split(rng, month_spend - essentials, rng.randint(2, 4)):
                    add(user, m, rng.randint(1, 28), amt, rng.choice(["Discretionary", "Transport"]), "Debit")

    return demographics, txns


def write(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    demographics, txns = build()
    with open(os.path.join(out_dir, "demographics.json"), "w", encoding="utf-8") as f:
        json.dump(demographics, f, indent=2)
    fields = ["transaction_id", "user_id", "date", "amount", "category", "type", "on_time"]
    with open(os.path.join(out_dir, "transactions.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({**t, "on_time": "" if t["on_time"] is None else str(t["on_time"])} for t in txns)
    with open(os.path.join(out_dir, "transactions.json"), "w", encoding="utf-8") as f:
        json.dump(txns, f, indent=1)
    print(f"Wrote {len(demographics)} users, {len(txns)} transactions to {out_dir}")


if __name__ == "__main__":
    write(os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_template"))
