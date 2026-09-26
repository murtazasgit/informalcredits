export default function Recommendations({ recommendations, currentScore }) {
  return (
    <div className="recommendations-grid" style={{ marginBottom: '32px' }}>
      {recommendations.map((rec, i) => (
        <div
          key={rec.product_id}
          className={`product-card ${rec.eligible ? 'eligible' : 'ineligible'}`}
        >
          <span className={`eligibility-tag ${rec.eligible ? 'eligible' : 'ineligible'}`}>
            {rec.eligible ? '✓ Eligible' : 'Not yet'}
          </span>

          <div className="product-name">{rec.name}</div>

          <div className="product-rate">
            {rec.interest_rate}%
            <span> p.a.</span>
          </div>

          <div className="product-reason">{rec.reason}</div>
        </div>
      ))}
    </div>
  )
}
