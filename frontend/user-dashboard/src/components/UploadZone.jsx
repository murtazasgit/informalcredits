import { useRef, useState } from 'react'

export default function UploadZone({ onUpload, uploading, error, apiBase }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [templateError, setTemplateError] = useState(null)
  const [fileError, setFileError] = useState(null)

  function chooseFile(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setFileError('Choose a CSV file.')
      return
    }
    setFileError(null)
    onUpload(file)
  }

  async function downloadTemplate() {
    setTemplateError(null)
    try {
      const response = await fetch(`${apiBase}/csv-template`)
      if (!response.ok) throw new Error('Could not load the CSV template.')
      const template = await response.json()
      const columns = Object.keys(template.sample_row)
      const values = columns.map(column => template.sample_row[column])
      const blob = new Blob([`${columns.join(',')}\r\n${values.join(',')}\r\n`], {
        type: 'text/csv;charset=utf-8',
      })
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
    chooseFile(event.dataTransfer.files[0])
  }

  return (
    <section className="upload-page">
      <header className="upload-heading">
        <div className="upload-kicker">ALTCREDIT / SCORING WORKSPACE</div>
        <h1>Assess a credit profile</h1>
        <p>Upload applicant data to calculate scores, understand their drivers, and review eligible products.</p>
      </header>

      <div
        className={`upload-dropzone ${dragging ? 'is-dragging' : ''}`}
        onDragEnter={event => { event.preventDefault(); setDragging(true) }}
        onDragOver={event => event.preventDefault()}
        onDragLeave={event => {
          if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false)
        }}
        onDrop={handleDrop}
        aria-busy={uploading}
      >
        <input
          ref={inputRef}
          className="upload-file-input"
          type="file"
          accept=".csv,text/csv"
          onChange={event => {
            chooseFile(event.target.files[0])
            event.target.value = ''
          }}
        />
        <div className="upload-mark" aria-hidden="true">CSV</div>
        <h2>{uploading ? 'Scoring applicants...' : 'Drop a CSV file here'}</h2>
        <p>One applicant per row. Your file is processed for scoring and is not stored.</p>
        <button
          className="upload-button"
          type="button"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? 'Processing' : 'Choose CSV'}
        </button>
        <span className="upload-file-note">CSV files only</span>
      </div>

      {(error || templateError || fileError) && (
        <p className="upload-error" role="alert">{error || templateError || fileError}</p>
      )}

      <div className="upload-support-row">
        <div>
          <h2>Need a starting point?</h2>
          <p>Download a sample row with the supported column names.</p>
        </div>
        <button className="template-button" type="button" onClick={downloadTemplate}>
          Download CSV template
        </button>
      </div>
    </section>
  )
}