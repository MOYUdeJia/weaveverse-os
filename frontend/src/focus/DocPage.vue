<script setup>
import { DOMSerializer } from '@tiptap/pm/model'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import DOMPurify from 'dompurify'
import { computed, ref, watch } from 'vue'

import { attachmentUrl, uploadFile, uploadImage } from '../api/client'
import { useQueuedSave } from '../blocks/queuedSave.js'
import { showMenu } from '../contextMenu.js'
import { openDocTarget } from '../openExternal.js'
import { docExtensions, fileFromImageBlob, imageFilesFromList, linkLabel, normalizeUrl } from './docEditor.js'

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

const MODES = [
  { id: 'edit', label: '编辑' },
  { id: 'split', label: '分栏' },
  { id: 'preview', label: '预览' },
]

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save'])

const mode = ref('split')
const previewHtml = ref('')
const notice = ref('')
const linkOpen = ref(false)
const linkUrl = ref('')
const linkInput = ref(null)
const imageInput = ref(null)
const fileInput = ref(null)
const rev = ref(0)
const remembered = ref(null)
let hydrating = false

function readContent() {
  const instance = editor.value
  if (!instance) {
    return { text: props.block.content?.text || '' }
  }
  return { text: instance.getMarkdown() }
}

const { queue, flush } = useQueuedSave(emit, readContent, 500)

function viewKey(id) {
  return `wv.doc.view.${id}`
}

function syncPreview(instance) {
  const markdown = instance.getMarkdown().trim()
  previewHtml.value = markdown ? DOMPurify.sanitize(instance.getHTML()) : ''
}

function loadMarkdown(instance, markdown) {
  hydrating = true
  const source = markdown || ''
  if (source.trim()) {
    try {
      instance.commands.setContent(source, { contentType: 'markdown', emitUpdate: false })
    } catch (error) {
      console.error('Failed to parse doc markdown:', error)
      instance.commands.setContent(`<p>${escapeHtml(source)}</p>`, { contentType: 'html', emitUpdate: false })
    }
  } else {
    instance.commands.clearContent(false)
  }
  syncPreview(instance)
  hydrating = false
}

function rememberSelection() {
  const instance = editor.value
  if (!instance) {
    return
  }
  const { from, to } = instance.state.selection
  remembered.value = { from, to }
}

function chainAtSelection(instance) {
  const range = remembered.value
  const chain = instance.chain().focus()
  if (!range) {
    return chain
  }
  return chain.setTextSelection(range)
}

const editor = useEditor({
  extensions: docExtensions(),
  content: '',
  contentType: 'html',
  editorProps: {
    attributes: { class: 'doc-surface' },
    handleClick(_view, _pos, event) {
      const anchor = event.target?.closest?.('a')
      if (!anchor) {
        return false
      }
      const href = anchor.getAttribute('href')
      if (!href) {
        return false
      }
      event.preventDefault()
      openDocTarget(href)
      return true
    },
    handlePaste(_view, event) {
      const images = imageFilesFromList(event.clipboardData?.files)
      if (!images.length) {
        const item = [...(event.clipboardData?.items || [])].find(
          (entry) => entry.kind === 'file' && entry.type.startsWith('image/'),
        )
        const file = item?.getAsFile()
        if (!file) {
          return false
        }
        event.preventDefault()
        insertImageFiles([file])
        return true
      }
      event.preventDefault()
      insertImageFiles(images)
      return true
    },
    handleDrop(view, event, _slice, moved) {
      if (moved) {
        return false
      }
      const images = imageFilesFromList(event.dataTransfer?.files)
      if (!images.length) {
        return false
      }
      event.preventDefault()
      const coords = view.posAtCoords({ left: event.clientX, top: event.clientY })
      insertImageFiles(images, coords?.pos ?? null)
      return true
    },
  },
  onCreate: ({ editor: instance }) => {
    loadMarkdown(instance, props.block.content?.text || '')
    instance.setEditable(mode.value !== 'preview')
  },
  onUpdate: ({ editor: instance }) => {
    rev.value += 1
    if (hydrating) {
      return
    }
    syncPreview(instance)
    queue(props.block.id)
  },
  onSelectionUpdate: () => {
    rev.value += 1
  },
})

