// Max points per factor for bar width calculation
const MAX_POINTS = {
  'On-time payment track record': 200,
  'Payment delinquency record': 150,
  'Employment stability': 150,
  'Spending-to-income ratio': 120,
  'Debt-to-income ratio': 120,
  'Credit utilization': 100,
  'Housing / rent history': 80,
  'Essential vs. discretionary spending': 80,
  'Savings buffer': 80,
  'Utility & bill payment consistency': 70,
  'Monthly cash-flow stability': 70,
  'Education level': 50,
  'Positive financial habits': 50,
  'Risk flags detected': 50,
}

function describe(factor, maxPts) {
  const pts = factor.points
  if (pts < 0) return `costs you ${Math.abs(pts)} points`
  if (pts === 0) return 'no points earned'
  const ratio = pts / maxPts
  const level = ratio >= 0.8 ? 'a strength' : ratio >= 0.5 ? 'solid' : 'room to improve'
  return `${pts} of ${maxPts} possible points (${level})`
}

export default function FactorBreakdown({ explanation }) {
  const { factors } = explanation

  // Show every factor (including zero-point ones) so the explanation is complete
  const visibleFactors = factors

  return (
    <div className="factors-list">
      {visibleFactors.map((factor, i) => {
        const maxPts = MAX_POINTS[factor.label] || 200
        const barWidth = Math.min(Math.abs(factor.points) / maxPts * 100, 100)
        const isPositive = factor.direction === 'positive'

        return (
          <div key={i} className="factor-item">
            <div className={`factor-icon ${isPositive ? 'positive' : 'negative'}`}>
              {isPositive ? '↑' : '↓'}
            </div>
            <div className="factor-info">
              <div className="factor-label">
                {factor.label}
                <span className="factor-detail"> � {describe(factor, maxPts)}</span>
              </div>
              <div className="factor-bar">
                <div
                  className={`factor-bar-fill ${isPositive ? 'positive' : 'negative'}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
            <div className={`factor-points ${isPositive ? 'positive' : 'negative'}`}>
              {factor.points > 0 ? '+' : ''}{factor.points}
            </div>
          </div>
        )
      })}
    </div>
  )
}
