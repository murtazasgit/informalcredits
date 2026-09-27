import { useEffect, useState } from 'react'
import { authFetch } from '../auth'

// Loan application to one registered lender for the product the borrower clicked "Get loan approval" on.
export default function ApplyForm({ apiBase, session, product, onUnauthorized, onDone, onCancel }) {
  const [lenders, setLenders] = useState(null)
  const [lenderId, setLenderId] = useState('')
  const [amount, setAmount] = useState('')
  const [tenure, setTenure] = useState('12')
  const [purpose, setPurpose] = useState('')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetch(`${apiBase}/lenders`).then(r => r.json()).then(list => {
      setLenders(list)
      setLenderId(list[0]?.lender_id || '')
    }).catch(() => setError('Could not load the list of lenders'))
  }, [apiBase])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = await authFetch(`${apiBase}/users/${encodeURIComponent(session.userId)}/applications`, session, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lender_id: lenderId, product_id: product.product_id, requested_amount: Number(amount),
          tenure_months: Number(tenure), purpose, full_name: fullName, phone,
        }),
      }, onUnauthorized)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not submit the application')
      onDone(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="detail-page" style={{ maxWidth: 560 }}>
      <button className="back-button" type="button" onClick={onCancel}>Back</button>
      <div className="upload-kicker">LOAN APPROVAL APPLICATION</div>
      <h1>{product.name}</h1>
      <p>{product.interest_rate}% p.a. · Choose the bank you want to apply with. Your name and phone are shared only with that bank.</p>

      <form className="lender-login detail-panel" onSubmit={submit} style={{ maxWidth: 'none', margin: '16px 0 0' }}>
        <label>Apply to
          <select value={lenderId} onChange={e => setLenderId(e.target.value)} required disabled={!lenders?.length}>
            {(lenders || []).map(l => <option key={l.lender_id} value={l.lender_id}>{l.bank_name}</option>)}
          </select>
        </label>
        {lenders && lenders.length === 0 && <div className="offer-error">No lenders have registered yet.</div>}
        <label>Amount needed (₹)<input type="number" min="1" value={amount} onChange={e => setAmount(e.target.value)} required /></label>
        <label>Tenure (months)<input type="number" min="1" max="360" value={tenure} onChange={e => setTenure(e.target.value)} required /></label>
        <label>Purpose<input value={purpose} onChange={e => setPurpose(e.target.value)} placeholder="Optional" /></label>
        <label>Full name<input value={fullName} onChange={e => setFullName(e.target.value)} autoComplete="name" required /></label>
        <label>Phone<input type="tel" value={phone} onChange={e => setPhone(e.target.value)} autoComplete="tel" required /></label>
        {error && <div className="offer-error" role="alert">{error}</div>}
        <button type="submit" className="offer-button" disabled={busy || !lenderId}>{busy ? 'Submitting…' : 'Submit application'}</button>
      </form>
    </section>
  )
}
