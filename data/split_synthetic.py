"""
Splits the combined synthetic dataset (data/synthetic/demographics.json + transactions.csv) into one
folder per user, grouped by credit category:

    data/synthetic/<category>/user_<n>/
        demographics.json     this user's profile (a one-element list, so it uploads as-is)
        transactions.csv      this user's own bank transactions
        expected_score.json   rule-engine score, risk category, 14-factor breakdown and engineered features

Category = the rule-based engine's risk band for that user (poor / fair / good / excellent); only
categories that actually contain users get a folder. `user_<n>` is numbered within the category in
user_id order. Each user folder can be uploaded directly to POST /upload-raw.

The combined files stay in place (the API's fallback data source); this script only reads them.
Deterministic: re-running rewrites identical files.   python data/split_synthetic.py
"""
import csv
import json
import os
import shutil
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from backend.scoring_engine.engine import compute_score          # noqa: E402
from data.feature_engineering import get_all_user_features        # noqa: E402

SYNTHETIC = os.path.join(ROOT, "data", "synthetic")
TX_FIELDS = ["transaction_id", "user_id", "date", "amount", "category", "type", "on_time"]
CATEGORIES = ("poor", "fair", "good", "excellent")


def split(src_dir: str = SYNTHETIC) -> dict[str, list[str]]:
    with open(os.path.join(src_dir, "demographics.json"), encoding="utf-8") as f:
        demographics = {d["user_id"]: d for d in json.load(f)}
    with open(os.path.join(src_dir, "transactions.csv"), newline="", encoding="utf-8") as f:
        raw_tx = defaultdict(list)
        for row in csv.DictReader(f):
            raw_tx[row["user_id"]].append(row)
    features = get_all_user_features(src_dir)

    for category in CATEGORIES:                        # clear old output so reruns never leave stale users
        shutil.rmtree(os.path.join(src_dir, category), ignore_errors=True)

    by_category = defaultdict(list)
    for user_id in sorted(demographics):
        by_category[compute_score(features[user_id]).risk_category.lower()].append(user_id)

    layout = {}
    for category, users in by_category.items():
        layout[category] = []
        for n, user_id in enumerate(users, start=1):
            folder = os.path.join(src_dir, category, f"user_{n}")
            os.makedirs(folder)
            result = compute_score(features[user_id])
            with open(os.path.join(folder, "demographics.json"), "w", encoding="utf-8") as f:
                json.dump([demographics[user_id]], f, indent=2)
            with open(os.path.join(folder, "transactions.csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=TX_FIELDS)
                writer.writeheader()
                writer.writerows(raw_tx[user_id])
            with open(os.path.join(folder, "expected_score.json"), "w", encoding="utf-8") as f:
                json.dump({"user_id": user_id, "total_score": result.total_score,
                           "risk_category": result.risk_category, "breakdown": result.breakdown.model_dump(),
                           "features": features[user_id].model_dump()}, f, indent=2)
            layout[category].append(f"user_{n} = {user_id} ({result.total_score})")
    return layout


def load_split_dataset(src_dir: str = SYNTHETIC) -> tuple[list[dict], list[dict]]:
    """Read every user folder back into (demographics list, normalised transactions list)."""
    from data.feature_engineering import load_transactions
    demographics, transactions = [], []
    for category in CATEGORIES:
        base = os.path.join(src_dir, category)
        if not os.path.isdir(base):
            continue
        for user_dir in sorted(os.listdir(base), key=lambda n: int(n.split("_")[1])):
            with open(os.path.join(base, user_dir, "demographics.json"), encoding="utf-8") as f:
                demographics.extend(json.load(f))
            transactions.extend(load_transactions(os.path.join(base, user_dir, "transactions.csv")))
    return demographics, transactions


if __name__ == "__main__":
    for category, users in split().items():
        print(f"{category}: {len(users)} users")
        for line in users:
            print("   ", line)
