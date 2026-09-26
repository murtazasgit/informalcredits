import { useState } from 'react'

const STATUS_LABEL = { pushed: 'New offer', accepted: 'Accepted', rejected: 'Declined' }

export default function OffersInbox({ apiBase }) {
  const [userId, setUserId] = useState('')
  const [offers, setOffers] = useState(null)
  const [error, setError] = useState(null)

  const load = async (id = userId) => {
    setError(null)
    const res = await fetch(`${apiBase}/users/${encodeURIComponent(id.trim())}/offers`)
    if (!res.ok) { setOffers(null); setError((await res.json()).detail || 'Could not load offers'); return }
    setOffers(await res.json())
  }

  const respond = async (offerId, action) => {
    const res = await fetch(`${apiBase}/users/${encodeURIComponent(userId.trim())}/offers/${offerId}/respond`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    })
    if (!res.ok) setError((await res.json()).detail || 'Could not respond')
    load()
  }

  return (
    <section className="detail-page">
      <div className="upload-kicker">YOUR OFFERS</div>
      <h1>Offers from lenders</h1>
      <p>Lenders only see an anonymous reference until you accept an offer.</p>
      <form className="lender-filters detail-panel" onSubmit={e => { e.preventDefault(); load() }}>
        <label>Your applicant ID
          <input value={userId} onChange={e => setUserId(e.target.value)} placeholder="e.g. USR_001" required />
        </label>
        <button type="submit" className="offer-button">Show my offers</button>
      </form>
      {error && <div className="offer-error" role="alert">{error}</div>}
      {offers && offers.length === 0 && <p>No offers yet.</p>}
      <div className="recommendations-grid">
        {(offers || []).map(o => (
          <div key={o.offer_id} className="product-card eligible">
            <span className="eligibility-tag eligible">{STATUS_LABEL[o.status] || o.status}</span>
            <div className="product-name">{o.product_name}</div>
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
