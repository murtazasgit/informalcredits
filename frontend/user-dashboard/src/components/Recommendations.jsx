import { useState } from 'react'

const DECISION_LABEL = {
  pre_approved: 'Pre-approved',
  manual_review: 'Sent for manual review',
  declined: 'Declined',
}

export default function Recommendations({ recommendations, currentScore, features, apiBase }) {
  // productId -> { loading, error, result }
  const [applications, setApplications] = useState({})

  const preapprove = async (productId) => {
    setApplications(a => ({ ...a, [productId]: { loading: true } }))
    try {
      const res = await fetch(`${apiBase}/offers/preapprove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, features, user_id: features?.user_id }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Pre-approval failed')
      setApplications(a => ({ ...a, [productId]: { result: data } }))
    } catch (e) {
      setApplications(a => ({ ...a, [productId]: { error: e.message } }))
    }
  }

  return (
    <div className="recommendations-grid" style={{ marginBottom: '32px' }}>
      {recommendations.map((rec) => {
        const app = applications[rec.product_id] || {}
        return (
          <div
            key={rec.product_id}
            className={`product-card ${rec.eligible ? 'eligible' : 'ineligible'}`}
          >
            <span className={`eligibility-tag ${rec.eligible ? 'eligible' : 'ineligible'}`}>
              {rec.eligible ? '✓ Eligible' : 'Not yet'}
            </span>

            <div className="product-name">{rec.name}</div>

            <div className="product-rate">
              {rec.interest_rate}%
              <span> p.a.</span>
            </div>

            <div className="product-reason">{rec.reason}</div>

            {rec.eligible && features && apiBase && !app.result && (
              <button type="button" className="offer-button" disabled={app.loading}
                onClick={() => preapprove(rec.product_id)}>
                {app.loading ? 'Contacting bank…' : 'Get pre-approved'}
              </button>
            )}
            {app.error && <div className="offer-error" role="alert">{app.error}</div>}
            {app.result && (
              <div className={`offer-result ${app.result.decision}`} role="status">
                <strong>{DECISION_LABEL[app.result.decision] || app.result.decision}</strong>
                {app.result.credit_limit > 0 && <span> · limit {app.result.credit_limit.toLocaleString()}</span>}
                <div>{app.result.reason}</div>
                <small>Ref {app.result.application_id}</small>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
