// Consumer session (token + user id) kept in localStorage; authFetch adds the bearer header.
const KEY = 'altcredit.session'

export function loadSession() {
  try { return JSON.parse(localStorage.getItem(KEY)) } catch { return null }
}

export function saveSession(session) {
  try { localStorage.setItem(KEY, JSON.stringify(session)) } catch { /* private mode */ }
}

export function clearSession() {
  try { localStorage.removeItem(KEY) } catch { /* ignore */ }
}

export async function authFetch(url, session, options = {}, onUnauthorized) {
  const res = await fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), Authorization: `Bearer ${session.token}` },
  })
  if (res.status === 401 && onUnauthorized) onUnauthorized()
  return res
}

// Lender session: sessionStorage, so closing the tab signs the business user out.
const LENDER_KEY = 'altcredit_lender_token'
const LENDER_BANK_KEY = 'altcredit_lender_bank'

export function loadLenderToken() {
  try { return sessionStorage.getItem(LENDER_KEY) } catch { return null }
}

export function loadLenderBank() {
  try { return sessionStorage.getItem(LENDER_BANK_KEY) || '' } catch { return '' }
}

export function saveLenderSession(token, bankName) {
  try {
    if (token) { sessionStorage.setItem(LENDER_KEY, token); sessionStorage.setItem(LENDER_BANK_KEY, bankName || '') }
    else { sessionStorage.removeItem(LENDER_KEY); sessionStorage.removeItem(LENDER_BANK_KEY) }
  } catch { /* private mode */ }
}
