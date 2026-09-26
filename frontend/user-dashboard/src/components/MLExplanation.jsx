const RISK_COLORS = {
  Excellent: 'var(--color-excellent)',
  Good: 'var(--color-good)',
  Fair: 'var(--color-fair)',
  Poor: 'var(--color-poor)',
}

export default function MLExplanation({ ruleScore, mlScore }) {
  if (!mlScore) {
    return (
      <div className="ml-explanation ml-explanation-unavailable">
        <div className="ml-explanation-title">ML cross-check</div>
        <p>The ML model couldn't score this applicant (missing model files or bad input). The rule-based score above is unaffected.</p>
      </div>
    )
  }

  const delta = mlScore.total_score - ruleScore.total_score
  const absDelta = Math.abs(delta)
  const pd = Math.round(mlScore.probability_of_default * 1000) / 10 // one decimal place, as %
  const color = RISK_COLORS[mlScore.risk_category] || 'var(--color-text-muted)'

  let agreement
  if (absDelta <= 40) {
    agreement = 'closely agrees with'
  } else if (absDelta <= 100) {
    agreement = 'is broadly in line with'
  } else {
    agreement = 'differs noticeably from'
  }

  return (
    <div className="ml-explanation">
      <div className="ml-explanation-title">ML cross-check</div>
      <div className="ml-explanation-body">
        <div className="ml-stat">
          <span className="ml-stat-value" style={{ color }}>{pd}%</span>
          <span className="ml-stat-label">Predicted probability of default</span>
        </div>
        <div className="ml-stat">
          <span className="ml-stat-value" style={{ color }}>{mlScore.total_score}</span>
          <span className="ml-stat-label">Equivalent ML score ({mlScore.risk_category})</span>
        </div>
      </div>
      <p className="ml-explanation-summary">
        Trained on historical repayment outcomes, the model puts this applicant's chance of default at{' '}
        <strong>{pd}%</strong>, giving an equivalent score of <strong>{mlScore.total_score}</strong>. That{' '}
        {agreement} the rule-based score of {ruleScore.total_score}
        {absDelta > 0 && ` (${delta > 0 ? '+' : ''}${delta} pts)`}.
      </p>
    </div>
  )
}