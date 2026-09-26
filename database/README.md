# Module: Database (SQLite)

## Goal
Store users, transactions, scores, product catalog, and offers so the API isn't recomputing
everything on every request.

## Tech stack
**SQLite + SQLAlchemy** — zero setup, judges can run the project with no external DB service.

## Schema (DDL)
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    age INTEGER,
    employment_status TEXT,
    months_employed INTEGER,
    education_level TEXT,
    monthly_income REAL,
    city_tier TEXT,
    housing_status TEXT,
    housing_months INTEGER
);

CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    date TEXT,
    amount REAL,
    category TEXT,
    type TEXT,
    on_time BOOLEAN
);

CREATE TABLE scores (
    user_id TEXT REFERENCES users(user_id),
    total_score INTEGER,
    risk_category TEXT,
    breakdown_json TEXT,   -- store the full breakdown dict as JSON text
    computed_at TEXT,
    PRIMARY KEY (user_id, computed_at)
);

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    min_score_required INTEGER,
    interest_rate REAL
);

CREATE TABLE offers (
    offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT REFERENCES users(user_id),
    product_id TEXT REFERENCES products(product_id),
    status TEXT,   -- 'pushed', 'accepted', 'rejected'
    pushed_at TEXT
);

CREATE TABLE lenders (
    lender_id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
);
```

## SQLAlchemy model example
```python
from sqlalchemy import Column, String, Integer, Float, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    age = Column(Integer)
    employment_status = Column(String)
    months_employed = Column(Integer)
    education_level = Column(String)
    monthly_income = Column(Float)
    city_tier = Column(String)
    housing_status = Column(String)
    housing_months = Column(Integer)
```

## Tasks checklist
- [ ] Set up SQLAlchemy engine pointed at `altcredit.db`
- [ ] Define all 6 tables as ORM models
- [ ] Write a seed script that loads synthetic data + product catalog on first run

## Handoff
Import the `Base`/models into `backend/api/` for all persistence calls.
