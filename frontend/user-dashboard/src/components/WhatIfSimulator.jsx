import { useState } from 'react'

// Predefined scenarios from the spec
const SCENARIOS = [
  {
    label: 'Save ₹1000/month for 3 months',
    changes: { savings_days: 90, cashflow_volatility_pct: 5 },
    description: 'Increase savings buffer and reduce cash-flow volatility',
  },
  {
    label: 'Set up auto-pay for bills',
    changes: { on_time_payment_pct: 99, digital_bill_ontime_pct: 98 },
    description: 'Maximize payment consistency through automation',
  },
  {
    label: 'High discretionary spending',
    changes: { essential_spend_pct: 35, spend_to_income_ratio: 0.85 },
    description: 'Spend 75% of income on non-essentials for 2 months',
  },
  {
    label: 'Miss bill payments',
    changes: { on_time_payment_pct: 60, delinquency_flags: ['30_day_late', '60_day_late'] },
    description: 'Miss internet/mobile bill by 45 days, delay rent by 15 days',
  },
]

export default function WhatIfSimulator({ userId, currentScore, features, apiBase }) {
  const [selectedScenario, setSelectedScenario] = useState(null)
  const [customField, setCustomField] = useState('')
  const [customValue, setCustomValue] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const EDITABLE_FIELDS = [
    { key: 'savings_days', label: 'Savings days', type: 'number' },
    { key: 'on_time_payment_pct', label: 'On-time payment %', type: 'number' },
    { key: 'digital_bill_ontime_pct', label: 'Bill on-time %', type: 'number' },
    { key: 'spend_to_income_ratio', label: 'Spend/income ratio', type: 'number' },
    { key: 'essential_spend_pct', label: 'Essential spend %', type: 'number' },
    { key: 'cashflow_volatility_pct', label: 'Cash-flow volatility %', type: 'number' },
    { key: 'debt_to_income_ratio', label: 'Debt/income ratio', type: 'number' },
    { key: 'months_employed', label: 'Months employed', type: 'number' },
  ]

  async function runSimulation(changes) {
    setLoading(true)
    setResult(null)
    try {
      const resp = await fetch(`${apiBase}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          hypothetical_changes: changes,
        }),
      })
      if (!resp.ok) throw new Error('Simulation failed')
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      setResult({ error: err.message })
    } finally {
      setLoading(false)
    }
  }

  function handleScenario(idx) {
    setSelectedScenario(idx)
    setCustomField('')
    setCustomValue('')
    runSimulation(SCENARIOS[idx].changes)
  }

  function handleCustomSimulation() {
    if (!customField || customValue === '') return
    const changes = {}
    const val = parseFloat(customValue)
    if (isNaN(val)) return
    changes[customField] = val
    setSelectedScenario(null)
    runSimulation(changes)
  }

  return (
    <div className="simulator-form">
      {/* Preset Scenarios */}
      <div>
        <label style={{ fontSize: '13px', fontWeight: 500, color: '#5a6178', marginBottom: '8px', display: 'block' }}>
          Quick scenarios
        </label>
        <div className="scenario-buttons">
          {SCENARIOS.map((s, i) => (
            <button
              key={i}
              className={`scenario-btn ${selectedScenario === i ? 'active' : ''}`}
              onClick={() => handleScenario(i)}
              disabled={loading}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Custom simulation */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
        <div className="form-group" style={{ flex: 1 }}>
          <label>Or adjust a specific factor</label>
          <select
            value={customField}
            onChange={e => setCustomField(e.target.value)}
          >
            <option value="">Select factor...</option>
            {EDITABLE_FIELDS.map(f => (
              <option key={f.key} value={f.key}>
                {f.label} (current: {features[f.key] ?? '—'})
              </option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ width: '140px' }}>
          <label>New value</label>
          <input
            type="number"
            step="any"
            value={customValue}
            onChange={e => setCustomValue(e.target.value)}
            placeholder="e.g. 95"
          />
        </div>
        <button
          className="btn btn-primary"
          onClick={handleCustomSimulation}
          disabled={loading || !customField || customValue === ''}
          style={{ height: '42px' }}
        >
          {loading ? 'Running...' : 'Simulate'}
        </button>
      </div>

      {/* Result */}
      {result && !result.error && (
        <div className={`simulation-result ${
          result.delta > 0 ? 'positive' : result.delta < 0 ? 'negative' : 'neutral'
        }`}>
          <div className="sim-delta" style={{
            color: result.delta > 0 ? 'var(--color-positive)' :
                   result.delta < 0 ? 'var(--color-negative)' : 'var(--color-text-secondary)'
          }}>
            {result.delta > 0 ? '+' : ''}{result.delta} points
          </div>
          <div className="sim-message">{result.message}</div>
          <div className="sim-scores">
            <div className="sim-score-item">
              <div className="sim-score-label">Current</div>
              <div className="sim-score-value">{result.old_score}</div>
            </div>
            <div className="sim-score-item" style={{ fontSize: '20px', color: '#8b91a8', alignSelf: 'center' }}>→</div>
            <div className="sim-score-item">
              <div className="sim-score-label">Projected</div>
              <div className="sim-score-value" style={{
                color: result.delta > 0 ? 'var(--color-positive)' :
                       result.delta < 0 ? 'var(--color-negative)' : 'var(--color-text-primary)'
              }}>
                {result.new_score}
              </div>
            </div>
          </div>
        </div>
      )}

      {result && result.error && (
        <div className="simulation-result negative">
          <div className="sim-message">Error: {result.error}</div>
        </div>
      )}
    </div>
  )
}
