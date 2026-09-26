import { useEffect, useState } from 'react'
import ScoreGauge from '../components/ScoreGauge'
import FactorBreakdown from '../components/FactorBreakdown'
import MLExplanation from '../components/MLExplanation'
import Recommendations from '../components/Recommendations'

// Lender's view of a candidate: the same score analysis the consumer sees.
export default function LenderCandidateDetail({ userId, guarded, products, onBack, onPushed }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [productId, setProductId] = useState(products[0]?.product_id || '')
  const [message, setMessage] = useState('')
  const [notice, setNotice] = useState(null)

  const load = async () => {
    try {
      const res = await guarded(`/lender/candidates/${encodeURIComponent(userId)}`)
      if (!res.ok) throw new Error((await res.json()).detail || 'Could not load candidate')
      setData(await res.json())
    } catch (e) { setError(e.message) }
  }
  useEffect(() => { load() }, [userId]) // eslint-disable-line react-hooks/exhaustive-deps

  const push = async () => {
    const res = await guarded('/lender/offers', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_ids: [userId], product_id: productId, message }),
    })
    const body = await res.json()
    if (!res.ok) { setNotice(body.detail || 'Push failed'); return }
    const r = body.results[0]
    setNotice(r.status === 'pushed' ? 'Offer sent to the candidate.' : r.status === 'duplicate'
      ? 'You already have a live offer for this product.' : `Not sent: ${r.detail || r.status}`)
    onPushed?.()
    load()
  }

  const back = <button className="back-button" type="button" onClick={onBack}>Back to candidates</button>
  if (error) return <section className="detail-page">{back}<p className="offer-error">{error}</p></section>
  if (!data) return <section className="detail-page">{back}<p>Loading…</p></section>

  const { score, ml_score, explanation, recommendations, features, profile, contact } = data
  const profileLine = [
    profile.city_tier, profile.employment_status, profile.education_level,
    profile.age && `age ${profile.age}`,
    profile.monthly_income && `income ${Number(profile.monthly_income).toLocaleString()}/mo`,
  ].filter(Boolean).join(' · ')

  return (
    <section className="detail-page">
      {back}

      <header className="detail-heading">
        <div>
          <div className="upload-kicker">CANDIDATE</div>
          <h1>{data.user_id}</h1>
          <p>{explanation.summary_text}</p>
          <p className="lender-profile">{profileLine}</p>
        </div>
        <div className="lender-contact detail-panel">
          <strong>Contact details</strong>
          {contact
            ? <div>{contact.name}<br />{contact.phone}<br />{contact.address}</div>
            : <span className="lender-masked">Name, phone and address are hidden until the candidate accepts an offer{data.offer_status ? ` (offer ${data.offer_status})` : ''}.</span>}
        </div>
      </header>

      <div className="detail-grid">
        <section className="detail-panel detail-score-panel">
          <h2>Credit score</h2>
          <ScoreGauge score={score} />
        </section>
        <section className="detail-panel">
          <h2>Score factors</h2>
          <FactorBreakdown explanation={explanation} />
        </section>
      </div>

      <section className="detail-section">
        <div className="detail-section-heading">
          <h2>Risk engine calculation</h2>
          <p>Points earned per rule, exactly as the applicant sees them.</p>
        </div>
        <div className="results-table-wrap">
          <table className="results-table">
            <thead><tr><th>Rule</th><th>Points</th><th>Explanation</th></tr></thead>
            <tbody>
              {explanation.factors.map(f => (
                <tr key={f.label}>
                  <td>{f.label}</td>
                  <td className="table-score" style={{ color: f.points < 0 ? 'var(--color-poor)' : undefined }}>{f.points > 0 ? '+' : ''}{f.points}</td>
                  <td>{f.text}</td>
                </tr>
              ))}
              <tr><td><strong>Total (clamped 0–1000)</strong></td><td className="table-score">{score.total_score}</td><td>{score.risk_category}</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="detail-section">
        <div className="detail-section-heading">
          <h2>ML model explanation</h2>
          <p>An independent numerical check on the rule-based score.</p>
        </div>
        <MLExplanation ruleScore={score} mlScore={ml_score} />
      </section>

      <section className="detail-section">
        <div className="detail-section-heading"><h2>Product matches</h2></div>
        <Recommendations recommendations={recommendations} currentScore={score.total_score} />
      </section>

      <section className="lender-push detail-panel">
        <label>Offer a product
          <select value={productId} onChange={e => setProductId(e.target.value)}>
            {products.map(p => <option key={p.product_id} value={p.product_id}>{p.name} ({p.interest_rate}%, min {p.min_score_required})</option>)}
          </select>
        </label>
        <label>Message<input value={message} onChange={e => setMessage(e.target.value)} placeholder="Optional note" /></label>
        <button type="button" className="offer-button" disabled={!productId} onClick={push}>Push offer to {data.user_id}</button>
        {notice && <span role="status">{notice}</span>}
      </section>

      <details className="feature-details">
        <summary>View engineered feature values</summary>
        <dl>
          {Object.entries(features).filter(([k]) => k !== 'user_id').map(([k, v]) => (
            <div key={k}><dt>{k.replaceAll('_', ' ')}</dt><dd>{Array.isArray(v) ? v.join(', ') || 'None' : v}</dd></div>
          ))}
        </dl>
      </details>
    </section>
  )
}
