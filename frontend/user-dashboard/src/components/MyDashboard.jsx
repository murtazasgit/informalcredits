import { useEffect, useState } from 'react'
import { authFetch } from '../auth'
import ScoreDetail from './ScoreDetail'
import OffersInbox from './OffersInbox'
import UpdateData from './UpdateData'

// The logged-in user's home: lender offers on top, then their own score analysis.
export default function MyDashboard({ apiBase, session, onUnauthorized, onCount, onApply }) {
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    authFetch(`${apiBase}/me/dashboard`, session, {}, onUnauthorized)
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.detail || 'Could not load your dashboard')
        if (alive) setResult(data)
      })
      .catch(e => alive && setError(e.message))
    return () => { alive = false }
  }, [apiBase, session, onUnauthorized])

  const top = (
    <div className="dash-top">
      <OffersInbox compact apiBase={apiBase} session={session} onUnauthorized={onUnauthorized} onCount={onCount} />
      <UpdateData apiBase={apiBase} session={session} onUnauthorized={onUnauthorized} onUpdated={setResult} />
    </div>
  )

  return (
    <>
      {error && <div className="offer-error" role="alert">{error}</div>}
      {result && <ScoreDetail result={result} apiBase={apiBase} onApply={onApply} afterHero={top} />}
    </>
  )
}
