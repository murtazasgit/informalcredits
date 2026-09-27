import { useState } from 'react'

// File picker shared by registration and "update my data".
// Two ways to provide data: one features CSV, or bank transactions + demographics.
// Parent gets the current selection through onChange({ mode, features, transactions, demographics }).

export function appendFiles(formData, sel) {
  if (sel.mode === 'csv') {
    if (sel.features) formData.append('features_csv', sel.features)
  } else {
    if (sel.transactions) formData.append('transactions', sel.transactions)
    if (sel.demographics) formData.append('demographics', sel.demographics)
  }
}

export function selectionComplete(sel) {
  return sel.mode === 'csv' ? !!sel.features : !!(sel.transactions && sel.demographics)
}

export const EMPTY_SELECTION = { mode: 'csv', features: null, transactions: null, demographics: null }

export default function DataFiles({ apiBase, value, onChange }) {
  const [templateError, setTemplateError] = useState(null)
  const set = (patch) => onChange({ ...value, ...patch })

  const downloadTemplate = async () => {
    setTemplateError(null)
    try {
      const res = await fetch(`${apiBase}/csv-template`)
      if (!res.ok) throw new Error('Could not load the CSV template.')
      const template = await res.json()
      const columns = Object.keys(template.sample_row)
      const csv = `${columns.join(',')}\n${columns.map(c => template.sample_row[c]).join(',')}\n`
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
      link.download = 'altcredit-template.csv'
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (e) {
      setTemplateError(e.message)
    }
  }

  return (
    <fieldset className="data-files" style={{ border: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <legend style={{ fontSize: 13, marginBottom: 8 }}>Your financial data</legend>
      <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
        <label><input type="radio" name="data-mode" checked={value.mode === 'csv'} onChange={() => set({ mode: 'csv' })} /> One CSV of features</label>
        <label><input type="radio" name="data-mode" checked={value.mode === 'raw'} onChange={() => set({ mode: 'raw' })} /> Bank transactions + demographics</label>
      </div>
      {value.mode === 'csv' ? (
        <>
          <label>Features CSV
            <input type="file" accept=".csv" onChange={e => set({ features: e.target.files[0] || null })} />
          </label>
          <button type="button" className="back-button" onClick={downloadTemplate}>Download CSV template</button>
        </>
      ) : (
        <>
          <label>Transactions (CSV or JSON)
            <input type="file" accept=".csv,.json" onChange={e => set({ transactions: e.target.files[0] || null })} />
          </label>
          <label>Demographics (JSON)
            <input type="file" accept=".json" onChange={e => set({ demographics: e.target.files[0] || null })} />
          </label>
          <span style={{ fontSize: 12 }}>
            Templates: <a href={`${apiBase}/upload-template/transactions.csv`}>transactions.csv</a>,{' '}
            <a href={`${apiBase}/upload-template/demographics.json`}>demographics.json</a>
          </span>
        </>
      )}
      {templateError && <div className="offer-error" role="alert">{templateError}</div>}
    </fieldset>
  )
}
