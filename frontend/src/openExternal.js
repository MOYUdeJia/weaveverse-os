// 用 pywebview js_api 打开外链；没有桥时退回 window.open。
// Open external links via pywebview js_api, falling back to window.open.

const ATTACHMENT_HREF = /\/api\/attachments\/([^/?#]+)/

export async function openDocTarget(href) {
  const raw = String(href || '').trim()
  const match = raw.match(ATTACHMENT_HREF)
  if (!match) {
    return openExternalLink(raw)
  }

  const filename = decodeURIComponent(match[1])
  const api = window.pywebview?.api
  if (api && typeof api.open_attachment === 'function') {
    try {
      const opened = await api.open_attachment(filename)
      if (opened) {
        return
      }
    } catch (error) {
      console.error('pywebview open_attachment failed, opening the file URL instead:', error)
    }
  }

  window.open(`/api/attachments/${encodeURIComponent(filename)}`, '_blank', 'noopener,noreferrer')
}

export async function openExternalLink(url) {
  if (!url) {
    return
  }

  const api = window.pywebview?.api
  if (api && typeof api.open_url === 'function') {
    try {
      await api.open_url(url)
      return
    } catch (error) {
      console.error('pywebview open_url failed, falling back to window.open:', error)
    }
  }

  window.open(url, '_blank', 'noopener,noreferrer')
}
