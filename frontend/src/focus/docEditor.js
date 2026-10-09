// 长文编辑器的 TipTap 扩展。读写都走 Markdown，旧的 {text} 不用改库。
// TipTap extensions for the doc page. Markdown in and out, so existing {text} stays.

import Image from '@tiptap/extension-image'
import Placeholder from '@tiptap/extension-placeholder'
import { Table } from '@tiptap/extension-table'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableRow } from '@tiptap/extension-table-row'
import { Markdown } from '@tiptap/markdown'
import StarterKit from '@tiptap/starter-kit'

const IMAGE_TYPES = {
  'image/png': 'png',
  'image/jpeg': 'jpg',
  'image/jpg': 'jpg',
  'image/gif': 'gif',
  'image/webp': 'webp',
}

export function docExtensions() {
  return [
    StarterKit.configure({
      heading: { levels: [1, 2, 3, 4, 5, 6] },
      link: {
        openOnClick: false,
        autolink: true,
        linkOnPaste: true,
        HTMLAttributes: { rel: 'noopener noreferrer' },
      },
      dropcursor: { color: '#3f6f57', width: 2 },
    }),
    Placeholder.configure({ placeholder: '从这里开始写。' }),
    docImage(),
    Table.configure({ resizable: false }),
    TableRow,
    TableHeader,
    TableCell,
    Markdown,
  ]
}

function escapeAttr(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
}

function docImage() {
  return Image.extend({
    addAttributes() {
      return {
        ...this.parent?.(),
        width: {
          default: null,
          parseHTML: (element) => element.getAttribute('width'),
          renderHTML: (attrs) => (attrs.width ? { width: attrs.width } : {}),
        },
        height: {
          default: null,
          parseHTML: (element) => element.getAttribute('height'),
          renderHTML: (attrs) => (attrs.height ? { height: attrs.height } : {}),
        },
        align: {
          default: null,
          parseHTML: (element) => element.getAttribute('data-align'),
          renderHTML: (attrs) => (attrs.align ? { 'data-align': attrs.align } : {}),
        },
      }
    },
    renderMarkdown(node) {
      const attrs = node.attrs || {}
      const src = attrs.src || ''
      const alt = attrs.alt || ''
      const title = attrs.title || ''
      if (attrs.width || attrs.height || attrs.align) {
        const parts = [`src="${escapeAttr(src)}"`, `alt="${escapeAttr(alt)}"`]
        if (attrs.width) {
          parts.push(`width="${Number(attrs.width) || attrs.width}"`)
        }
        if (attrs.height) {
          parts.push(`height="${Number(attrs.height) || attrs.height}"`)
        }
        if (attrs.align) {
          parts.push(`data-align="${escapeAttr(attrs.align)}"`)
        }
        return `<img ${parts.join(' ')} />`
      }
      return title ? `![${alt}](${src} "${title}")` : `![${alt}](${src})`
    },
  }).configure({
    allowBase64: false,
    HTMLAttributes: { class: 'doc-image' },
    resize: {
      enabled: true,
      directions: ['bottom-right', 'right', 'bottom'],
      minWidth: 80,
      minHeight: 48,
      alwaysPreserveAspectRatio: true,
    },
  })
}

export function normalizeUrl(value) {
  const trimmed = String(value || '').trim()
  if (!trimmed || /^\s*javascript:/i.test(trimmed)) {
    return ''
  }
  if (/^(https?:|mailto:|\/)/i.test(trimmed)) {
    return trimmed
  }
  return `https://${trimmed}`
}

export function linkLabel(name) {
  const cleaned = String(name || '文件').replace(/[[\]\r\n]/g, '').trim()
  return (cleaned || '文件').slice(0, 80)
}

export function imageFilesFromList(fileList) {
  return [...(fileList || [])].filter((file) => IMAGE_TYPES[file.type])
}

export function fileFromImageBlob(blob, name) {
  const ext = IMAGE_TYPES[blob.type] || 'png'
  const type = blob.type === 'image/jpg' ? 'image/jpeg' : IMAGE_TYPES[blob.type] ? blob.type : 'image/png'
  const filename = name && /\.(png|jpe?g|gif|webp)$/i.test(name) ? name : `image.${ext}`
  return new File([blob], filename, { type })
}
