import { useCallback, useEffect, useState } from 'react'
import LenderCandidateDetail from './LenderCandidateDetail'
import AuthScreen from '../components/AuthScreen'
import { loadLenderBank, loadLenderToken, saveLenderSession, saveSession } from '../auth'
import '../components/mvp.css'

const API = '/api'
const saveToken = (t) => saveLenderSession(t)

function Portal({ token, onLogout }) {
  const auth = { Authorization: `Bearer ${token}` }
  const [minScore, setMinScore] = useState(650)
  const [tier, setTier] = useState('')
  const [candidates, setCandidates] = useState([])
  const [offers, setOffers] = useState([])
  const [applications, setApplications] = useState([])
  const [products, setProducts] = useState([])
  const [productId, setProductId] = useState('')
  const [message, setMessage] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [notice, setNotice] = useState(null)
  const [contact, setContact] = useState({})
  const [inspect, setInspect] = useState(null)   // user_id being inspected

  const guarded = useCallback(async (path, options = {}) => {
    const res = await fetch(`${API}${path}`, { ...options, headers: { ...auth, ...(options.headers || {}) } })
    if (res.status === 401) { saveToken(null); onLogout(); throw new Error('Session expired') }
    return res
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    const q = new URLSearchParams({ min_score: minScore })
    if (tier) q.set('city_tier', tier)
    const [c, o, a] = await Promise.all([guarded(`/lender/candidates?${q}`), guarded('/lender/offers'), guarded('/lender/applications')])
    setCandidates(await c.json())
    const byUser = (x, y) => x.user_id.localeCompare(y.user_id)
    setOffers((await o.json()).sort(byUser))
    setApplications((await a.json()).sort(byUser))
    setSelected(new Set())
  }, [guarded, minScore, tier])

  useEffect(() => { load().catch(() => {}) }, [load])
  useEffect(() => {
    fetch(`${API}/products`).then(r => r.json()).then(p => { setProducts(p); setProductId(p[0]?.product_id || '') }).catch(() => {})
  }, [])

  const toggle = (id) => setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  const push = async () => {
    const res = await guarded('/lender/offers', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_ids: [...selected], product_id: productId, message }),
    })
    const data = await res.json()
    if (!res.ok) { setNotice(data.detail || 'Push failed'); return }
    const tally = data.results.reduce((a, r) => ({ ...a, [r.status]: (a[r.status] || 0) + 1 }), {})
    setNotice(Object.entries(tally).map(([k, v]) => `${v} ${k}`).join(', '))
    load()
  }

  const decide = async (id, decision) => {
    const note = decision === 'decline' ? (window.prompt('Reason for declining (optional):') ?? '') : ''
    const res = await guarded(`/lender/applications/${id}/decision`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, note }),
    })
    if (!res.ok) setNotice((await res.json().catch(() => ({}))).detail || 'Could not save the decision')
    load()
  }

  const reveal = async (ref) => {
    const res = await guarded(`/lender/candidates/${encodeURIComponent(ref)}`)
    const d = await res.json()
    setContact(c => ({ ...c, [ref]: d.contact || false }))
  }

  if (inspect) {
    return <LenderCandidateDetail userId={inspect} guarded={guarded} products={products} onBack={() => { setInspect(null); load().catch(() => {}) }} />
  }

  return (
    <section className="lender-page">
      <header className="detail-heading lender-header">
        <div>
          <div className="upload-kicker">LENDER PORTAL</div>
          <h1>Candidates</h1>
          <p>Click a user ID to see their full score analysis. Name, phone and address are released only after a candidate accepts your offer.</p>
        </div>
      </header>

      <section className="dash-card" style={{ margin: '20px 0' }}>
      <h2>Loan applications ({applications.length})</h2>
      <p>Borrowers who chose your bank on “Get loan approval”. Their contact details were given to you in the application.</p>
      {applications.length === 0 ? <p style={{ marginTop: 10 }}>No applications yet.</p> : (
        <table className="lender-table" style={{ marginTop: 14, boxShadow: 'none' }}>
          <thead><tr><th>#</th><th>Applicant</th><th>Contact</th><th>Score</th><th>Product</th><th>Amount</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {applications.map(a => (
              <tr key={a.application_id}>
                <td>{a.application_id}</td>
                <td><button type="button" className="lender-link" onClick={() => setInspect(a.user_id)}>{a.user_id}</button><div>{a.applicant_name}</div></td>
                <td>{a.phone}</td>
                <td>{a.current_score ?? a.score_at_submit}</td>
                <td>{a.product_name}</td>
                <td>₹{Number(a.requested_amount).toLocaleString()} / {a.tenure_months} mo{a.purpose ? <div>{a.purpose}</div> : null}</td>
                <td>{a.status}</td>
                <td>{a.status === 'submitted' && (
                  <span style={{ display: 'flex', gap: 8 }}>
                    <button type="button" className="offer-button" onClick={() => decide(a.application_id, 'approve')}>Approve</button>
                    <button type="button" className="back-button" onClick={() => decide(a.application_id, 'decline')}>Decline</button>
                  </span>)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </section>

      <div className="lender-filters detail-panel">
        <label>Minimum score
          <input type="number" min="0" max="1000" value={minScore} onChange={e => setMinScore(Number(e.target.value))} />
        </label>
        <label>City tier
          <select value={tier} onChange={e => setTier(e.target.value)}>
            <option value="">All</option><option value="tier-1">Tier 1</option><option value="tier-2">Tier 2</option><option value="tier-3">Tier 3</option>
          </select>
        </label>
        <span>{candidates.length} candidates</span>
      </div>

      <div className="lender-push detail-panel">
        <label>Product
          <select value={productId} onChange={e => setProductId(e.target.value)}>
            {products.map(p => <option key={p.product_id} value={p.product_id}>{p.name} ({p.interest_rate}%, min {p.min_score_required})</option>)}
          </select>
        </label>
        <label>Message<input value={message} onChange={e => setMessage(e.target.value)} placeholder="Optional note to the candidate" /></label>
        <button type="button" className="offer-button" disabled={!selected.size || !productId} onClick={push}>
          Push offer to {selected.size} selected
        </button>
        {notice && <span role="status">{notice}</span>}
      </div>

      <table className="lender-table">
        <thead><tr><th></th><th>User ID</th><th>Score</th><th>Risk</th><th>City tier</th><th>Offer</th><th>Contact</th></tr></thead>
        <tbody>
          {candidates.map(c => (
            <tr key={c.user_id}>
              <td><input type="checkbox" checked={selected.has(c.user_id)} onChange={() => toggle(c.user_id)} aria-label={`Select ${c.user_id}`} /></td>
              <td><button type="button" className="lender-link" onClick={() => setInspect(c.user_id)}>{c.user_id}</button></td>
              <td>{c.score}</td>
              <td><span className={`lender-tier ${c.risk_category}`}>{c.risk_category}</span></td>
              <td>{c.city_tier}</td>
              <td>{c.offer_status || '—'}</td>
              <td>
                {c.pii_unlocked
                  ? (contact[c.user_id]
                      ? <span>{contact[c.user_id].name} · {contact[c.user_id].phone} · {contact[c.user_id].address}</span>
                      : <button type="button" className="back-button" onClick={() => reveal(c.user_id)}>View</button>)
                  : <span className="lender-masked">Hidden until accepted</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginTop: 32 }}>Your offers ({offers.length})</h2>
      <table className="lender-table">
        <thead><tr><th>#</th><th>User ID</th><th>Product</th><th>Status</th><th>Sent</th></tr></thead>
        <tbody>
          {offers.map(o => (
            <tr key={o.offer_id}><td>{o.offer_id}</td><td><button type="button" className="lender-link" onClick={() => setInspect(o.user_id)}>{o.user_id}</button></td><td>{o.product_name}</td><td>{o.status}</td><td>{new Date(o.created_at).toLocaleString()}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

export default function LenderPortal() {
  const [token, setToken] = useState(loadLenderToken())
  const logout = () => { saveLenderSession(null); setToken(null) }
  if (!token) return <AuthScreen apiBase={API} initialRole="lender" onLenderAuth={setToken} onBorrowerAuth={(session) => { saveSession(session); window.location.hash = '#/' }} />
  const bank = loadLenderBank()
  return (
    <div className="app">
      <nav className="navbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span className="navbar-brand" aria-label="Lender portal">
          <span className="logo-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </span>
        </span>
        <div className="user-chip" title="Signed in">
          <span className="user-avatar">{(bank || 'L').slice(0, 1).toUpperCase()}</span>
          <span className="user-meta"><strong>{bank || 'Lender'}</strong><small>Lender</small></span>
        </div>
        </div>
        <button type="button" className="logout-btn" onClick={logout}>Log out</button>
      </nav>
      <main className="main-content">
        <Portal token={token} onLogout={() => setToken(null)} />
      </main>
    </div>
  )
}
