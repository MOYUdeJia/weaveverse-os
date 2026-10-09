const API_PREFIX = '/api'

// 把后端 {field, message} 或旧字符串 detail 转成可读错误。
// Turn a {field, message} body or a legacy string detail into a readable error.
function formatDetail(detail) {
  if (!detail) {
    return ''
  }
  if (typeof detail === 'string') {
    return detail
  }
  if (detail.field && detail.message) {
    return `${detail.field}: ${detail.message}`
  }
  return detail.message || JSON.stringify(detail)
}

// 发起 /api 请求，JSON 默认，FormData 不强制 Content-Type。
// Send an /api request; JSON by default, FormData without a forced Content-Type.
async function request(path, options = {}) {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers ?? {}),
  }

  const response = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = ''
    try {
      const payload = await response.json()
      message = formatDetail(payload.detail)
    } catch {
      message = await response.text()
    }
    throw new Error(message || `Request failed with ${response.status}`)
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export function getHealth() {
  return request('/health')
}

export function getPageTypes() {
  return request('/page-types')
}

export function getTemplates() {
  return request('/templates')
}

export function getGroups() {
  return request('/groups')
}

export function createGroup(data) {
  return request('/groups', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateGroup(id, data) {
  return request(`/groups/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteGroup(id) {
  return request(`/groups/${id}`, {
    method: 'DELETE',
  })
}

export function reorderGroups(ids) {
  return request('/groups/reorder', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}

export function getNav(groupId) {
  const query = groupId == null ? '' : `?group_id=${encodeURIComponent(groupId)}`
  return request(`/nav${query}`)
}

export function getNavItem(id) {
  return request(`/nav/${id}`)
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

export function patchNav(id, data) {
  return request(`/nav/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function pinNav(id) {
  return request(`/nav/${id}/pin`, {
    method: 'PATCH',
  })
}

export function lockNav(id) {
  return request(`/nav/${id}/lock`, {
    method: 'PATCH',
  })
}

export function lockGroup(id) {
  return request(`/groups/${id}/lock`, {
    method: 'PATCH',
  })
}

export function deleteNav(id) {
  return request(`/nav/${id}`, {
    method: 'DELETE',
  })
}

export function reorderNav(ids) {
  return request('/nav/reorder', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}

export function createBlock(navId, payload) {
  return request(`/nav/${navId}/blocks`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateBlock(blockId, payload) {
  return request(`/blocks/${blockId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteBlock(blockId) {
  return request(`/blocks/${blockId}`, {
    method: 'DELETE',
  })
}

export function uploadImage(blockId, file) {
  const body = new FormData()
  body.append('file', file)
  return request(`/blocks/${blockId}/images`, {
    method: 'POST',
    body,
  })
}

export function uploadFile(blockId, file) {
  const body = new FormData()
  body.append('file', file)
  return request(`/blocks/${blockId}/files`, {
    method: 'POST',
    body,
  })
}

export function deleteAttachment(filename) {
  return request(`/attachments/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  })
}

export function attachmentUrl(filename) {
  return `${API_PREFIX}/attachments/${encodeURIComponent(filename)}`
}

export function listBooks(sort = 'recent', format = '') {
  const params = new URLSearchParams({ sort })
  if (format) {
    params.set('format', format)
  }
  return request(`/books?${params}`)
}

export function getBook(id) {
  return request(`/books/${id}`)
}

export function uploadBook(file) {
  const body = new FormData()
  body.append('file', file)
  return request('/books', {
    method: 'POST',
    body,
  })
}

export function updateBook(id, data) {
  return request(`/books/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteBook(id) {
  return request(`/books/${id}`, {
    method: 'DELETE',
  })
}

export function getBookContent(id, chapter = 0) {
  return request(`/books/${id}/content?chapter=${chapter}`)
}

export function bookCoverUrl(id) {
  return `${API_PREFIX}/books/${id}/cover`
}

export function uploadIcon(blob) {
  const body = new FormData()
  body.append('file', blob, 'icon.png')
  return request('/icons', {
    method: 'POST',
    body,
  })
}

export function deleteIcon(icon) {
  const id = String(icon || '').replace('@file:', '')
  return request(`/icons/${encodeURIComponent(id)}.png`, {
    method: 'DELETE',
  })
}
