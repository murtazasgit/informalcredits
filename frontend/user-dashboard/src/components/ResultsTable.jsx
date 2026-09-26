export default function ResultsTable({ data, onSelect, onBack }) {
  const results = data.results || []
  const errors = data.errors || []

  return (
    <section className="results-page">
      <header className="results-heading">
        <div>
          <div className="upload-kicker">SCORING RUN</div>
          <h1>Applicant results</h1>
          <p>{data.filename} · processed {data.processed_at ? new Date(data.processed_at).toLocaleString() : 'just now'}</p>
        </div>
        <button className="template-button" type="button" onClick={onBack}>Upload another file</button>
      </header>

      <div className="results-summary" aria-label="Upload summary">
        <div><span>Rows</span><strong>{data.total_rows}</strong></div>
        <div><span>Scored</span><strong>{data.processed}</strong></div>
        <div><span>Could not score</span><strong>{data.failed}</strong></div>
      </div>

      {results.length > 0 ? (
        <div className="results-table-wrap">
          <table className="results-table">
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Score</th>
                <th>Risk band</th>
                <th>Eligible products</th>
                <th><span className="visually-hidden">Details</span></th>
              </tr>
            </thead>
            <tbody>
              {results.map(result => {
                const eligibleCount = result.recommendations.filter(item => item.eligible).length
                return (
                  <tr key={`${result.row_number}-${result.user_id}`}>
                    <td>
                      <strong>{result.user_id}</strong>
                      <span className="table-secondary">Row {result.row_number}</span>
                    </td>
                    <td className="table-score">{result.score.total_score}</td>
                    <td>
                      <span className={`risk-pill risk-${result.score.risk_category.toLowerCase()}`}>
                        {result.score.risk_category}
                      </span>
                    </td>
                    <td>{eligibleCount} / {result.recommendations.length}</td>
                    <td>
                      <button className="row-action" type="button" onClick={() => onSelect(result)}>
                        View score
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="results-empty">
          <h2>No applicants were scored</h2>
          <p>Check the row errors below or try a different CSV file.</p>
        </div>
      )}

      {errors.length > 0 && (
        <section className="row-errors">
          <h2>Rows needing attention</h2>
          {errors.map(error => (
            <p key={`${error.row_number}-${error.user_id}`}>
              <strong>Row {error.row_number} · {error.user_id}:</strong> {error.error}
            </p>
          ))}
        </section>
      )}
    </section>
  )
}