import { useState, useRef, useCallback } from 'react'
import ScoreGauge from './components/ScoreGauge'
import FactorBreakdown from './components/FactorBreakdown'
import Recommendations from './components/Recommendations'
import UploadZone from './components/UploadZone'
import ResultsTable from './components/ResultsTable'
import ScoreDetail from './components/ScoreDetail'
import OffersInbox from './components/OffersInbox'
import AuthScreen from './components/AuthScreen'
import ApplyForm from './components/ApplyForm'
import MyApplications from './components/MyApplications'
import MyDashboard from './components/MyDashboard'
import { loadSession, saveSession, clearSession } from './auth'
import './components/mvp.css'

const API_BASE = '/api'

export default function App() {
  const [session, setSession] = useState(loadSession)
  const [mode, setMode] = useState('home') // 'home' | 'offers' | 'applications' | 'apply' | 'upload' | 'results' | 'detail'
  const [newOffers, setNewOffers] = useState(0)
  const [applyProduct, setApplyProduct] = useState(null)
  const [appliedNotice, setAppliedNotice] = useState(null)
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

  const handleRawUpload = useCallback(async (transactions, demographics) => {
    setUploading(true)
    setError(null)
    const formData = new FormData()
    formData.append('transactions', transactions)
    formData.append('demographics', demographics)
    try {
      const res = await fetch(`${API_BASE}/upload-raw`, { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
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

  const handleLogin = (s) => { saveSession(s); setSession(s); setMode('home') }
  const handleLogout = useCallback(() => {
    if (session) fetch(`${API_BASE}/auth/logout`, { method: 'POST', headers: { Authorization: `Bearer ${session.token}` } }).catch(() => {})
    clearSession()
    setSession(null)
    setNewOffers(0)
  }, [session])
  const handleUnauthorized = useCallback(() => { clearSession(); setSession(null) }, [])

  const handleReset = () => {
    setMode('upload')
    setUploadResult(null)
    setSelectedResult(null)
    setError(null)
  }

  if (!session) {
    return <AuthScreen apiBase={API_BASE} onBorrowerAuth={handleLogin} onLenderAuth={() => { window.location.hash = '#/lender' }} />
  }

  const startApply = (product) => { setApplyProduct(product); setAppliedNotice(null); setMode('apply') }

  return (
    <div className="app">
      {/* Navbar */}
      <nav className="navbar">
        <button className="navbar-brand" onClick={() => setMode('home')}>
          <div className="logo-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </button>
        <div className="nav-links">
          {[
            ['home', newOffers > 0 ? `My dashboard · ${newOffers} new` : 'My dashboard', () => setMode('home')],
            ['offers', 'My offers', () => setMode('offers')],
            ['applications', 'My applications', () => { setAppliedNotice(null); setMode('applications') }],
            ['upload', 'Score a file', handleReset],
          ].map(([key, label, go]) => {
            const active = mode === key || (key === 'upload' && (mode === 'results' || mode === 'detail')) || (key === 'home' && mode === 'apply')
            return <button key={key} type="button" className={`nav-btn ${active ? 'active' : ''}`} onClick={go}>{label}</button>
          })}
        </div>
        <div className="navbar-right">
          <div className="user-chip" title="Signed in">
            <span className="user-avatar">{session.userId.slice(0, 1).toUpperCase()}</span>
            <span className="user-meta"><strong>{session.userId}</strong><small>Borrower</small></span>
          </div>
          <button type="button" className="logout-btn" onClick={handleLogout}>Log out</button>
        </div>
      </nav>

      <main className="main-content">
        {mode === 'home' && <MyDashboard apiBase={API_BASE} session={session} onUnauthorized={handleUnauthorized} onCount={setNewOffers} onApply={startApply} />}
        {mode === 'offers' && <OffersInbox apiBase={API_BASE} session={session} onUnauthorized={handleUnauthorized} onCount={setNewOffers} />}
        {mode === 'applications' && <MyApplications apiBase={API_BASE} session={session} onUnauthorized={handleUnauthorized} notice={appliedNotice} />}
        {mode === 'apply' && applyProduct && (
          <ApplyForm apiBase={API_BASE} session={session} product={applyProduct} onUnauthorized={handleUnauthorized}
            onCancel={() => setMode('home')}
            onDone={(a) => { setAppliedNotice(`Application sent to ${a.bank_name}. You'll see their decision here.`); setMode('applications') }} />
        )}
        {mode === 'upload' && (
          <UploadZone onUpload={handleUpload} onRawUpload={handleRawUpload} uploading={uploading} error={error} apiBase={API_BASE} />
        )}
        {mode === 'results' && uploadResult && (
          <ResultsTable data={uploadResult} onSelect={handleSelectResult} onBack={handleReset} />
        )}
        {mode === 'detail' && selectedResult && (
          <ScoreDetail result={selectedResult} onBack={() => setMode('results')} apiBase={API_BASE} />
        )}
      </main>
    </div>
  )
}