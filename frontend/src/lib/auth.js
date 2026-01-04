import { api } from './api.js'
import { setTokens, clearTokens, getTokens } from './storage.js'

export async function login(username, password) {
  const res = await api.post('/auth/login', { username, password })
  setTokens(res.data)
  return res.data
}

export async function logout() {
  clearTokens()
}

export async function me() {
  const res = await api.get('/auth/me')
  return res.data
}

export function isLoggedIn() {
  const t = getTokens()
  return Boolean(t?.access_token && t?.refresh_token)
}
