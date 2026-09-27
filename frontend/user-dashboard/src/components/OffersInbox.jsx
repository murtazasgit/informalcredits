import { useCallback, useEffect, useState } from 'react'
import { authFetch } from '../auth'

const STATUS_LABEL = { pushed: 'New offer', accepted: 'Accepted', rejected: 'Declined' }
const POLL_MS = 10000   // new lender pushes show up without a manual refresh

export default function OffersInbox({ apiBase, session, onUnauthorized, onCount, compact }) {
  const [offers, setOffers] = useState(null)
  const [error, setError] = useState(null)
  const base = `${apiBase}/users/${encodeURIComponent(session.userId)}/offers`

  const load = useCallback(async () => {
    const res = await authFetch(base, session, {}, onUnauthorized)
    if (!res.ok) { setError((await res.json().catch(() => ({}))).detail || 'Could not load offers'); return }
    setError(null)
    const data = await res.json()
    setOffers(data)
    onCount?.(data.filter(o => o.status === 'pushed').length)
  }, [base, session, onUnauthorized, onCount])

  useEffect(() => {
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  const respond = async (offerId, action) => {
    const res = await authFetch(`${base}/${offerId}/respond`, session, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    }, onUnauthorized)
    if (!res.ok) setError((await res.json().catch(() => ({}))).detail || 'Could not respond')
    load()
  }

  return (
    <section className={compact ? 'dash-card' : 'detail-page'}>
      {compact ? (
        <div className="dash-card-head">
          <div>
            <h2>Offers from lenders{offers?.length ? ` (${offers.length})` : ''}</h2>
            <p>Lenders only see an anonymous reference until you accept an offer.</p>
          </div>
        </div>
      ) : (<>
        <div className="upload-kicker">YOUR OFFERS</div>
        <h1>Offers from lenders</h1>
        <p>Lenders only see an anonymous reference until you accept an offer.</p>
      </>)}
      {error && <div className="offer-error" role="alert">{error}</div>}
      {offers && offers.length === 0 && <p>No offers yet. New ones will appear here automatically.</p>}
      <div className="recommendations-grid">
        {(offers || []).map(o => (
          <div key={o.offer_id} className="product-card eligible">
            <span className="eligibility-tag eligible">{STATUS_LABEL[o.status] || o.status}</span>
            <div className="product-name">{o.product_name}</div>
            {o.bank_name && <div className="product-reason">from {o.bank_name}</div>}
            <div className="product-rate">{o.interest_rate}%<span> p.a.</span></div>
            {o.message && <div className="product-reason">{o.message}</div>}
            {o.status === 'pushed' && (
              <div className="offer-actions">
                <button type="button" className="offer-button" onClick={() => respond(o.offer_id, 'accept')}>Accept</button>
                <button type="button" className="back-button" onClick={() => respond(o.offer_id, 'reject')}>Decline</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
