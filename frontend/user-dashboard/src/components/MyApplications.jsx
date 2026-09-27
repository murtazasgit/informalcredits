import { useCallback, useEffect, useState } from 'react'
import { authFetch } from '../auth'

const STATUS_LABEL = { submitted: 'Under review', approved: 'Approved', declined: 'Declined' }
const POLL_MS = 10000   // a lender's decision shows up without a manual refresh

export default function MyApplications({ apiBase, session, onUnauthorized, notice }) {
  const [apps, setApps] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    const res = await authFetch(`${apiBase}/users/${encodeURIComponent(session.userId)}/applications`, session, {}, onUnauthorized)
    if (!res.ok) { setError((await res.json().catch(() => ({}))).detail || 'Could not load applications'); return }
    setError(null)
    setApps(await res.json())
  }, [apiBase, session, onUnauthorized])

  useEffect(() => {
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  return (
    <section className="detail-page">
      <div className="upload-kicker">YOUR APPLICATIONS</div>
      <h1>Loan applications</h1>
      <p>Applications you sent to lenders, and what they decided.</p>
      {notice && <div className="offer-result pre_approved" role="status">{notice}</div>}
      {error && <div className="offer-error" role="alert">{error}</div>}
      {apps && apps.length === 0 && <p>No applications yet. Open a product you are eligible for and choose “Get loan approval”.</p>}
      <div className="recommendations-grid">
        {(apps || []).map(a => (
          <div key={a.application_id} className="product-card eligible">
            <span className="eligibility-tag eligible">{STATUS_LABEL[a.status] || a.status}</span>
            <div className="product-name">{a.bank_name}</div>
            <div className="product-reason">{a.product_name} · ₹{Number(a.requested_amount).toLocaleString()} over {a.tenure_months} months</div>
            {a.lender_note && <div className="product-reason">“{a.lender_note}”</div>}
            <small>Sent {new Date(a.created_at).toLocaleString()}</small>
          </div>
        ))}
      </div>
    </section>
  )
}
