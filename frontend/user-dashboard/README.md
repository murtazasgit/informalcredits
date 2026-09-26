# Module: User Dashboard (Frontend)

## Goal
Show the user their score, a visual factor breakdown, product recommendations, a "what-if"
simulator, and a report download button.

## Tech stack
- **React** (Vite for fast setup)
- **Tailwind CSS** — fast, clean fintech-style UI (Revolut/Chime look)
- **Recharts** — score gauge / bar chart for factor breakdown

## Input (calls to `backend/api/`)
- `GET /score/{user_id}` → score + breakdown
- `GET /explain/{user_id}` → factors list
- `POST /simulate` → hypothetical score change
- `GET /report/{user_id}` → PDF download link

## Output
Rendered pages/components:
- `ScoreGauge` — color-coded score (4 risk bands: Poor/Fair/Good/Excellent)
- `FactorBreakdownChart` — bar chart of `factors` (from `/explain`), positive vs negative color-coded
- `RecommendationCards` — product cards where `min_score_required <= user.score`
- `WhatIfSimulator` — form (e.g. "save ₹1000 more/month for 3 months") → calls `/simulate` → shows delta
- `ReportButton` — downloads PDF from `/report/{user_id}`

## Starter code
```jsx
// ScoreGauge.jsx
import { useEffect, useState } from "react";

function riskColor(score) {
  if (score >= 800) return "text-green-600";
  if (score >= 600) return "text-blue-600";
  if (score >= 400) return "text-yellow-600";
  return "text-red-600";
}

export default function ScoreGauge({ userId }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch(`/api/score/${userId}`).then(r => r.json()).then(setData);
  }, [userId]);
  if (!data) return <div>Loading...</div>;
  return (
    <div className="p-6 rounded-xl shadow bg-white">
      <div className={`text-6xl font-bold ${riskColor(data.total_score)}`}>
        {data.total_score}
      </div>
      <div className="text-lg text-gray-500">{data.risk_category}</div>
    </div>
  );
}
```

## Tasks checklist
- [ ] Set up Vite + Tailwind
- [ ] Build `ScoreGauge`, `FactorBreakdownChart`, `RecommendationCards`, `WhatIfSimulator`, `ReportButton`
- [ ] Wire all components to the API endpoints listed above
- [ ] Handle loading/error states (API might be slow or return missing-data cases)

## Handoff
Nothing downstream — this is the final UI layer for the User Mode.

## Onboarding — New User Login Portal (stretch — "Good to Have")

### Goal
Let a brand-new user create a profile and upload their transaction history, instead of only
working with pre-seeded synthetic users.

### Pages needed
1. **Sign-up** — username/password → calls `POST /auth/register` (role="user")
2. **Profile creation** — form capturing all `Demographic` fields (age, employment_status,
   months_employed, education_level, monthly_income, city_tier, housing_status, housing_months)
   → calls `POST /users/register`
3. **Upload transactions** — file picker accepting `.csv` or `.pdf` → calls
   `POST /transactions/upload` (backend routes PDF to the OCR path — see `data/README.md`)

### Starter code
```jsx
// ProfileCreation.jsx
import { useState } from "react";

export default function ProfileCreation({ onDone }) {
  const [form, setForm] = useState({});
  const submit = async () => {
    await fetch("/api/users/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form)
    });
    onDone();
  };
  return (
    <form onSubmit={e => { e.preventDefault(); submit(); }} className="space-y-3">
      <input placeholder="Age" onChange={e => setForm({...form, age: +e.target.value})} />
      <input placeholder="Monthly income" onChange={e => setForm({...form, monthly_income: +e.target.value})} />
      {/* ...remaining Demographic fields... */}
      <button type="submit">Create Profile</button>
    </form>
  );
}
```

### Tasks checklist
- [ ] Build sign-up + profile creation + upload pages
- [ ] Validate required fields client-side before submit
- [ ] After upload, redirect to the score dashboard (triggers `POST /score/{user_id}` automatically)
