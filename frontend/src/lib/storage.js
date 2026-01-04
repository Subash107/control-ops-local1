const KEY = 'dcp_tokens'

export function getTokens() {
  try { return JSON.parse(localStorage.getItem(KEY)) || null } catch { return null }
}

export function setTokens(tokens) {
  localStorage.setItem(KEY, JSON.stringify(tokens))
}

export function clearTokens() {
  localStorage.removeItem(KEY)
}
