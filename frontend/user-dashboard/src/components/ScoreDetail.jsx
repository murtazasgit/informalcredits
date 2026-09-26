import FactorBreakdown from './FactorBreakdown'
import Recommendations from './Recommendations'
import ScoreGauge from './ScoreGauge'

export default function ScoreDetail({ result, onBack }) {
  const { score, explanation, recommendations, features, warnings } = result

  return (
    <section className="detail-page">
      <button className="back-button" type="button" onClick={onBack}>Back to results</button>

      <header className="detail-heading">
        <div>
          <div className="upload-kicker">APPLICANT / ROW {result.row_number}</div>
          <h1>{result.user_id}</h1>
          <p>{explanation.summary_text}</p>
        </div>
      </header>

      {warnings?.length > 0 && (
        <div className="detail-warnings" role="status">
          <strong>Input notes</strong>
          {warnings.map((warning, index) => <p key={index}>{warning}</p>)}
        </div>
      )}

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
          <div>
            <h2>Product matches</h2>
            <p>{recommendations.filter(item => item.eligible).length} products currently eligible</p>
          </div>
        </div>
        <Recommendations recommendations={recommendations} currentScore={score.total_score} />
      </section>

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