const inTable = computed(() => rev.value >= 0 && Boolean(editor.value?.isActive('table')))

function active(name, attrs) {
  return rev.value >= 0 && Boolean(editor.value?.isActive(name, attrs))
}

function canRun(name) {
  const instance = editor.value
  if (!instance || rev.value < 0) {
    return false
  }
  return instance.can()[name]()
}

function btnClass(on) {
  return on ? 'bg-white text-ink shadow-sm' : 'text-ink/70 hover:bg-white'
}

function run(command) {
  const instance = editor.value
  if (!instance || mode.value === 'preview') {
    return
  }
  command(instance.chain().focus()).run()
}

watch(
  () => props.block.id,
  (_id, previous) => {
    if (previous != null) {
      flush()
    }
    linkOpen.value = false
    notice.value = ''
    try {
      const stored = localStorage.getItem(viewKey(props.block.id))
      mode.value = MODES.some((item) => item.id === stored) ? stored : 'split'
    } catch {
      mode.value = 'split'
    }
    const instance = editor.value
    if (instance) {
      loadMarkdown(instance, props.block.content?.text || '')
      instance.setEditable(mode.value !== 'preview')
    }
  },
  { immediate: true },
)

watch(mode, (value) => {
  editor.value?.setEditable(value !== 'preview')
})

function chooseMode(next) {
  mode.value = next
  try {
    localStorage.setItem(viewKey(props.block.id), next)
  } catch {
    // 视图偏好写失败时，这次切换仍然生效。
  }
}

async function insertImageFiles(files, pos = null) {
  const instance = editor.value
  if (!instance || !files.length) {
    return
  }
  notice.value = '正在上传图片…'
  try {
    let at = pos
    for (const file of files) {
      const saved = await uploadImage(props.block.id, file)
      placeImage(instance, { src: attachmentUrl(saved.filename), alt: file.name || 'image' }, at)
      at = instance.state.selection.to
    }
    notice.value = ''
  } catch (error) {
    notice.value = error.message || '图片上传失败'
  }
}

function placeImage(instance, attrs, pos) {
  const content = { type: 'image', attrs }
  if (typeof pos === 'number') {
    instance.chain().focus().insertContentAt(pos, content).run()
    return
  }
  const selected = instance.state.selection
  if (selected.node?.type?.name === 'image') {
    instance.chain().focus().insertContentAt(selected.to, content).run()
    return
  }
  instance.chain().focus().insertContent(content).run()
}

async function insertFile(file) {
  const instance = editor.value
  if (!instance || !file) {
    return
  }
  notice.value = '正在上传文件…'
  try {
    const saved = await uploadFile(props.block.id, file)
    const href = attachmentUrl(saved.filename)
    const label = linkLabel(file.name)
    chainAtSelection(instance).insertContent(`[${label}](${href})`, { contentType: 'markdown' }).run()
    notice.value = ''
  } catch (error) {
    notice.value = error.message || '文件上传失败'
  }
}

function pickImage() {
  rememberSelection()
  imageInput.value?.click()
}

function pickFile() {
  rememberSelection()
  fileInput.value?.click()
}

function onPickImage(event) {
  const files = imageFilesFromList(event.target.files)
  event.target.value = ''
  insertImageFiles(files)
}

function onPickFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  insertFile(file)
}

function openLinkForm() {
  rememberSelection()
  linkUrl.value = editor.value?.getAttributes('link').href || ''
  linkOpen.value = true
  setTimeout(() => linkInput.value?.focus(), 0)
}

function applyLink() {
  const instance = editor.value
  if (!instance) {
    return
  }
  const href = normalizeUrl(linkUrl.value)
  if (!href) {
    chainAtSelection(instance).extendMarkRange('link').unsetLink().run()
    linkOpen.value = false
    return
  }
  const range = remembered.value
  const empty = !range || range.from === range.to
  if (empty) {
    chainAtSelection(instance)
      .insertContent({
        type: 'text',
        text: href,
        marks: [{ type: 'link', attrs: { href } }],
      })
      .run()
  } else {
    chainAtSelection(instance).extendMarkRange('link').setLink({ href }).run()
  }
  linkOpen.value = false
}

function selectionRange(instance) {
  return remembered.value || { from: instance.state.selection.from, to: instance.state.selection.to }
}

