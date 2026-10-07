// 用 pywebview js_api 打开外链；没有桥时退回 window.open。
// Open external links via pywebview js_api, falling back to window.open.

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
