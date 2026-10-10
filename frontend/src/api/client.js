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

export function searchLibrary(query) {
  return request(`/search?q=${encodeURIComponent(query)}`)
}

export function getAppearance() {
  return request('/appearance')
}

export function updateAppearance(data) {
  return request('/appearance', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function uploadBackground(file, kind, groupId) {
  const body = new FormData()
  body.append('file', file)
  const query = new URLSearchParams({ kind })
  if (groupId != null) {
    query.set('group_id', String(groupId))
  }
  return request(`/appearance/files?${query}`, {
    method: 'POST',
    body,
  })
}

export function clearBackground(kind, groupId) {
  const query = new URLSearchParams({ kind })
  if (groupId != null) {
    query.set('group_id', String(groupId))
  }
  return request(`/appearance/files?${query}`, { method: 'DELETE' })
}

export function backgroundUrl(filename) {
  return `${API_PREFIX}/appearance/files/${encodeURIComponent(filename)}`
}

export function saveQuickNote(text, tags = []) {
  return request('/inbox/notes', {
    method: 'POST',
    body: JSON.stringify({ text, tags }),
  })
}

export function getQuickTags() {
  return request('/inbox/tags')
}

export function saveQuickTags(tags) {
  return request('/inbox/tags', {
    method: 'PUT',
    body: JSON.stringify({ tags }),
  })
}

export function listTracks() {
  return request('/music')
}

export function uploadTrack(file) {
  const body = new FormData()
  body.append('file', file)
  return request('/music', { method: 'POST', body })
}

export function deleteTrack(filename) {
  return request(`/music/${encodeURIComponent(filename)}`, { method: 'DELETE' })
}

export function trackUrl(filename) {
  return `${API_PREFIX}/music/files/${encodeURIComponent(filename)}`
}

function photoHeaders(password) {
  return password ? { 'Album-Password': password } : {}
}

export function listAlbums() {
  return request('/photos/albums')
}

export function createAlbum(name, isPrivate, password = '', color = '') {
  return request('/photos/albums', {
    method: 'POST',
    body: JSON.stringify({ name, is_private: isPrivate, password, color }),
  })
}

export function reorderAlbums(ids) {
  return request('/photos/albums/reorder', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}

export function updateAlbum(id, data) {
  return request(`/photos/albums/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteAlbum(id) {
  return request(`/photos/albums/${id}`, { method: 'DELETE' })
}

export function unlockAlbum(id, password) {
  return request(`/photos/albums/${id}/unlock`, {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
}

export function listPhotos(albumId = null, password = '') {
  const query = albumId == null ? '' : `?album_id=${albumId}`
  return request(`/photos${query}`, { headers: photoHeaders(password) })
}

export function addPhoto(filename, note = '', albumId = null, password = '') {
  return request('/photos', {
    method: 'POST',
    headers: photoHeaders(password),
    body: JSON.stringify({ filename, note, album_id: albumId }),
  })
}

export function uploadPhoto(file, albumId = null, password = '') {
  const body = new FormData()
  body.append('file', file)
  const query = albumId == null ? '' : `?album_id=${albumId}`
  return request(`/photos/upload${query}`, {
    method: 'POST',
    headers: photoHeaders(password),
    body,
  })
}

export function renamePhoto(id, displayName) {
  return request(`/photos/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ display_name: displayName }),
  })
}

export function movePhotos(ids, albumId, password = '') {
  return request('/photos/move', {
    method: 'POST',
    headers: photoHeaders(password),
    body: JSON.stringify({ ids, album_id: albumId }),
  })
}

export function deletePhotos(ids) {
  return request('/photos/bulk-delete', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  })
}

export function deletePhoto(id) {
  return request(`/photos/${id}`, {
    method: 'DELETE',
  })
}

export async function saveAttachmentLocal(filename, suggestedName = '') {
  const api = window.pywebview?.api
  if (api && typeof api.save_attachment === 'function') {
    const result = await api.save_attachment(filename, suggestedName || filename)
    if (result?.error) {
      throw new Error(result.error)
    }
    return result
  }
  const link = document.createElement('a')
  link.href = attachmentUrl(filename)
  link.download = suggestedName || filename
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
  return { path: '' }
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

export function getAiSettings() {
  return request('/ai/settings')
}

export function saveAiSettings(data) {
  return request('/ai/settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function testAiConnection() {
  return request('/ai/test', { method: 'POST' })
}

export function listIdeas() {
  return request('/ideas')
}

export function createIdea(data) {
  return request('/ideas', { method: 'POST', body: JSON.stringify(data) })
}

export function updateIdea(id, data) {
  return request(`/ideas/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteIdea(id) {
  return request(`/ideas/${id}`, { method: 'DELETE' })
}

export function summarizeIdea(id) {
  return request(`/ideas/${id}/summary`, { method: 'POST' })
}

export function autotagIdea(id) {
  return request(`/ideas/${id}/tags`, { method: 'POST' })
}

export async function streamAiChat(messages, onEvent, resume = null) {
  const response = await fetch(`${API_PREFIX}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, resume }),
  })
  if (!response.ok) {
    let message = '网络错误，请重试'
    try {
      const payload = await response.json()
      message = formatDetail(payload.detail) || message
    } catch {
      message = '网络错误，请重试'
    }
    throw new Error(message)
  }
  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('网络错误，请重试')
  }
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      const line = chunk.split('\n').find((item) => item.startsWith('data:'))
      if (!line) {
        continue
      }
      const data = line.slice(5).trim()
      if (data === '[DONE]') {
        return
      }
      const payload = JSON.parse(data)
      if (payload.error) {
        throw new Error(payload.error)
      }
      onEvent(payload)
    }
  }
}