function copySelection() {
  const instance = editor.value
  if (!instance) {
    return
  }
  const { from, to } = selectionRange(instance)
  if (from === to) {
    return
  }
  const slice = instance.state.doc.slice(from, to)
  const holder = document.createElement('div')
  holder.appendChild(DOMSerializer.fromSchema(instance.schema).serializeFragment(slice.content))
  const html = holder.innerHTML
  const text = instance.state.doc.textBetween(from, to, '\n')
  const onCopy = (event) => {
    event.preventDefault()
    event.clipboardData.setData('text/html', html)
    event.clipboardData.setData('text/plain', text)
  }
  document.addEventListener('copy', onCopy)
  const copied = document.execCommand('copy')
  document.removeEventListener('copy', onCopy)
  if (!copied) {
    navigator.clipboard?.writeText(text).catch(() => {
      notice.value = '复制失败'
    })
  }
}

function cutSelection() {
  const instance = editor.value
  if (!instance) {
    return
  }
  const range = selectionRange(instance)
  if (range.from === range.to) {
    return
  }
  copySelection()
  instance.chain().focus().setTextSelection(range).deleteSelection().run()
}

async function pasteClipboard() {
  const instance = editor.value
  if (!instance) {
    return
  }
  try {
    const items = await navigator.clipboard.read()
    for (const item of items) {
      const imageType = item.types.find((type) => type.startsWith('image/'))
      if (!imageType) {
        continue
      }
      const blob = await item.getType(imageType)
      await insertImageFiles([fileFromImageBlob(blob, 'paste.png')])
      return
    }
    for (const item of items) {
      if (!item.types.includes('text/html')) {
        continue
      }
      const html = await (await item.getType('text/html')).text()
      chainAtSelection(instance).insertContent(html, { contentType: 'html' }).run()
      return
    }
    for (const item of items) {
      if (!item.types.includes('text/plain')) {
        continue
      }
      const text = await (await item.getType('text/plain')).text()
      chainAtSelection(instance).insertContent(text).run()
      return
    }
    notice.value = '剪贴板是空的'
  } catch {
    notice.value = '浏览器拦住了菜单粘贴。用 Ctrl+V。'
  }
}

function imageFromEvent(event) {
  return event.target?.closest?.('img') || null
}

function imagePos(instance, img) {
  const host = img.closest('[data-resize-container]') || img
  return instance.view.posAtDOM(host, 0)
}

function resizeImage(img, ratio) {
  const instance = editor.value
  if (!instance || !img) {
    return
  }
  const pos = imagePos(instance, img)
  img.style.width = ''
  img.style.height = ''
  if (ratio == null) {
    instance.chain().setNodeSelection(pos).updateAttributes('image', { width: null, height: null }).run()
    return
  }
  const column = instance.view.dom.clientWidth || 640
  const width = Math.max(80, Math.round(column * ratio))
  img.style.width = `${width}px`
  img.style.height = 'auto'
  instance.chain().setNodeSelection(pos).updateAttributes('image', { width, height: null }).run()
}

function alignImage(img, align) {
  const instance = editor.value
  if (!instance || !img) {
    return
  }
  const pos = imagePos(instance, img)
  instance.chain().setNodeSelection(pos).updateAttributes('image', { align }).run()
}

function onMenu(event) {
  const instance = editor.value
  if (!instance || mode.value === 'preview') {
    return
  }
  const img = imageFromEvent(event)
  if (img) {
    showMenu(event, [
      { label: '充满宽度', onClick: () => resizeImage(img, null) },
      { label: '75%', onClick: () => resizeImage(img, 0.75) },
      { label: '50%', onClick: () => resizeImage(img, 0.5) },
      { label: '25%', onClick: () => resizeImage(img, 0.25) },
      { label: '左对齐', divided: true, onClick: () => alignImage(img, 'left') },
      { label: '居中', onClick: () => alignImage(img, 'center') },
      { label: '右对齐', onClick: () => alignImage(img, 'right') },
    ])
    return
  }
  rememberSelection()
  const range = remembered.value
  const hasSelection = Boolean(range && range.from !== range.to)
  showMenu(event, [
    { label: '剪切', disabled: !hasSelection, onClick: cutSelection },
    { label: '复制', disabled: !hasSelection, onClick: copySelection },
    { label: '粘贴', onClick: pasteClipboard },
    { label: '全选', onClick: () => instance.chain().focus().selectAll().run() },
    { label: '添加链接', divided: true, onClick: openLinkForm },
    { label: '添加图片', onClick: pickImage },
    { label: '添加文件', onClick: pickFile },
    { label: '撤销', divided: true, disabled: !instance.can().undo(), onClick: () => run((chain) => chain.undo()) },
    { label: '重做', disabled: !instance.can().redo(), onClick: () => run((chain) => chain.redo()) },
  ])
}

