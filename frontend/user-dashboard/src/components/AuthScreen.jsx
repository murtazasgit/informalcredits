import { useState } from 'react'
import DataFiles, { appendFiles, selectionComplete, EMPTY_SELECTION } from './DataFiles'
import { saveLenderSession } from '../auth'
import '../auth.css'

// Two-panel sign-in / create-account screen for both roles.
//   Borrower: user ID + password (+ CSV upload on registration, as before).
//   Lender:   bank name + username + password, so borrowers can apply to that bank from "Get loan approval".

async function postJson(url, body) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed')
  return data
}

function Field({ label, children }) {
  return <div className="au-field"><label>{label}</label>{children}</div>
}

function PasswordField({ label, value, onChange, ...rest }) {
  const [show, setShow] = useState(false)
  return (
    <Field label={label}>
      <div className="au-pw">
        <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)} required {...rest} />
        <button type="button" onClick={() => setShow(s => !s)} aria-label={show ? 'Hide password' : 'Show password'}>{show ? '🙈' : '👁'}</button>
      </div>
    </Field>
  )
}

function useSubmit() {
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const run = (fn) => async (e) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try { await fn() } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return { error, setError, busy, run }
}

function BorrowerSignIn({ apiBase, onBorrowerAuth }) {
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const { error, busy, run } = useSubmit()
  const submit = run(async () => {
    const d = await postJson(`${apiBase}/auth/login`, { user_id: userId.trim(), password })
    onBorrowerAuth({ token: d.token, userId: d.user_id })
  })
  return (
    <form className="au-form" onSubmit={submit}>
      <Field label="User ID"><input value={userId} onChange={e => setUserId(e.target.value)} autoComplete="username" required autoFocus /></Field>
      <PasswordField label="Password" value={password} onChange={setPassword} placeholder="••••••••" autoComplete="current-password" />
      {error && <div className="au-alert" role="alert">{error}</div>}
      <button className="au-btn" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
    </form>
  )
}

function BorrowerRegister({ apiBase, onBorrowerAuth }) {
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [files, setFiles] = useState(EMPTY_SELECTION)
  const [idProblem, setIdProblem] = useState(null)
  const { error, setError, busy, run } = useSubmit()

  const checkId = async () => {
    const id = userId.trim()
    if (!id) return
    try {
      const data = await (await fetch(`${apiBase}/auth/check-id?user_id=${encodeURIComponent(id)}`)).json()
      setIdProblem(data.available ? null : data.reason)
    } catch { /* the server re-checks on submit */ }
  }

  const submit = run(async () => {
    if (password !== confirm) throw new Error('Passwords do not match')
    if (!selectionComplete(files)) throw new Error('Please choose your data file(s) first')
    const body = new FormData()
    body.append('user_id', userId.trim())
    body.append('password', password)
    appendFiles(body, files)
    const res = await fetch(`${apiBase}/auth/register`, { method: 'POST', body })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Registration failed')
    onBorrowerAuth({ token: data.token, userId: data.user_id })
  })

  return (
    <form className="au-form" onSubmit={submit}>
      <Field label="User ID">
        <input value={userId} onChange={e => { setUserId(e.target.value); setIdProblem(null); setError(null) }} onBlur={checkId}
          placeholder="3–40 letters, digits, _ . -" autoComplete="username" required autoFocus />
      </Field>
      {idProblem && <div className="au-alert tight" role="alert">{idProblem}</div>}
      <PasswordField label="Password" value={password} onChange={setPassword} placeholder="At least 8 characters" autoComplete="new-password" minLength={8} />
      <PasswordField label="Confirm password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
      <DataFiles apiBase={apiBase} value={files} onChange={setFiles} />
      {error && <div className="au-alert" role="alert">{error}</div>}
      <button className="au-btn" disabled={busy || !!idProblem}>{busy ? 'Creating account…' : 'Create account'}</button>
    </form>
  )
}

