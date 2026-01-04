import React, { useEffect, useState } from 'react'
import Tools from './Tools.jsx'
import Users from './Users.jsx'
import { me, logout } from '../lib/auth.js'

export default function Dashboard({ onLoggedOut }) {
  const [user, setUser] = useState(null)
  const [tab, setTab] = useState('tools')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoading(true)
      setError('')
      try {
        const u = await me()
        if (mounted) setUser(u)
      } catch (e) {
        setError('Session expired. Please sign in again.')
        onLoggedOut()
      } finally {
        if (mounted) setLoading(false)
      }
    }
    load()
    return () => { mounted = false }
  }, [onLoggedOut])

  async function doLogout() {
    await logout()
    onLoggedOut()
  }

  const isAdmin = user?.role === 'admin'

  return (
    <div className="container">
      <div className="nav">
        <div>
          <div className="brand">DevOps Control Plane</div>
          <div className="small">
            {user ? (
              <>
                Signed in as <strong>{user.username}</strong> <span className="badge">{user.role}</span>
              </>
            ) : null}
          </div>
        </div>
        <button className="btn secondary" onClick={doLogout}>Sign out</button>
      </div>

      {loading ? <div className="card">Loading...</div> : null}
      {error ? <div className="card" style={{ borderColor: 'rgba(252,165,165,0.5)' }}>{error}</div> : null}

      {!loading && user ? (
        <>
          <div className="tabs" style={{ marginBottom: 12 }}>
            <div className={`tab ${tab === 'tools' ? 'active' : ''}`} onClick={() => setTab('tools')}>Tools</div>
            {isAdmin ? (
              <div className={`tab ${tab === 'users' ? 'active' : ''}`} onClick={() => setTab('users')}>Users</div>
            ) : null}
          </div>

          {tab === 'tools' ? <Tools isAdmin={isAdmin} /> : null}
          {tab === 'users' && isAdmin ? <Users /> : null}
        </>
      ) : null}
    </div>
  )
}
