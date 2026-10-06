const API_PREFIX = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  })

  if (!response.ok) {
    let message = ''
    try {
      const payload = await response.json()
      message = payload.detail
    } catch {
      message = await response.text()
    }
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

export function createNav(data) {
  return request('/nav', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateNav(id, data) {
  return request(`/nav/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function deleteNav(id) {
  return request(`/nav/${id}`, {
    method: 'DELETE',
  })
}
