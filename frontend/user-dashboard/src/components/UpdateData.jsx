import { useState } from 'react'
import { authFetch } from '../auth'
import DataFiles, { appendFiles, selectionComplete, EMPTY_SELECTION } from './DataFiles'

// "Update my data": upload newer files, get re-scored, and see the change.
export default function UpdateData({ apiBase, session, onUnauthorized, onUpdated }) {
  const [open, setOpen] = useState(false)
  const [files, setFiles] = useState(EMPTY_SELECTION)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setNotice(null)
    if (!selectionComplete(files)) { setError('Please choose your data file(s) first'); return }
    setBusy(true)
    try {
      const body = new FormData()
      appendFiles(body, files)
      const res = await authFetch(`${apiBase}/me/data`, session, { method: 'POST', body }, onUnauthorized)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Update failed')
      const now = data.score.total_score
      const prev = data.previous_score
      setNotice(prev == null || prev === now
        ? `Your score is ${now}.`
        : `Your score changed from ${prev} to ${now} (${now > prev ? '+' : ''}${now - prev}).`)
      setFiles(EMPTY_SELECTION)
      setOpen(false)
      onUpdated(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="dash-card">
      <div className="dash-card-head">
        <div>
          <h2>Keep your score current</h2>
          <p>Upload newer data and we re-compute your score.</p>
        </div>
        {!open && <button type="button" className="offer-button" onClick={() => setOpen(true)}>Update my data</button>}
      </div>
      {notice && <div className="offer-result pre_approved" role="status">{notice}</div>}
      {open && (
        <form className="lender-login" onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 'none', margin: '16px 0 0' }}>
          <p>Upload your latest data. It replaces what we have and re-computes your score.</p>
          <DataFiles apiBase={apiBase} value={files} onChange={setFiles} />
          {error && <div className="offer-error" role="alert">{error}</div>}
          <div className="offer-actions">
            <button type="submit" className="offer-button" disabled={busy}>{busy ? 'Scoring…' : 'Upload and re-score'}</button>
            <button type="button" className="back-button" onClick={() => { setOpen(false); setError(null) }}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  )
}
