import React, { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import Modal from '../components/Modal.jsx'

export default function Users() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/admin/users')
      setUsers(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function openCreate() {
    setModal({ mode: 'create', user: { username: '', password: '', role: 'user' } })
  }

  function openEdit(u) {
    setModal({ mode: 'edit', user: { id: u.id, username: u.username, password: '', role: u.role } })
  }

  async function save() {
    const { mode, user } = modal
    if (mode === 'create') {
      await api.post('/admin/users', user)
    } else {
      await api.put(`/admin/users/${user.id}`, { password: user.password || null, role: user.role })
    }
    setModal(null)
    await load()
  }

  async function remove(u) {
    if (!confirm(`Delete user "${u.username}"?`)) return
    await api.delete(`/admin/users/${u.id}`)
    await load()
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 18 }}>User Management</div>
          <div className="small">Admin-only. Create users and set roles.</div>
        </div>
        <button className="btn" onClick={openCreate}>New User</button>
      </div>

      {error ? <div style={{ color: '#fca5a5', marginTop: 12 }}>{error}</div> : null}
      {loading ? <div style={{ marginTop: 12 }}>Loading...</div> : null}

      {!loading ? (
        <div style={{ marginTop: 12, overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 260 }}>Username</th>
                <th style={{ width: 160 }}>Role</th>
                <th style={{ width: 200 }} />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td><strong>{u.username}</strong></td>
                  <td><span className="badge">{u.role}</span></td>
                  <td>
                    <div className="row">
                      <button className="btn secondary" onClick={() => openEdit(u)}>Edit</button>
                      <button className="btn danger" onClick={() => remove(u)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 ? (
                <tr>
                  <td colSpan={3} className="small">No users yet.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}

      {modal ? (
        <Modal title={modal.mode === 'create' ? 'Create User' : 'Edit User'} onClose={() => setModal(null)}>
          <div style={{ marginBottom: 10 }}>
            <div className="label">Username</div>
            <input className="input" disabled={modal.mode === 'edit'} value={modal.user.username}
              onChange={(e) => setModal({ ...modal, user: { ...modal.user, username: e.target.value } })} />
          </div>

          <div style={{ marginBottom: 10 }}>
            <div className="label">{modal.mode === 'create' ? 'Password' : 'New Password (optional)'}</div>
            <input className="input" type="password" value={modal.user.password}
              onChange={(e) => setModal({ ...modal, user: { ...modal.user, password: e.target.value } })} />
          </div>

          <div style={{ marginBottom: 10 }}>
            <div className="label">Role</div>
            <select className="input" value={modal.user.role}
              onChange={(e) => setModal({ ...modal, user: { ...modal.user, role: e.target.value } })}>
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          </div>

          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn" onClick={save}>Save</button>
          </div>
        </Modal>
      ) : null}
    </div>
  )
}