function LenderSignIn({ apiBase, onLenderAuth }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { error, busy, run } = useSubmit()
  const submit = run(async () => {
    const d = await postJson(`${apiBase}/lender/login`, { username: username.trim(), password })
    saveLenderSession(d.token, d.bank_name)
    onLenderAuth(d.token)
  })
  return (
    <form className="au-form" onSubmit={submit}>
      <Field label="Username"><input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" required autoFocus /></Field>
      <PasswordField label="Password" value={password} onChange={setPassword} placeholder="••••••••" autoComplete="current-password" />
      {error && <div className="au-alert" role="alert">{error}</div>}
      <button className="au-btn" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to lender portal'}</button>
    </form>
  )
}

function LenderRegister({ apiBase, onLenderAuth }) {
  const [bankName, setBankName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const { error, busy, run } = useSubmit()
  const submit = run(async () => {
    if (password !== confirm) throw new Error('Passwords do not match')
    const d = await postJson(`${apiBase}/lender/register`, { bank_name: bankName.trim(), username: username.trim(), password })
    saveLenderSession(d.token, d.bank_name)
    onLenderAuth(d.token)
  })
  return (
    <form className="au-form" onSubmit={submit}>
      <Field label="Bank / lender name"><input value={bankName} onChange={e => setBankName(e.target.value)} placeholder="e.g. First National Bank" required autoFocus /></Field>
      <Field label="Username"><input value={username} onChange={e => setUsername(e.target.value)} placeholder="3–40 letters, digits, _ . -" autoComplete="username" required /></Field>
      <PasswordField label="Password" value={password} onChange={setPassword} placeholder="At least 8 characters" autoComplete="new-password" minLength={8} />
      <PasswordField label="Confirm password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
      {error && <div className="au-alert" role="alert">{error}</div>}
      <button className="au-btn" disabled={busy}>{busy ? 'Registering…' : 'Register lender'}</button>
    </form>
  )
}

const COPY = {
  user: {
    login: ['Welcome back', 'Sign in to view your credit score and offers.'],
    register: ['Create your account', 'Upload your data once and get your alternative credit score in minutes.'],
  },
  lender: {
    login: ['Lender sign-in', 'Review candidates, push offers and handle loan applications.'],
    register: ['Register your bank', 'Users will be able to choose your bank when they apply for a loan.'],
  },
}

export default function AuthScreen({ apiBase, onBorrowerAuth, onLenderAuth, initialRole = 'user' }) {
  const [tab, setTab] = useState('login')
  const [role, setRole] = useState(initialRole)
  const [title, sub] = COPY[role][tab]
  const props = { apiBase, onBorrowerAuth, onLenderAuth }
  const Form = { user: { login: BorrowerSignIn, register: BorrowerRegister }, lender: { login: LenderSignIn, register: LenderRegister } }[role][tab]

  return (
    <div className="au-layout">
      <div className="au-panel-right">
        <div className="au-card">
          <div className="au-tabs">
            <button type="button" className={`au-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => setTab('login')}>Sign in</button>
            <button type="button" className={`au-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => setTab('register')}>Create account</button>
          </div>
          <div className="au-title">{title}</div>
          <div className="au-sub">{sub}</div>

          <div className="au-segment" role="radiogroup" aria-label="Account type">
            {[['user', 'User'], ['lender', 'Lender']].map(([key, label]) => (
              <button type="button" role="radio" aria-checked={role === key} key={key}
                className={role === key ? 'selected' : ''} onClick={() => setRole(key)}>{label}</button>
            ))}
          </div>

          <Form key={`${role}-${tab}`} {...props} />

          <p className="au-foot">
            {tab === 'login'
              ? <>No account? <button type="button" onClick={() => setTab('register')}>Create one free</button></>
              : <>Already registered? <button type="button" onClick={() => setTab('login')}>Sign in</button></>}
          </p>
        </div>
      </div>
    </div>
  )
}
