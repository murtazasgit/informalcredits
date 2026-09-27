import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import LenderPortal from './lender/LenderPortal.jsx'
import './index.css'
import './theme.css'

// Two separate modes behind one bundle: consumer app at "#/", lender portal at "#/lender".
function Root() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const onHash = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  return hash.startsWith('#/lender') ? <LenderPortal /> : <App />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
