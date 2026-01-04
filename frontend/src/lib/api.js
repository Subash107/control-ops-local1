import axios from 'axios'
import { getTokens, setTokens, clearTokens } from './storage.js'

const apiBase = import.meta.env.VITE_API_BASE || '/api'

export const api = axios.create({
  baseURL: apiBase,
  timeout: 15000
})

let refreshingPromise = null

api.interceptors.request.use((config) => {
  const tokens = getTokens()
  if (tokens?.access_token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${tokens.access_token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    if (status !== 401 || original?._retry) {
      return Promise.reject(error)
    }

    const tokens = getTokens()
    if (!tokens?.refresh_token) {
      clearTokens()
      return Promise.reject(error)
    }

    original._retry = true

    try {
      refreshingPromise = refreshingPromise || api.post('/auth/refresh', { refresh_token: tokens.refresh_token })
      const res = await refreshingPromise
      refreshingPromise = null
      setTokens(res.data)
      original.headers = original.headers || {}
      original.headers.Authorization = `Bearer ${res.data.access_token}`
      return api(original)
    } catch (e) {
      refreshingPromise = null
      clearTokens()
      return Promise.reject(e)
    }
  }
)
