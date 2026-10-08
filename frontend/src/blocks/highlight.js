// 少量语言的就地高亮。先转义再包 span，不引入高亮库。
// A small in-place highlighter. Escape first, then wrap spans. No highlight library.

const KEYWORDS = {
  javascript: ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'class', 'import', 'export', 'from', 'new', 'async', 'await', 'try', 'catch', 'throw'],
  python: ['def', 'return', 'if', 'elif', 'else', 'for', 'while', 'class', 'import', 'from', 'as', 'try', 'except', 'with', 'lambda', 'pass', 'in', 'not', 'and', 'or', 'none', 'true', 'false'],
  sql: ['select', 'from', 'where', 'and', 'or', 'insert', 'into', 'values', 'update', 'set', 'delete', 'create', 'table', 'join', 'left', 'on', 'order', 'by', 'group', 'limit'],
  css: ['important', 'media', 'keyframes'],
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function span(className, text) {
  return `<span class="${className}">${text}</span>`
}

export function highlightCode(source, language) {
  const lang = (language || 'plain').toLowerCase()
  const text = escapeHtml(source || '')
  if (lang === 'plain' || lang === 'markdown') {
    return text
  }

  const keywords = new Set(KEYWORDS[lang] || [])
  const pattern = /(&lt;!--[\s\S]*?--&gt;|\/\*[\s\S]*?\*\/|\/\/.*|#.*|&quot;(?:\\.|[^&])*?&quot;|&#39;(?:\\.|[^&#])*?&#39;|&(?:#39|quot);|'(?:\\.|[^'\n])*'|"(?:\\.|[^"\n])*"|`(?:\\.|[^`\n])*`|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][\w]*\b)/g

  return text.replace(pattern, (token) => {
    if (
      token.startsWith('//')
      || token.startsWith('#')
      || token.startsWith('/*')
      || token.startsWith('&lt;!--')
    ) {
      return span('text-ink/40', token)
    }
    if (token.startsWith('"') || token.startsWith("'") || token.startsWith('`') || token.startsWith('&quot;') || token.startsWith('&#39;')) {
      return span('text-ember', token)
    }
    if (/^\d/.test(token)) {
      return span('text-aurora', token)
    }
    if (keywords.has(token.toLowerCase())) {
      return span('font-semibold text-moss', token)
    }
    return token
  })
}
