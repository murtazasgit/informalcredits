"""
Synthetic data generator — creates realistic fake users, transactions, and product catalog
so the entire pipeline can be tested end-to-end without any real data.
"""

import json
import csv
import random
import os
from datetime import date, timedelta


def generate_synthetic_data(output_dir: str, num_users: int = 20):
    """Generate synthetic demographics, transactions, and product catalog."""
    os.makedirs(output_dir, exist_ok=True)

    # --- Demographics ---
    demographics = []
    for i in range(1, num_users + 1):
        user_id = f"U{1000 + i}"
        demo = {
            "user_id": user_id,
            "age": random.randint(21, 55),
            "employment_status": random.choice(["full-time", "part-time", "gig-platform", "freelance", "self-employed"]),
            "months_employed": random.randint(0, 60),
            "education_level": random.choice(["high_school", "bachelor", "masters", "phd", "certification"]),
            "monthly_income": round(random.uniform(15000, 150000), 2),
            "city_tier": random.choice(["tier-1", "tier-2", "tier-3"]),
            "housing_status": random.choice(["own", "rent", "none"]),
            "housing_months": random.randint(0, 60),
            "existing_credit_lines": random.randint(0, 3),
        }
        demographics.append(demo)

    with open(os.path.join(output_dir, "demographics.json"), "w") as f:
        json.dump(demographics, f, indent=2)

    # --- Transactions ---
    categories = ["Rent", "Utility", "Salary", "Food", "Discretionary", "Transport", "Insurance", "EMI"]
    transactions = []
    txn_id = 1

    for demo in demographics:
        user_id = demo["user_id"]
        monthly_income = demo["monthly_income"]

        # Generate 6 months of transactions
        start_date = date(2025, 10, 1)
        for month_offset in range(6):
            month_start = start_date + timedelta(days=30 * month_offset)

            # Monthly salary credit
            transactions.append({
                "transaction_id": f"TXN{txn_id:05d}",
                "user_id": user_id,
                "date": (month_start + timedelta(days=random.randint(0, 3))).isoformat(),
                "amount": round(monthly_income, 2),
                "category": "Salary",
                "type": "Credit",
                "on_time": None,
            })
            txn_id += 1

            # Monthly rent
            if demo["housing_status"] == "rent":
                on_time = random.random() < 0.85
                transactions.append({
                    "transaction_id": f"TXN{txn_id:05d}",
                    "user_id": user_id,
                    "date": (month_start + timedelta(days=random.randint(1, 5))).isoformat(),
                    "amount": round(monthly_income * random.uniform(0.2, 0.35), 2),
                    "category": "Rent",
                    "type": "Debit",
                    "on_time": on_time,
                })
                txn_id += 1

            # Utility bills (2-3 per month)
            for _ in range(random.randint(2, 3)):
                on_time = random.random() < 0.80
                transactions.append({
                    "transaction_id": f"TXN{txn_id:05d}",
                    "user_id": user_id,
                    "date": (month_start + timedelta(days=random.randint(5, 25))).isoformat(),
                    "amount": round(random.uniform(500, 5000), 2),
                    "category": "Utility",
                    "type": "Debit",
                    "on_time": on_time,
                })
                txn_id += 1

            # Food, discretionary, transport (5-10 per month)
            for _ in range(random.randint(5, 10)):
                cat = random.choice(["Food", "Discretionary", "Transport"])
                transactions.append({
                    "transaction_id": f"TXN{txn_id:05d}",
                    "user_id": user_id,
                    "date": (month_start + timedelta(days=random.randint(1, 28))).isoformat(),
                    "amount": round(random.uniform(100, 8000), 2),
                    "category": cat,
                    "type": "Debit",
                    "on_time": None,
                })
                txn_id += 1

            # EMI / Insurance (occasional)
            if random.random() < 0.4:
                on_time = random.random() < 0.90
                transactions.append({
                    "transaction_id": f"TXN{txn_id:05d}",
                    "user_id": user_id,
                    "date": (month_start + timedelta(days=random.randint(5, 15))).isoformat(),
                    "amount": round(random.uniform(2000, 15000), 2),
                    "category": random.choice(["EMI", "Insurance"]),
                    "type": "Debit",
                    "on_time": on_time,
                })
                txn_id += 1

    # Write as CSV
    csv_path = os.path.join(output_dir, "transactions.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["transaction_id", "user_id", "date", "amount", "category", "type", "on_time"])
        writer.writeheader()
        writer.writerows(transactions)

    # --- Product Catalog ---
    products = [
        {"product_id": "P001", "name": "Starter Credit Card", "type": "Starter Card", "min_score_required": 400, "interest_rate": 28.0},
        {"product_id": "P002", "name": "Basic Microloan", "type": "Microloan", "min_score_required": 450, "interest_rate": 22.0},
        {"product_id": "P003", "name": "Standard Credit Card", "type": "Standard Card", "min_score_required": 550, "interest_rate": 18.0},
        {"product_id": "P004", "name": "Personal Loan", "type": "Personal Loan", "min_score_required": 600, "interest_rate": 15.0},
        {"product_id": "P005", "name": "Gold Credit Card", "type": "Gold Card", "min_score_required": 700, "interest_rate": 14.0},
        {"product_id": "P006", "name": "Premium Credit Card", "type": "Premium Card", "min_score_required": 800, "interest_rate": 12.0},
        {"product_id": "P007", "name": "Home Loan (Pre-approved)", "type": "Home Loan", "min_score_required": 850, "interest_rate": 8.5},
    ]

    with open(os.path.join(output_dir, "product_catalog.json"), "w") as f:
        json.dump(products, f, indent=2)

    print(f"Generated {len(demographics)} users, {len(transactions)} transactions, {len(products)} products in {output_dir}")
    return demographics, transactions, products


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "synthetic")
    generate_synthetic_data(out)
