import { useMemo } from 'react'

const RISK_COLORS = {
  Excellent: '#0d9f6e',
  Good: '#2563eb',
  Fair: '#d97706',
  Poor: '#dc2626',
}

export default function ScoreGauge({ score }) {
  const { total_score, risk_category } = score
  const color = RISK_COLORS[risk_category] || '#8b91a8'

  // SVG circle parameters
  const radius = 85
  const circumference = 2 * Math.PI * radius
  const percentage = total_score / 1000
  const offset = circumference * (1 - percentage)

  return (
    <>
      <div className="score-ring-container">
        <svg viewBox="0 0 200 200">
          <circle
            className="score-ring-bg"
            cx="100"
            cy="100"
            r={radius}
          />
          <circle
            className="score-ring-fill"
            cx="100"
            cy="100"
            r={radius}
            stroke={color}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="score-number">
          <div className="value" style={{ color }}>{total_score}</div>
          <div className="out-of">/ 1000</div>
        </div>
      </div>
      <div className="score-category" style={{ color }}>
        {risk_category}
      </div>
      <div className="score-method">
        Rule-Based Assessment
      </div>
    </>
  )
}
