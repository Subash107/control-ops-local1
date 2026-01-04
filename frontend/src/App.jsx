import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import { isLoggedIn } from './lib/auth.js'

function RequireAuth({ children }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const navigate = useNavigate()
  const [authed, setAuthed] = useState(isLoggedIn())

  function onLoggedIn() {
    setAuthed(true)
    navigate('/')
  }

  function onLoggedOut() {
    setAuthed(false)
    navigate('/login')
  }

  useEffect(() => {
    setAuthed(isLoggedIn())
  }, [])

  return (
    <Routes>
      <Route path="/login" element={<Login onLoggedIn={onLoggedIn} />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Dashboard onLoggedOut={onLoggedOut} />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to={authed ? '/' : '/login'} replace />} />
    </Routes>
  )
}
