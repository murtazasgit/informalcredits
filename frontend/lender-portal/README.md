# Module: Lender Portal (Business User Frontend)

## Goal
Let banks/microfinance/fintech lenders log in, search/filter anonymized candidates, view risk
profiles, and push loan/card offers.

## Tech stack
- **React** (can be a second route/app in the same Vite project as the user dashboard, or a
  separate app if time allows — same stack either way: Tailwind + Recharts)

## Input (calls to `backend/api/`)
- `POST /auth/login` (role=lender) → JWT
- `GET /lender/candidates?min_score=650&city_tier=tier-1` → anonymized candidate list
- `POST /lender/offer` → push an offer to a candidate

## Output
- Login screen
- Candidate search/filter table (score range, city tier, risk category)
- Candidate detail view (anonymized — no name/address/phone until offer accepted)
- "Push Offer" button per candidate or bulk-select

## Starter code
```jsx
// CandidateSearch.jsx
import { useState } from "react";

export default function CandidateSearch({ token }) {
  const [candidates, setCandidates] = useState([]);
  const [minScore, setMinScore] = useState(650);

  const search = async () => {
    const res = await fetch(`/api/lender/candidates?min_score=${minScore}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    setCandidates(await res.json());
  };

  const pushOffer = async (candidateRef, productId) => {
    await fetch("/api/lender/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ candidate_ref: candidateRef, product_id: productId })
    });
  };

  return (
    <div>
      <input type="number" value={minScore} onChange={e => setMinScore(e.target.value)} />
      <button onClick={search}>Search</button>
      {candidates.map(c => (
        <div key={c.candidate_ref} className="border p-2 my-1">
          {c.candidate_ref} — Score: {c.score} ({c.risk_category})
          <button onClick={() => pushOffer(c.candidate_ref, "P001")}>Push Offer</button>
        </div>
      ))}
    </div>
  );
}
```

## Tasks checklist
- [ ] Build lender login screen
- [ ] Build candidate search/filter table
- [ ] Build "Push Offer" flow (single + bulk select)
- [ ] Confirm anonymization: no PII fields ever rendered in this UI before offer acceptance

## Handoff
Nothing downstream — final UI layer for Business Mode.
