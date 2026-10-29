// 预设里的图标绑定。文件图标只属于当前预设，没绑过的预设回到页面默认符号。

const DEFAULTS = {
  doc: '📄',
  plain: '📝',
  bookmarks: '🔖',
  canvas: '🎨',
  inbox: '📥',
  timeline: '⏳',
  bookshelf: '📚',
  photo_library: '🖼',
  idea_box: '💡',
  password_vault: '🔒',
  markdown: '📄',
  todo: '✅',
  gallery: '🖼️',
  collection: '🔗',
  group_overview: '📁',
}

export function isFileIcon(icon) {
  return /^@file:[0-9a-f]{12}$/.test(String(icon || ''))
}

export function defaultIcon(pageType) {
  return DEFAULTS[pageType] || '📄'
}

export function resolveIcon(bindings, kind, id, stored, pageType) {
  const hit = bindings?.[kind]?.[String(id)]
  if (hit) {
    return hit
  }
  if (isFileIcon(stored)) {
    return kind === 'group' ? '📁' : defaultIcon(pageType)
  }
  return stored || (kind === 'group' ? '📁' : defaultIcon(pageType))
}
