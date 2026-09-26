import { useState, useRef, useCallback } from 'react'
import ScoreGauge from './components/ScoreGauge'
import FactorBreakdown from './components/FactorBreakdown'
import Recommendations from './components/Recommendations'
import UploadZone from './components/UploadZone'
import ResultsTable from './components/ResultsTable'
import ScoreDetail from './components/ScoreDetail'
import './components/mvp.css'

const API_BASE = '/api'

export default function App() {
  const [mode, setMode] = useState('upload') // 'upload' | 'results' | 'detail'
  const [uploadResult, setUploadResult] = useState(null)
  const [selectedResult, setSelectedResult] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)

  const handleUpload = useCallback(async (file) => {
    setUploading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`${API_BASE}/upload-csv`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
      const data = await res.json()
      setUploadResult(data)
      setMode('results')
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }, [])

  const handleSelectResult = (result) => {
    setSelectedResult(result)
    setMode('detail')
  }

  const handleReset = () => {
    setMode('upload')
    setUploadResult(null)
    setSelectedResult(null)
    setError(null)
  }

  return (
    <div className="app">
      {/* Navbar */}
      <nav className="navbar">
        <button className="navbar-brand" onClick={handleReset}>
          <div className="logo-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span>AltCredit</span>
        </button>
        <div className="navbar-center">
          <div className="breadcrumb">
            <span className={`breadcrumb-item ${mode === 'upload' ? 'active' : 'done'}`} onClick={handleReset}>
              Upload
            </span>
            {(mode === 'results' || mode === 'detail') && (
              <>
                <span className="breadcrumb-sep">›</span>
                <span className={`breadcrumb-item ${mode === 'results' ? 'active' : mode === 'detail' ? 'done' : ''}`}
                  onClick={() => mode === 'detail' && setMode('results')}>
                  Results ({uploadResult?.processed ?? 0})
                </span>
              </>
            )}
            {mode === 'detail' && (
              <>
                <span className="breadcrumb-sep">›</span>
                <span className="breadcrumb-item active">Score Detail</span>
              </>
            )}
          </div>
        </div>
        <div className="navbar-right">
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="api-badge">
            API Docs
          </a>
        </div>
      </nav>

      <main className="main-content">
        {mode === 'upload' && (
          <UploadZone onUpload={handleUpload} uploading={uploading} error={error} apiBase={API_BASE} />
        )}
        {mode === 'results' && uploadResult && (
          <ResultsTable data={uploadResult} onSelect={handleSelectResult} onBack={handleReset} />
        )}
        {mode === 'detail' && selectedResult && (
          <ScoreDetail result={selectedResult} onBack={() => setMode('results')} />
        )}
      </main>
    </div>
  )
}
