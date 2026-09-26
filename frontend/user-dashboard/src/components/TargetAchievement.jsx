import { useState } from 'react'

export default function TargetAchievement({ features, ineligibleProducts, apiBase }) {
  const ineligible = ineligibleProducts || []
  const [productId, setProductId] = useState(ineligible[0]?.product_id || '')
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  if (ineligible.length === 0) {
    return null // already eligible for everything — nothing to plan toward
  }

  const selected = ineligible.find(p => p.product_id === productId) || ineligible[0]

  const handleCheck = async () => {
    setLoading(true)
    setError(null)
    setPlan(null)
    try {
      const res = await fetch(`${apiBase}/target-achievement`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          features,
          target_score: selected.min_score_required,
          target_product_name: selected.name,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Could not compute a plan')
      }
      setPlan(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="target-achievement">
      <div className="target-achievement-controls">
        <label htmlFor="target-product">How do I qualify for…</label>
        <select
          id="target-product"
          value={selected.product_id}
          onChange={(e) => { setProductId(e.target.value); setPlan(null) }}
        >
          {ineligible.map(p => (
            <option key={p.product_id} value={p.product_id}>
              {p.name} (needs {p.min_score_required})
            </option>
          ))}
        </select>
        <button type="button" className="row-action" onClick={handleCheck} disabled={loading}>
          {loading ? 'Calculating…' : 'Show me the plan'}
        </button>
      </div>

      {error && <p className="target-achievement-error">{error}</p>}

      {plan && (
        <div className="target-achievement-plan">
          <p className="target-achievement-message">{plan.message}</p>
          {plan.plan?.length > 0 && (
            <ul className="target-achievement-steps">
              {plan.plan.map((step) => (
                <li key={step.feature_field}>
                  <strong>{step.label}:</strong> {step.current_value} → {step.target_value}
                  <span className="target-achievement-gain"> (+{step.expected_point_gain} pts)</span>
                </li>
              ))}
            </ul>
          )}
          <p className="target-achievement-projection">
            Projected score: <strong>{plan.projected_score}</strong> / target {plan.target_score}
            {plan.gap_closed ? ' — qualifies ✓' : ' — not quite there yet'}
          </p>
        </div>
      )}
    </div>
  )
}