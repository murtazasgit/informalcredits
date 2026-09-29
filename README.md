# InformalCredits

**Explainable alternative credit scoring for people the credit bureaus can't see.**

InformalCredits is an alternative credit scoring platform that evaluates creditworthiness using everyday financial behaviour such as bill payments, rent, employment, spending, and savings. It provides an explainable score, shows users what factors affect their score, and includes tools for score improvement, financial product recommendations, and lender-borrower connections.

> **Prototype only.** All data is synthetic and the scores are for demonstration purposes only.

## Features

* Explainable credit scoring
* Rule-based 0–1000 scoring system
* ML-based score cross-check
* "Why this score?" explanations
* What-if score simulator
* Credit improvement planner
* Financial product recommendations
* Borrower dashboard
* Lender portal
* Privacy-preserving candidate matching
* PDF transparency reports

## Tech Stack

**Backend:** FastAPI, Python, Pydantic, SQLAlchemy, SQLite, scikit-learn
**Frontend:** React, Vite, Recharts
**Other:** ReportLab, pytest

## Installation

### Prerequisites

* Python 3.11+
* Node.js 18+

### 1. Clone the repository

```bash
git clone https://github.com/murtazasgit/informalcredits.git
cd informalcredits
```

### 2. Backend Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the backend:

```powershell
python -m uvicorn backend.api.main:app --reload
```

Backend: `http://localhost:8000`

API Docs: `http://localhost:8000/docs`

### 3. Frontend Setup

Open a second terminal:

```powershell
cd frontend/user-dashboard
npm install
npm run dev
```

Frontend: `http://localhost:3000`

### 4. Lender Portal

```text
http://localhost:3000/#/lender
```
