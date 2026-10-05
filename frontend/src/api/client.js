const API_PREFIX = '/api'

async function request(path) {
  const response = await fetch(`${API_PREFIX}${path}`)

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed with ${response.status}`)
  }

  return response.json()
}

export function getHealth() {
  return request('/health')
}

export function getNav() {
  return request('/nav')
}