function onContentClick(event) {
  const anchor = event.target.closest('a')
  if (!anchor || !anchor.href) {
    return
  }
  event.preventDefault()
  openDocTarget(anchor.getAttribute('href') || anchor.href)
}
</script>

<template>
  <div class="flex min-h-full flex-col">
    <div class="sticky top-0 z-10 border-b border-black/10 bg-[#fcfaf5]/95 px-4 py-2 backdrop-blur-sm">
      <div class="flex items-center justify-between gap-3">
        <div class="flex rounded-md bg-black/5 p-0.5">
          <button
            v-for="item in MODES"
            :key="item.id"
            type="button"
            class="h-7 rounded px-3 text-xs font-medium"
            :class="mode === item.id ? 'bg-white text-ink shadow-sm' : 'text-ink/55 hover:text-ink'"
            @click="chooseMode(item.id)"
          >
            {{ item.label }}
          </button>
        </div>
        <p class="text-xs text-ink/40">{{ notice || '自动保存' }}</p>
      </div>

      <div v-show="mode !== 'preview'" class="mt-2 flex flex-wrap items-center gap-1">
        <button type="button" title="标题 1" class="h-7 rounded px-1.5 text-xs font-semibold" :class="btnClass(active('heading', { level: 1 }))" @mousedown.prevent @click="run((chain) => chain.toggleHeading({ level: 1 }))">H1</button>
        <button type="button" title="标题 2" class="h-7 rounded px-1.5 text-xs font-semibold" :class="btnClass(active('heading', { level: 2 }))" @mousedown.prevent @click="run((chain) => chain.toggleHeading({ level: 2 }))">H2</button>
        <button type="button" title="标题 3" class="h-7 rounded px-1.5 text-xs font-semibold" :class="btnClass(active('heading', { level: 3 }))" @mousedown.prevent @click="run((chain) => chain.toggleHeading({ level: 3 }))">H3</button>
        <span class="mx-0.5 h-4 w-px bg-black/10" />
        <button type="button" title="粗体 Ctrl+B" class="h-7 rounded px-1.5 text-xs font-bold" :class="btnClass(active('bold'))" @mousedown.prevent @click="run((chain) => chain.toggleBold())">B</button>
        <button type="button" title="斜体 Ctrl+I" class="h-7 rounded px-1.5 text-xs italic" :class="btnClass(active('italic'))" @mousedown.prevent @click="run((chain) => chain.toggleItalic())">I</button>
        <button type="button" title="下划线 Ctrl+U" class="h-7 rounded px-1.5 text-xs underline" :class="btnClass(active('underline'))" @mousedown.prevent @click="run((chain) => chain.toggleUnderline())">U</button>
        <button type="button" title="删除线" class="h-7 rounded px-1.5 text-xs line-through" :class="btnClass(active('strike'))" @mousedown.prevent @click="run((chain) => chain.toggleStrike())">S</button>
        <span class="mx-0.5 h-4 w-px bg-black/10" />
        <button type="button" title="无序列表" class="h-7 rounded px-1.5 text-xs" :class="btnClass(active('bulletList'))" @mousedown.prevent @click="run((chain) => chain.toggleBulletList())">• 列表</button>
        <button type="button" title="有序列表" class="h-7 rounded px-1.5 text-xs" :class="btnClass(active('orderedList'))" @mousedown.prevent @click="run((chain) => chain.toggleOrderedList())">1. 列表</button>
        <button type="button" title="引用" class="h-7 rounded px-1.5 text-xs" :class="btnClass(active('blockquote'))" @mousedown.prevent @click="run((chain) => chain.toggleBlockquote())">❝</button>
        <button type="button" title="行内代码" class="h-7 rounded px-1.5 font-mono text-xs" :class="btnClass(active('code'))" @mousedown.prevent @click="run((chain) => chain.toggleCode())">&lt;/&gt;</button>
        <button type="button" title="代码块" class="h-7 rounded px-1.5 font-mono text-xs" :class="btnClass(active('codeBlock'))" @mousedown.prevent @click="run((chain) => chain.toggleCodeBlock())">{ }</button>
        <span class="mx-0.5 h-4 w-px bg-black/10" />
        <button type="button" title="表格" class="h-7 rounded px-1.5 text-xs" :class="btnClass(inTable)" @mousedown.prevent @click="run((chain) => chain.insertTable({ rows: 3, cols: 3, withHeaderRow: true }))">▦</button>
        <template v-if="inTable">
          <button type="button" title="下方加一行" class="h-7 rounded px-1.5 text-xs text-ink/70 hover:bg-white" @mousedown.prevent @click="run((chain) => chain.addRowAfter())">+行</button>
          <button type="button" title="右侧加一列" class="h-7 rounded px-1.5 text-xs text-ink/70 hover:bg-white" @mousedown.prevent @click="run((chain) => chain.addColumnAfter())">+列</button>
          <button type="button" title="删除表格" class="h-7 rounded px-1.5 text-xs text-ink/70 hover:bg-white" @mousedown.prevent @click="run((chain) => chain.deleteTable())">删表</button>
        </template>
        <button type="button" title="分割线" class="h-7 rounded px-1.5 text-xs text-ink/70 hover:bg-white" @mousedown.prevent @click="run((chain) => chain.setHorizontalRule())">—</button>
        <button type="button" title="链接" class="h-7 rounded px-1.5 text-xs" :class="btnClass(active('link') || linkOpen)" @mousedown.prevent @click="openLinkForm">🔗</button>
        <span class="mx-0.5 h-4 w-px bg-black/10" />
        <button type="button" title="撤销 Ctrl+Z" class="h-7 rounded px-1.5 text-xs text-ink/70 hover:bg-white disabled:opacity-30" :disabled="!canRun('undo')" @mousedown.prevent @click="run((chain) => chain.undo())">↶</button>
        <button type="button" title="重做 Ctrl+Shift+Z" class="h-7 rounded px-1.5 text-xs text-ink/70 hover:bg-white disabled:opacity-30" :disabled="!canRun('redo')" @mousedown.prevent @click="run((chain) => chain.redo())">↷</button>
      </div>

      <form v-if="linkOpen && mode !== 'preview'" class="mt-2 flex items-center gap-2" @submit.prevent="applyLink">
        <input
          ref="linkInput"
          v-model="linkUrl"
          type="text"
          class="h-8 min-w-0 flex-1 rounded border border-black/10 bg-white px-2 text-sm outline-none"
          placeholder="https:// 或留空取消链接"
          @keydown.esc="linkOpen = false"
        />
        <button type="submit" class="h-8 rounded bg-moss px-3 text-xs font-medium text-white">确定</button>
        <button type="button" class="h-8 rounded px-2 text-xs text-ink/55" @click="linkOpen = false">取消</button>
      </form>
    </div>

    <input ref="imageInput" class="hidden" type="file" accept="image/png,image/jpeg,image/gif,image/webp" multiple @change="onPickImage" />
    <input ref="fileInput" class="hidden" type="file" @change="onPickFile" />

    <div class="grid min-h-0 flex-1" :class="mode === 'split' ? 'lg:grid-cols-2' : 'grid-cols-1'">
      <div
        v-show="mode !== 'preview'"
        class="min-h-[70vh]"
        :class="mode === 'split' ? 'lg:border-r lg:border-black/10' : ''"
        @contextmenu="onMenu"
      >
        <editor-content :editor="editor" class="doc-editor doc-prose px-8 py-7" />
      </div>
      <article
        v-show="mode !== 'edit'"
        class="doc-prose doc-reading min-h-[70vh] px-8 py-7"
        @click="onContentClick"
        v-html="previewHtml || '<p class=&quot;doc-empty&quot;>还没有文字。切到编辑或分栏开始写。</p>'"
      />
    </div>
  </div>
</template>
