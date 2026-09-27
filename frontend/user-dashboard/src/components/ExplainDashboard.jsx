import { useEffect, useState } from 'react'

// "Why this score", in plain language: what helps, what hurts, what to do, and a second opinion.
// Everything comes from POST /xai as ready-made sentences.

function Item({ icon, tone, title, text, badge }) {
  return (
    <li className={`xai-item ${tone}`}>
      <span className="xai-icon">{icon}</span>
      <span className="xai-copy">
        {title && <strong>{title}</strong>}
        <span>{text}</span>
      </span>
      {badge && <span className="xai-badge">{badge}</span>}
    </li>
  )
}

function Card({ title, sub, children }) {
  return (
    <section className="detail-panel xai-card-box">
      <h2>{title}</h2>
      {sub && <p className="xai-sub">{sub}</p>}
      {children}
    </section>
  )
}

export default function ExplainDashboard({ features, apiBase }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    setData(null)
    setError(null)
    fetch(`${apiBase}/xai`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ features }),
    })
      .then(async res => {
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Could not load the explanation')
        if (alive) setData(body)
      })
      .catch(e => alive && setError(e.message))
    return () => { alive = false }
  }, [features, apiBase])

  if (error) return <div className="offer-error" role="alert">{error}</div>
  if (!data) return <p>Loading explanation…</p>

  const so = data.second_opinion

  return (
    <div className="xai">
      <p className="xai-headline">{data.headline}</p>

      <div className="detail-grid">
        <Card title="What is helping you" sub="These are working in your favour.">
          <ul className="xai-list">
            {data.helping.length === 0 && <li className="xai-empty">Nothing stands out yet. The actions below show where to start.</li>}
            {data.helping.map(h => <Item key={h.label} icon="✓" tone="good" title={h.label} text={h.text} />)}
          </ul>
        </Card>
        <Card title="What is holding you back" sub="Where you are losing points.">
          <ul className="xai-list">
            {data.holding_back.length === 0 && <li className="xai-empty">Nothing is costing you a meaningful number of points.</li>}
            {data.holding_back.map(h => <Item key={h.label} icon="!" tone="bad" title={h.label} text={h.text} badge={`-${h.points_lost} pts`} />)}
          </ul>
        </Card>
      </div>

      <Card title="What you can do" sub="Each change is worked out with the same rules used to score you, so the points are exact.">
        <ul className="xai-list">
          {data.actions.length === 0 && <li className="xai-empty">You are already at the top on the things you can change. Keep it up.</li>}
          {data.actions.map(a => <Item key={a.text} icon="↑" tone="good" text={a.text} badge={`+${a.points} pts`} />)}
        </ul>
        {data.watch_outs.length > 0 && (
          <>
            <h3 className="xai-h3">Be careful of</h3>
            <ul className="xai-list">
              {data.watch_outs.map(w => <Item key={w.text} icon="↓" tone="bad" text={w.text} badge={`${w.points} pts`} />)}
            </ul>
          </>
        )}
      </Card>

      {so && (
        <Card title="A second opinion">
          <p className={`xai-opinion ${so.verdict}`}>{so.text}</p>
          {so.drivers.length > 0 && (
            <ul className="xai-list">
              {so.drivers.map(d => <Item key={d.text} icon={d.direction === 'hurts' ? '!' : '✓'} tone={d.direction === 'hurts' ? 'bad' : 'good'} text={d.text} />)}
            </ul>
          )}
        </Card>
      )}

      <p className="xai-fair">🛡 {data.fairness}</p>
    </div>
  )
}
