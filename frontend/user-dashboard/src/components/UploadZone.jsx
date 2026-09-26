import { useRef, useState } from 'react'

// Work out what an uploaded file is by looking inside it, not just at its name.
//   'transactions' | 'demographics' | 'features' (one-row-per-applicant feature CSV) | null
async function detectRole(file) {
  const name = file.name.toLowerCase()
  const text = await file.text()
  try {
    if (name.endsWith('.json')) {
      const data = JSON.parse(text)
      const rows = Array.isArray(data) ? data : data.transactions || data.users || data.demographics || []
      const first = rows[0] || {}
      if ('amount' in first || 'transaction_id' in first) return 'transactions'
      if ('user_id' in first) return 'demographics'
      return null
    }
    if (name.endsWith('.csv')) {
      const header = text.split(/\r?\n/, 1)[0].toLowerCase()
      return header.includes('transaction_id') || (header.includes('amount') && header.includes('category'))
        ? 'transactions'
        : 'features'
    }
  } catch { /* fall through */ }
  return null
}

const SLOTS = [
  { key: 'transactions', icon: '₹', title: 'Bank transactions', hint: 'CSV or JSON · date, amount, category, type, on-time flag' },
  { key: 'demographics', icon: '👤', title: 'Applicant profiles', hint: 'JSON · age, income, tier, employment, lifestyle' },
]

export default function UploadZone({ onUpload, onRawUpload, uploading, error, apiBase }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [files, setFiles] = useState({ transactions: null, demographics: null })
  const [message, setMessage] = useState(null)
  const [templateError, setTemplateError] = useState(null)

  async function handleFiles(fileList) {
    const picked = Array.from(fileList || [])
    if (!picked.length) return
    setMessage(null)
    const next = { ...files }
    for (const file of picked) {
      const role = await detectRole(file)
      if (role === 'features') {
        // a ready-made one-row-per-applicant feature CSV: score it straight away
        setFiles({ transactions: null, demographics: null })
        onUpload(file)
        return
      }
      if (!role) {
        setMessage(`"${file.name}" was not recognised. Use a transactions CSV/JSON and a demographics JSON.`)
        continue
      }
      next[role] = file
    }
    setFiles(next)
    if (next.transactions && next.demographics) {
      onRawUpload(next.transactions, next.demographics)   // both present: no extra click needed
    } else if (next.transactions || next.demographics) {
      setMessage(`Got ${next.transactions ? 'transactions' : 'applicant profiles'} — now add the ${next.transactions ? 'applicant profiles JSON' : 'bank transactions file'}.`)
    }
  }

  async function trySample() {
    setMessage(null)
    try {
      const [tx, demo] = await Promise.all([
        fetch(`${apiBase}/upload-template/transactions.csv`),
        fetch(`${apiBase}/upload-template/demographics.json`),
      ])
      if (!tx.ok || !demo.ok) throw new Error('Sample data is not available on the server.')
      const txFile = new File([await tx.blob()], 'transactions.csv', { type: 'text/csv' })
      const demoFile = new File([await demo.blob()], 'demographics.json', { type: 'application/json' })
      setFiles({ transactions: txFile, demographics: demoFile })
      onRawUpload(txFile, demoFile)
    } catch (e) {
      setMessage(e.message)
    }
  }

  async function downloadTemplate() {
    setTemplateError(null)
    try {
      const response = await fetch(`${apiBase}/csv-template`)
      if (!response.ok) throw new Error('Could not load the CSV template.')
      const template = await response.json()
      const columns = Object.keys(template.sample_row)
      const values = columns.map(column => template.sample_row[column])
      const blob = new Blob([`${columns.join(',')}\r\n${values.join(',')}\r\n`], { type: 'text/csv;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = 'altcredit-template.csv'
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (downloadError) {
      setTemplateError(downloadError.message)
    }
  }

  function handleDrop(event) {
    event.preventDefault()
    setDragging(false)
    handleFiles(event.dataTransfer.files)
  }

  const shownError = error || templateError

  return (
    <section className="upload-page">
      <header className="upload-heading">
        <div className="upload-kicker">ALTCREDIT / SCORING WORKSPACE</div>
        <h1>Assess a credit profile</h1>
        <p>Upload bank transactions and applicant profiles to get scores, the reasons behind them, and matching products.</p>
      </header>

      <div
        className={`hub ${dragging ? 'is-dragging' : ''} ${uploading ? 'is-busy' : ''}`}
        onDragEnter={event => { event.preventDefault(); setDragging(true) }}
        onDragOver={event => event.preventDefault()}
        onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false) }}
        onDrop={handleDrop}
        aria-busy={uploading}
      >
        {uploading && (
          <div className="hub-overlay" role="status">
            <div className="hub-spinner" aria-hidden="true" />
            <strong>Scoring applicants…</strong>
            <span>Building features, scoring and cross-checking with the ML model</span>
          </div>
        )}

        <div className="hub-slots">
          {SLOTS.map(slot => {
            const file = files[slot.key]
            return (
              <div key={slot.key} className={`hub-slot ${file ? 'is-filled' : ''}`}>
                <div className="hub-slot-icon" aria-hidden="true">{file ? '✓' : slot.icon}</div>
                <div>
                  <div className="hub-slot-title">{slot.title}</div>
                  <div className="hub-slot-hint">{file ? file.name : slot.hint}</div>
                </div>
              </div>
            )
          })}
        </div>

        <h2>Drag &amp; drop both files here</h2>
        <p>Drop them together or one at a time — each file is recognised automatically and scoring starts as soon as both are in.</p>

        <input
          ref={inputRef}
          className="upload-file-input"
          type="file"
          multiple
          accept=".csv,.json,text/csv,application/json"
          onChange={event => { handleFiles(event.target.files); event.target.value = '' }}
        />
        <div className="hub-actions">
          <button className="upload-button" type="button" disabled={uploading} onClick={() => inputRef.current?.click()}>
            Browse files
          </button>
          <button className="template-button" type="button" disabled={uploading} onClick={trySample}>
            ✨ Try with sample data
          </button>
        </div>
        <span className="upload-file-note">Sample: 30 applicants across tier-1, tier-2 and tier-3, from Poor to Excellent</span>
      </div>

      {message && <p className="hub-message" role="status">{message}</p>}
      {shownError && <p className="upload-error" role="alert">{shownError}</p>}

      <div className="upload-support-row">
        <div>
          <h2>Need the file formats?</h2>
          <p>
            Download the sample files:{' '}
            {['transactions.csv', 'transactions.json', 'demographics.json'].map(name => (
              <a key={name} href={`${apiBase}/upload-template/${name}`} download={name} style={{ marginRight: 12 }}>{name}</a>
            ))}
            <br />Already have one row of pre-computed features per applicant? Drop that CSV instead.
          </p>
        </div>
        <button className="template-button" type="button" onClick={downloadTemplate}>
          Download feature-CSV template
        </button>
      </div>
    </section>
  )
}
