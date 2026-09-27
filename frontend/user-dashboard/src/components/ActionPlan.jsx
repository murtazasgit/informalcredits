import { useEffect, useState } from 'react'

export default function ActionPlan({ features, recommendations, apiBase }) {
  const ineligible = recommendations.filter(r => !r.eligible)
    .sort((a, b) => a.min_score_required - b.min_score_required)
  const [productId, setProductId] = useState(ineligible[0]?.product_id || '')
  const [plan, setPlan] = useState(null)
  const [error, setError] = useState(null)

  const selected = ineligible.find(p => p.product_id === productId) || ineligible[0]

  useEffect(() => {
    if (!selected) return
    let cancelled = false
    setPlan(null)
    setError(null)
    fetch(`${apiBase}/target-achievement`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        features,
        target_score: selected.min_score_required,
        target_product_name: selected.name,
      }),
    })
      .then(async res => {
        if (!res.ok) throw new Error((await res.json()).detail || 'Could not compute a plan')
        return res.json()
      })
      .then(data => { if (!cancelled) setPlan(data) })
      .catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [selected?.product_id, features, apiBase])

  if (!selected) {
    return (
      <div className="action-empty">
        <strong>You're eligible for every product.</strong>
        <p>Nothing to fix right now — keep up your current payment habits to stay at this level.</p>
      </div>
    )
  }

  const steps = (plan?.plan || []).slice(0, 3)

  return (
    <div className="action-plan">
      <div className="target-achievement-controls">
        <label htmlFor="plan-product">Goal:</label>
        <select id="plan-product" value={selected.product_id} onChange={e => setProductId(e.target.value)}>
          {ineligible.map(p => (
            <option key={p.product_id} value={p.product_id}>
              {p.name} (needs {p.min_score_required})
            </option>
          ))}
        </select>
      </div>

      {error && <p className="target-achievement-error">{error}</p>}
      {!plan && !error && <p className="action-loading">Building your plan…</p>}
      {plan && (
        <>
          <p className="target-achievement-message">{plan.message}</p>
          <div className="action-cards">
            {steps.map(step => (
              <div key={step.feature_field} className="action-card">
                <div className="action-card-title">{step.label}</div>
                <div className="action-card-change">{step.current_value} → {step.target_value}</div>
                <div className="action-card-gain">+{step.expected_point_gain} pts</div>
              </div>
            ))}
          </div>
          <p className="target-achievement-projection">
            Projected score: <strong>{plan.projected_score}</strong> / needed {plan.target_score}
            {plan.gap_closed ? ' — qualifies ✓' : ' — keep going, this gets you closer'}
          </p>
        </>
      )}
    </div>
  )
}
