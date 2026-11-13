import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import App from './App'
import Login from './Login'
import { Theme } from './lib'
import './styles.css'

function readTheme(): Theme {
  const s = localStorage.getItem('marketmind.theme')
  if (s === 'dark' || s === 'light') return s
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function Root() {
  const [theme, setTheme] = useState<Theme>(readTheme)
  const [gate, setGate] = useState<'wait' | 'in' | 'out'>('wait')
  document.documentElement.dataset.theme = theme
  useEffect(() => { localStorage.setItem('marketmind.theme', theme) }, [theme])
  useEffect(() => {
    let on = true
    fetch('/api/auth/me').then(r => { if (on) setGate(r.ok ? 'in' : 'out') }).catch(() => { if (on) setGate('out') })
    return () => { on = false }
  }, [])
  if (gate === 'wait') return <div className="login-screen" aria-busy="true" />
  if (gate === 'out') return <Login theme={theme} onTheme={setTheme} onSuccess={() => setGate('in')} />
  return <App onSignOut={() => setGate('out')} />
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Root/></React.StrictMode>)
