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

export default function FactorBreakdown({ explanation }) {
  const { factors } = explanation

  // Show top 10 factors, skip zeros
  const visibleFactors = factors
    .filter(f => f.points !== 0)
    .slice(0, 10)

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
              <div className="factor-label">{factor.label}</div>
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
