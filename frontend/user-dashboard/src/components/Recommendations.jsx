// Product cards. "Get loan approval" (eligible products, signed-in borrower only) opens the application form
// for that product, where the borrower picks which registered lender to apply to.
export default function Recommendations({ recommendations, onApply }) {
  return (
    <div className="recommendations-grid" style={{ marginBottom: '32px' }}>
      {recommendations.map((rec) => (
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

          {rec.eligible && onApply && (
            <button type="button" className="offer-button" onClick={() => onApply(rec)}>
              Get loan approval
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
