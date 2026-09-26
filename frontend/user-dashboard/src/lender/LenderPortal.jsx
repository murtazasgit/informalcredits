import { useCallback, useEffect, useState } from 'react'
import LenderCandidateDetail from './LenderCandidateDetail'
import '../components/mvp.css'

const API = '/api'
const TOKEN_KEY = 'altcredit_lender_token'

const readToken = () => { try { return sessionStorage.getItem(TOKEN_KEY) } catch { return null } }
const saveToken = (t) => { try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ } }

function Login({ onLoggedIn }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    const res = await fetch(`${API}/lender/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.trim(), password: password.trim() }),
    })
    if (!res.ok) { setError('Invalid credentials'); return }
    const { token } = await res.json()
    saveToken(token)
    onLoggedIn(token)
  }

  return (
    <form className="lender-login detail-panel" onSubmit={submit}>
      <div className="upload-kicker">LENDER PORTAL</div>
      <h1>Business sign-in</h1>
      <label>Username<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" required /></label>
      <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required /></label>
      {error && <div className="offer-error" role="alert">{error}</div>}
      <button type="submit" className="offer-button">Sign in</button>
    </form>
  )
}

function Portal({ token, onLogout }) {
  const auth = { Authorization: `Bearer ${token}` }
  const [minScore, setMinScore] = useState(650)
  const [tier, setTier] = useState('')
  const [candidates, setCandidates] = useState([])
  const [offers, setOffers] = useState([])
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
    const [c, o] = await Promise.all([guarded(`/lender/candidates?${q}`), guarded('/lender/offers')])
    setCandidates(await c.json())
    setOffers(await o.json())
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
        <button className="back-button" type="button" onClick={() => { saveToken(null); onLogout() }}>Sign out</button>
      </header>

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
  const [token, setToken] = useState(readToken())
  return (
    <div className="app">
      <nav className="navbar">
        <a className="navbar-brand" href="#/"><span>AltCredit</span></a>
        <div className="navbar-center"><span className="breadcrumb-item active">Lender portal</span></div>
        <div className="navbar-right"><a className="api-badge" href="#/">Consumer app</a></div>
      </nav>
      <main className="main-content">
        {token ? <Portal token={token} onLogout={() => setToken(null)} /> : <Login onLoggedIn={setToken} />}
      </main>
    </div>
  )
}
