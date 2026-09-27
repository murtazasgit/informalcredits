import FactorBreakdown from './FactorBreakdown'
import Recommendations from './Recommendations'
import MLExplanation from './MLExplanation'
import ActionPlan from './ActionPlan'
import ExplainDashboard from './ExplainDashboard'
import { useState } from 'react'

async function downloadReport(result, apiBase) {
  const { score, explanation, recommendations, ml_score } = result
  const res = await fetch(`${apiBase}/report/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ score, explanation, recommendations, ml_score }),
  })
  if (!res.ok) throw new Error('Could not generate the report')
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = `transparency-report-${result.user_id}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export default function ScoreDetail({ result, onBack, apiBase, onApply, afterHero }) {
  const { score, ml_score, explanation, recommendations, features, warnings } = result
  const [tab, setTab] = useState('overview')
  const [reporting, setReporting] = useState(false)
  const [reportError, setReportError] = useState(null)

  const handleReport = async () => {
    setReporting(true)
    setReportError(null)
    try { await downloadReport(result, apiBase) } catch (e) { setReportError(e.message) } finally { setReporting(false) }
  }

  return (
    <section className="detail-page">
      {onBack && <button className="back-button" type="button" onClick={onBack}>Back to results</button>}

      <header className="score-hero">
        <div>
          <div className="upload-kicker">{result.row_number ? `APPLICANT / ROW ${result.row_number}` : 'YOUR CREDIT SCORE'}</div>
          <div className="score-hero-label">{result.user_id}</div>
          <div className="score-hero-num">{score.total_score}<small>/ 1000</small></div>
          <span className={`risk-pill risk-${score.risk_category.toLowerCase()}`}>{score.risk_category}</span>
          <p>{explanation.summary_text}</p>
        </div>
        <div className="score-hero-actions">
          <button type="button" className="offer-button" onClick={handleReport} disabled={reporting}>
            {reporting ? 'Generating…' : 'Download Transparency Report (PDF)'}
          </button>
          {reportError && <div className="offer-error" role="alert">{reportError}</div>}
        </div>
      </header>

      {afterHero}

      {warnings?.length > 0 && (
        <div className="detail-warnings" role="status">
          <strong>Input notes</strong>
          {warnings.map((warning, index) => <p key={index}>{warning}</p>)}
        </div>
      )}

      <div className="detail-tabs" role="tablist">
        <button type="button" role="tab" className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>Score &amp; results</button>
        <button type="button" role="tab" className={tab === 'why' ? 'active' : ''} onClick={() => setTab('why')}>Why this score</button>
        <button type="button" role="tab" className={tab === 'plan' ? 'active' : ''} onClick={() => setTab('plan')}>Recommended actions</button>
      </div>

      {tab === 'why' && <ExplainDashboard features={features} apiBase={apiBase} />}

      {tab === 'plan' && (
        <section className="detail-section">
          <div className="detail-section-heading">
            <h2>Recommended actions</h2>
            <p>Changes that would raise your score enough to qualify for the product you want.</p>
          </div>
          <ActionPlan key={result.user_id} features={features} recommendations={recommendations} apiBase={apiBase} />
        </section>
      )}

      {tab === 'overview' && (<>
      <div className="detail-grid">
        <section className="detail-panel">
          <h2>Score factors</h2>
          <FactorBreakdown explanation={explanation} />
        </section>
      </div>

      <section className="detail-section">
        <div className="detail-section-heading">
          <h2>ML model explanation</h2>
          <p>An independent numerical check on the rule-based score above, from a model trained on historical repayment outcomes.</p>
        </div>
        <MLExplanation ruleScore={score} mlScore={ml_score} />
      </section>

      <section className="detail-section">
        <div className="detail-section-heading">
          <div>
            <h2>Product matches</h2>
            <p>{recommendations.filter(item => item.eligible).length} products currently eligible</p>
          </div>
        </div>
        <Recommendations recommendations={recommendations} onApply={onApply} />
      </section>

      </>)}

      <details className="feature-details">
        <summary>View engineered feature values</summary>
        <dl>
          {Object.entries(features).filter(([key]) => key !== 'user_id').map(([key, value]) => (
            <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') || 'None' : value}</dd></div>
          ))}
        </dl>
      </details>
    </section>
  )
}