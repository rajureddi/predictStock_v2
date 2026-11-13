import { FormEvent, useState } from 'react'
import { FallingLeaves } from 'falling-leaves/react'
import Snowfall from 'react-snowfall'
import { Leaf, LockKey, Snowflake } from '@phosphor-icons/react'
import { Theme, readFalling, writeFalling } from './lib'

const LEAF_COLORS = ['#FF5E1A', '#E04809', '#F59E0B', '#C2410C', '#FBBF24']

export default function Login({ theme, onTheme, onSuccess }: {
  theme: Theme
  onTheme: (t: Theme) => void
  onSuccess: () => void
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [falling, setFalling] = useState(readFalling)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(body.error || 'Those details do not match.')
        return
      }
      onSuccess()
    } catch {
      setError('The desk could not be reached.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-screen">
      {falling && (
        <>
          <FallingLeaves
            fullScreen
            shapes={['maple']}
            count={18}
            colors={LEAF_COLORS}
            zIndex={1}
            opacity={0.92}
          />
          <Snowfall
            snowflakeCount={80}
            color={theme === 'dark' ? '#F4F7FB' : '#FFFFFF'}
            style={{ position: 'fixed', width: '100vw', height: '100vh', zIndex: 1, pointerEvents: 'none' }}
          />
        </>
      )}

      <div className="login-tools">
        <button
          type="button"
          className={`login-fall${falling ? ' on' : ''}`}
          aria-pressed={falling}
          onClick={() => setFalling(v => { writeFalling(!v); return !v })}
        >
          <Leaf size={15} weight="fill" />
          <Snowflake size={15} weight="fill" />
          <span>{falling ? 'Falling on' : 'Falling off'}</span>
        </button>
        <button
          type="button"
          className="login-theme"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={() => onTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {theme === 'dark' ? 'Light' : 'Dark'}
        </button>
      </div>

      <form className="login-card" onSubmit={submit}>
        <span className="brand-mark" aria-hidden="true" />
        <p className="login-kicker">NSE + BSE · one login</p>
        <h1>Quant Trader</h1>
        <p className="login-sub">The desk stays closed until this sign-in. There is no registration.</p>

        <label>
          Username
          <input
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="login-error" role="alert">{error}</p>}
        <button className="login-submit" type="submit" disabled={busy}>
          <LockKey size={16} weight="bold" />
          {busy ? 'Checking…' : 'Enter the desk'}
        </button>
      </form>
    </div>
  )
}
