import React, { useState } from 'react'
import { login } from '../lib/auth.js'

export default function Login({ onLoggedIn }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      onLoggedIn()
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="card" style={{ maxWidth: 520, margin: '60px auto' }}>
        <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 10 }}>DevOps Control Plane</div>
        <div className="small" style={{ marginBottom: 18 }}>
          Sign in to manage tools and users (admin) or view tools (user).
        </div>

        <form onSubmit={submit}>
          <div style={{ marginBottom: 12 }}>
            <div className="label">Username</div>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>

          <div style={{ marginBottom: 12 }}>
            <div className="label">Password</div>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>

          {error ? <div style={{ color: '#fca5a5', marginBottom: 12 }}>{error}</div> : null}

          <button className="btn" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
