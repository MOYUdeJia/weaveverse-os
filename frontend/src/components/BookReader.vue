<script setup>
import DOMPurify from 'dompurify'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import {
  createBookNote,
  deleteBookNote,
  getBook,
  getBookContent,
  listBookNotes,
  saveQuickNote,
  updateBook,
} from '../api/client'
import { showMenu } from '../contextMenu'
import { showToast } from '../toast'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close', 'progress'])

const COLORS = [
  { id: 'gold', label: '金' },
  { id: 'moss', label: '绿' },
  { id: 'sky', label: '蓝' },
  { id: 'rose', label: '粉' },
]

const detail = ref(null)
const content = ref(null)
const chapter = ref(0)
const loading = ref(true)
const errorMessage = ref('')
const openError = ref('')
const scroller = ref(null)
const textRoot = ref(null)
const htmlRoot = ref(null)
const notes = ref([])
const sideTab = ref('toc')
const noteOpen = ref(false)
const noteBody = ref('')
const bookmarkOpen = ref(false)
const bookmarkNote = ref('')
const pendingSelection = ref(null)
const activeBookmarkId = ref(null)
let suspendScroll = false
let pending = null
let timer = 0
let activeNoteId = null
let capturedSelection = null
let capturedAt = 0

const toc = computed(() => detail.value?.toc ?? [])
const markNotes = computed(() => notes.value.filter((item) => item.type === 'highlight' || item.type === 'underline' || item.type === 'note'))
const bookmarks = computed(() =>
  notes.value
    .filter((item) => item.type === 'bookmark')
    .slice()
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()),
)
const textPieces = computed(() => pieces(content.value?.text || '', notes.value))

function queueProgress(patch, immediate = false) {
  pending = { ...(pending || {}), ...patch }
  window.clearTimeout(timer)
  if (immediate) {
    flushProgress()
    return
  }
  timer = window.setTimeout(flushProgress, 800)
}

async function flushProgress() {
  window.clearTimeout(timer)
  if (!pending) {
    return
  }
  const body = pending
  pending = null
  try {
    const updated = await updateBook(props.book.id, body)
    emit('progress', updated)
  } catch (error) {
    console.error('Failed to save reading progress:', error)
  }
}

function restoreScroll(offset) {
  const el = scroller.value
  if (!el) {
    return
  }
  const max = el.scrollHeight - el.clientHeight
  el.scrollTop = max > 0 ? max * (offset || 0) : 0
}

async function loadNotes() {
  const data = await listBookNotes(props.book.id)
  notes.value = data.notes || []
  if (props.book.format === 'epub') {
    await nextTick()
    paintHtmlMarks()
  }
}

async function loadChapter(index, offset) {
  suspendScroll = true
  if (!content.value) {
    loading.value = true
  }
  errorMessage.value = ''
  try {
    chapter.value = index
    content.value = await getBookContent(props.book.id, index)
    loading.value = false
    await nextTick()
    if (props.book.format === 'epub') {
      paintHtmlMarks()
    }
    restoreScroll(offset)
  } catch (error) {
    errorMessage.value = error.message || '无法打开这一章'
  } finally {
    loading.value = false
    await nextTick()
    suspendScroll = false
  }
}

function stepChapter(direction) {
  const next = chapter.value + direction
  if (next < 0 || next >= toc.value.length) {
    return
  }
  goTo(next)
}

async function goTo(index) {
  if (index === chapter.value || index < 0 || index >= toc.value.length) {
    return
  }
  await loadChapter(index, 0)
  queueProgress({ progress_chapter: index, progress_offset: 0, progress_cfi: `${index}:0` }, true)
}

function onScroll(event) {
  if (suspendScroll || props.book.format === 'pdf') {
    return
  }
  const el = event.target
  const max = el.scrollHeight - el.clientHeight
  const offset = max <= 0 ? 0 : el.scrollTop / max
  const patch = { progress_offset: Number(offset.toFixed(6)) }
  if (props.book.format === 'epub') {
    const length = htmlRoot.value?.textContent?.length || 0
    const index = Math.min(length, Math.round(offset * length))
    patch.progress_chapter = chapter.value
    patch.progress_cfi = `${chapter.value}:${index}`
  }
  queueProgress(patch)
}

function pieces(text, list) {
  const marks = list
    .filter((item) => {
      if (!item.text || String(item.position).includes(':')) {
        return false
      }
      if (item.type === 'highlight' || item.type === 'underline') {
        return true
      }
      return item.type === 'bookmark' && item.id === activeBookmarkId.value
    })
    .map((item) => ({
      start: Number(item.position),
      end: Number(item.position) + item.text.length,
      note: item,
    }))
    .filter((item) => Number.isFinite(item.start) && item.end > item.start)
  const points = new Set([0, text.length])
  for (const mark of marks) {
    points.add(Math.max(0, Math.min(text.length, mark.start)))
    points.add(Math.max(0, Math.min(text.length, mark.end)))
  }
  const sorted = [...points].sort((left, right) => left - right)
  const out = []
  for (let index = 0; index < sorted.length - 1; index += 1) {
    const start = sorted[index]
    const end = sorted[index + 1]
    if (end <= start) {
      continue
    }
    out.push({
      text: text.slice(start, end),
      start,
      marks: marks.filter((mark) => mark.start <= start && mark.end >= end).map((mark) => mark.note),
    })
  }
  return out.length ? out : [{ text, start: 0, marks: [] }]
}

function pieceClass(marks) {
  const highlight = marks.find((item) => item.type === 'highlight')
  const line = marks.find((item) => item.type === 'underline')
  const bookmark = marks.find((item) => item.type === 'bookmark')
  return [highlight ? `is-${highlight.color}` : '', line ? `is-line is-line-${line.color}` : '', bookmark ? 'is-bookmark' : ''].filter(Boolean)
}

function paintHtmlMarks() {
  const root = htmlRoot.value
  if (!root) {
    return
  }
  root.innerHTML = DOMPurify.sanitize(content.value?.html || '')
  const ranges = notes.value
    .filter((item) => item.text && (item.type === 'highlight' || item.type === 'underline' || (item.type === 'bookmark' && item.id === activeBookmarkId.value)))
    .map((item) => {
      const [chapterPart, startPart] = String(item.position).split(':')
      return {
        chapter: Number(chapterPart),
        start: Number(startPart),
        end: Number(startPart) + item.text.length,
        note: item,
      }
    })
    .filter((item) => item.chapter === chapter.value && Number.isFinite(item.start))
    .sort((left, right) => right.start - left.start)
  for (const range of ranges) {
    wrapHtml(root, range.start, range.end, range.note)
  }
}

function wrapHtml(root, start, end, note) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let count = 0
  let node = walker.nextNode()
  let startNode = null
  let startOffset = 0
  let endNode = null
  let endOffset = 0
  while (node) {
    const next = count + node.textContent.length
    if (!startNode && start < next) {
      startNode = node
      startOffset = Math.max(0, start - count)
    }
    if (startNode && end <= next) {
      endNode = node
      endOffset = Math.max(0, end - count)
      break
    }
    count = next
    node = walker.nextNode()
  }
  if (!startNode || !endNode) {
    return
  }
  const range = document.createRange()
  try {
    range.setStart(startNode, startOffset)
    range.setEnd(endNode, endOffset)
    const mark = document.createElement('mark')
    mark.dataset.noteId = String(note.id)
    mark.className = note.type === 'underline' ? `is-line is-line-${note.color}` : note.type === 'bookmark' ? 'is-bookmark' : `is-${note.color}`
    range.surroundContents(mark)
  } catch (error) {
    console.error('Failed to wrap highlight:', error)
  }
}

function offsetIn(root, node, nodeOffset) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let count = 0
  let current = walker.nextNode()
  while (current) {
    if (current === node) {
      return count + nodeOffset
    }
    count += current.textContent.length
    current = walker.nextNode()
  }
  return count
}

function readSelection(root) {
  const selection = window.getSelection()
  if (!root || !selection || !selection.rangeCount || !root.contains(selection.anchorNode)) {
    return null
  }
  const text = selection.toString().trim()
  if (!text) {
    return null
  }
  const range = selection.getRangeAt(0)
  const start = offsetIn(root, range.startContainer, range.startOffset)
  const end = offsetIn(root, range.endContainer, range.endOffset)
  const from = Math.min(start, end)
  return { text, position: String(from), end: Math.max(start, end) }
}

function pointerEvent(x, y) {
  return {
    clientX: x,
    clientY: y,
    preventDefault() {},
    stopPropagation() {},
  }
}

function noteSpan(note) {
  if (String(note.position).includes(':')) {
    const [chapterPart, startPart] = String(note.position).split(':')
    const start = Number(startPart)
    return { chapter: Number(chapterPart), start, end: start + (note.text?.length || 0) }
  }
  const start = Number(note.position)
  return { chapter: 0, start, end: start + (note.text?.length || 0) }
}

function marksCovering(selection) {
  const marks = notes.value.filter((item) => item.type === 'highlight' || item.type === 'underline')
  const start = selection?.rawStart != null ? Number(selection.rawStart) : null
  if (start != null && Number.isFinite(start)) {
    const end = selection.end ?? start
    const hits = marks.filter((item) => {
      const span = noteSpan(item)
      const sameChapter = props.book.format === 'epub' ? span.chapter === chapter.value : span.chapter === 0
      return sameChapter && span.start < end && span.end > start
    })
    if (hits.length) {
      return hits
    }
  }
  return activeNoteId ? marks.filter((item) => item.id === activeNoteId) : []
}

function openMarkMenu(selection) {
  pendingSelection.value = selection
  const canText = Boolean(selection?.text)
  showMenu(pointerEvent(selection.x, selection.y), [
    { label: '复制', disabled: !canText, onClick: () => copyText(selection.text) },
    {
      label: '高亮',
      disabled: !canText,
      children: COLORS.map((color) => ({ label: color.label, onClick: () => addMark('highlight', color.id) })),
    },
    {
      label: '划线',
      disabled: !canText,
      children: COLORS.map((color) => ({ label: color.label, onClick: () => addMark('underline', color.id) })),
    },
    { label: '取消高亮', disabled: !marksCovering(selection).length, onClick: clearMarks },
    {
      label: '添加笔记',
      disabled: !canText,
      onClick: () => {
        noteBody.value = ''
        noteOpen.value = true
      },
    },
    { label: '一键摘抄', disabled: !canText, onClick: excerpt },
  ])
}

function readingRoot() {
  return props.book.format === 'epub' ? htmlRoot.value : textRoot.value
}

function onMouseUp() {
  capturedSelection = readSelection(readingRoot())
  capturedAt = Date.now()
}

function onTextMenu(event) {
  event.preventDefault()
  const root = readingRoot()
  const mark = event.target?.closest?.('mark')
  if (mark?.dataset?.noteId) {
    activeNoteId = Number(mark.dataset.noteId)
  }
  let selection = readSelection(root)
  if (!selection && capturedSelection && Date.now() - capturedAt < 800) {
    selection = capturedSelection
  }
  if (!selection && !activeNoteId) {
    return
  }
  const position = props.book.format === 'epub'
    ? `${chapter.value}:${selection?.position || 0}`
    : (selection?.position || '0')
  openMarkMenu({
    text: selection?.text || '',
    position: selection ? position : '',
    end: selection?.end,
    rawStart: selection?.position,
    x: event.clientX,
    y: event.clientY,
  })
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text || '')
    showToast('已复制')
  } catch {
    showToast('复制失败')
  }
}

async function addMark(type, color) {
  const selection = pendingSelection.value
  if (!selection?.text || !selection.position) {
    showToast('先选中一段文字')
    return
  }
  try {
    await createBookNote(props.book.id, {
      type,
      color,
      position: selection.position,
      text: selection.text,
      note_content: '',
    })
    await loadNotes()
    showToast(type === 'underline' ? '已划线' : '已高亮')
  } catch (error) {
    showToast(error.message || '没有记下')
  }
}

async function clearMarks() {
  const hits = marksCovering({
    position: pendingSelection.value?.rawStart,
    end: pendingSelection.value?.end,
  })
  if (!hits.length) {
    showToast('这里没有高亮')
    return
  }
  try {
    for (const note of hits) {
      await deleteBookNote(props.book.id, note.id)
    }
    activeNoteId = null
    await loadNotes()
    showToast('已取消高亮')
  } catch (error) {
    showToast(error.message || '没有取消')
  }
}

async function saveNote() {
  const selection = pendingSelection.value
  const body = noteBody.value.trim()
  if (!selection?.text || !body) {
    return
  }
  try {
    await createBookNote(props.book.id, {
      type: 'note',
      color: '',
      position: selection.position,
      text: selection.text,
      note_content: body,
    })
    noteOpen.value = false
    await loadNotes()
    sideTab.value = 'notes'
    showToast('已记下')
  } catch (error) {
    showToast(error.message || '没有记下')
  }
}

async function excerpt() {
  const selection = pendingSelection.value
  if (!selection?.text) {
    return
  }
  const title = (props.book.title || '未命名').replace(/#/g, '').trim() || '未命名'
  const quote = selection.text.replace(/\s+/g, ' ').trim().slice(0, 1700)
  const text = `${quote}\n—— 摘自《${title}》`.slice(0, 2000)
  try {
    await saveQuickNote(text, ['摘抄', title.slice(0, 24)])
    showToast('已摘抄到收件箱')
  } catch (error) {
    showToast(error.message || '没有摘抄')
  }
}

function visibleIndex() {
  const el = scroller.value
  const root = props.book.format === 'epub' ? htmlRoot.value : textRoot.value
  const length = root?.textContent?.length || content.value?.text?.length || 1
  const max = el ? el.scrollHeight - el.clientHeight : 0
  const ratio = !el || max <= 0 ? 0 : el.scrollTop / max
  return Math.min(length - 1, Math.max(0, Math.round(ratio * length)))
}

function stamp(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function askBookmark() {
  bookmarkNote.value = ''
  bookmarkOpen.value = true
}

async function addBookmark() {
  try {
    const index = visibleIndex()
    const position = props.book.format === 'epub' ? `${chapter.value}:${index}` : String(index)
    const source = props.book.format === 'epub' ? htmlRoot.value?.textContent || '' : content.value?.text || ''
    const created = await createBookNote(props.book.id, {
      type: 'bookmark',
      position,
      text: source.slice(index, index + 48),
      color: '',
      note_content: bookmarkNote.value.trim(),
    })
    bookmarkOpen.value = false
    await loadNotes()
    sideTab.value = 'bookmarks'
    activeBookmarkId.value = created.id
    showToast('已加书签')
  } catch (error) {
    showToast(error.message || '没有加书签')
  }
}

function scrollToIndex(index, root) {
  if (!root || !Number.isFinite(index)) {
    return
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let count = 0
  let node = walker.nextNode()
  while (node) {
    const next = count + node.textContent.length
    if (index < next) {
      ;(node.parentElement || root).scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    count = next
    node = walker.nextNode()
  }
}

const rendition = {
  async display(position) {
    const raw = String(position || '')
    if (props.book.format === 'epub' && raw.includes(':')) {
      const [chapterPart, indexPart] = raw.split(':')
      const nextChapter = Number(chapterPart)
      const charIndex = Number(indexPart)
      if (nextChapter !== chapter.value || !content.value) {
        await loadChapter(Number.isFinite(nextChapter) ? nextChapter : 0, 0)
      } else {
        paintHtmlMarks()
      }
      await nextTick()
      scrollToIndex(charIndex, htmlRoot.value)
      return
    }
    await nextTick()
    scrollToIndex(Number(raw), textRoot.value)
  },
}

async function focusNote(note) {
  activeBookmarkId.value = note.type === 'bookmark' ? note.id : activeBookmarkId.value
  await rendition.display(note.position)
  if (props.book.format === 'epub') {
    await nextTick()
    paintHtmlMarks()
    const span = noteSpan(note)
    scrollToIndex(span.start, htmlRoot.value)
  }
}

async function removeNote(note) {
  await deleteBookNote(props.book.id, note.id)
  await loadNotes()
}

async function openSystem() {
  openError.value = ''
  const api = window.pywebview?.api
  if (!api || typeof api.open_book !== 'function') {
    openError.value = '请在桌面窗口中使用系统应用打开'
    return
  }
  try {
    const ok = await api.open_book(props.book.id)
    if (!ok) {
      openError.value = '无法用系统应用打开'
    }
  } catch (error) {
    console.error('Failed to open PDF:', error)
    openError.value = '无法用系统应用打开'
  }
}

async function close() {
  await flushProgress()
  emit('close')
}

function onKey(event) {
  if (event.key === 'Escape') {
    if (noteOpen.value) {
      noteOpen.value = false
      return
    }
    if (bookmarkOpen.value) {
      bookmarkOpen.value = false
      return
    }
    close()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    detail.value = await getBook(props.book.id)
    if (props.book.format === 'pdf') {
      loading.value = false
      return
    }
    await loadNotes()
    const saved = detail.value.progress_cfi || ''
    if (props.book.format === 'epub' && saved.includes(':')) {
      loading.value = false
      await rendition.display(saved)
      return
    }
    await loadChapter(detail.value.progress_chapter || 0, detail.value.progress_offset || 0)
  } catch (error) {
    loading.value = false
    errorMessage.value = error.message || '无法打开这本书'
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.clearTimeout(timer)
  if (pending) {
    const body = pending
    pending = null
    updateBook(props.book.id, body).catch((error) => {
      console.error('Failed to save reading progress:', error)
    })
  }
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex flex-col bg-[#f7f3ea] text-ink">
    <header class="flex items-center gap-3 border-b border-black/10 px-5 py-3">
      <button type="button" class="h-10 rounded-md px-3 text-sm font-medium text-ink/70 hover:bg-black/5" @click="close">
        关闭
      </button>
      <div class="min-w-0 flex-1">
        <h2 class="truncate text-lg font-semibold">{{ book.title }}</h2>
        <p class="truncate text-xs text-ink/50">{{ book.author || '未知作者' }}</p>
      </div>
      <button
        v-if="book.format !== 'pdf'"
        type="button"
        class="h-10 rounded-md px-3 text-sm font-medium text-moss hover:bg-black/5"
        @click="askBookmark"
      >
        书签
      </button>
      <template v-if="book.format === 'epub' && toc.length">
        <button type="button" class="h-10 rounded-md px-3 text-sm font-medium text-moss disabled:text-ink/30" :disabled="chapter <= 0" @click="stepChapter(-1)">上一章</button>
        <button type="button" class="h-10 rounded-md px-3 text-sm font-medium text-moss disabled:text-ink/30" :disabled="chapter >= toc.length - 1" @click="stepChapter(1)">下一章</button>
      </template>
    </header>

    <p v-if="loading" class="px-8 py-10 text-sm text-ink/60">正在打开...</p>
    <p v-else-if="errorMessage" class="px-8 py-10 text-sm text-ember">{{ errorMessage }}</p>

    <div v-else-if="book.format === 'pdf'" class="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center">
      <p class="text-2xl font-semibold">{{ book.title }}</p>
      <p class="text-sm text-ink/60">{{ detail?.page_count || 0 }} 页 · PDF 用系统应用阅读</p>
      <button type="button" class="h-11 rounded-md bg-moss px-5 text-sm font-semibold text-white hover:bg-ink" @click="openSystem">
        用系统应用打开
      </button>
      <p v-if="openError" class="text-sm text-ember">{{ openError }}</p>
    </div>

    <div v-else class="flex min-h-0 flex-1">
      <aside class="flex w-72 shrink-0 flex-col bg-[#efeae1]">
        <div class="flex border-b border-black/10 text-xs">
          <button type="button" class="h-9 flex-1" :class="sideTab === 'toc' ? 'text-ink' : 'text-ink/40'" @click="sideTab = 'toc'">目录</button>
          <button type="button" class="h-9 flex-1" :class="sideTab === 'notes' ? 'text-ink' : 'text-ink/40'" @click="sideTab = 'notes'">笔记</button>
          <button type="button" class="h-9 flex-1" :class="sideTab === 'bookmarks' ? 'text-ink' : 'text-ink/40'" @click="sideTab = 'bookmarks'">书签</button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto p-2">
          <template v-if="sideTab === 'toc'">
            <button
              v-for="item in toc"
              :key="item.index"
              type="button"
              class="block w-full truncate px-2 py-1.5 text-left text-sm text-ink/80 hover:bg-black/5"
              @click="goTo(item.index)"
            >
              {{ item.title }}
            </button>
            <p v-if="!toc.length" class="px-2 py-3 text-xs text-ink/40">这本书没有目录</p>
          </template>
          <template v-else-if="sideTab === 'notes'">
            <div v-for="item in markNotes" :key="item.id" class="mb-2 bg-white/70 p-2">
              <button type="button" class="block w-full text-left" @click="focusNote(item)">
                <span class="block text-xs text-ink/40">{{ item.type === 'underline' ? '划线' : item.type === 'note' ? '笔记' : '高亮' }}</span>
                <span class="mt-1 block text-sm leading-5">{{ item.text }}</span>
                <span v-if="item.note_content" class="mt-1 block text-xs text-ink/60">{{ item.note_content }}</span>
              </button>
              <button type="button" class="mt-1 text-xs text-ink/35" @click="removeNote(item)">删除</button>
            </div>
            <p v-if="!markNotes.length" class="px-2 py-3 text-xs text-ink/40">选中文字后可以高亮或写笔记</p>
          </template>
          <template v-else>
            <div v-for="item in bookmarks" :key="item.id" class="mb-2 bg-[#fffcf7] p-3" :class="activeBookmarkId === item.id ? 'bg-[#fff1c9]' : ''">
              <button type="button" class="block w-full text-left" @click="focusNote(item)">
                <span class="block text-xs text-ink/50">{{ stamp(item.created_at) }}</span>
                <span class="mt-1 block text-sm font-semibold leading-5">{{ item.text || '这一处' }}</span>
                <span v-if="item.note_content" class="mt-1 block text-sm leading-5 text-ink/70">{{ item.note_content }}</span>
              </button>
              <button type="button" class="mt-2 text-sm text-[#9a4036]" @click="removeNote(item)">删除</button>
            </div>
            <p v-if="!bookmarks.length" class="px-2 py-3 text-sm text-ink/50">还没有书签。点右上角「书签」可以记下当前位置。</p>
          </template>
        </div>
      </aside>

      <div ref="scroller" class="reader-column min-h-0 flex-1 overflow-y-auto px-8 py-8" @scroll="onScroll" @mouseup="onMouseUp" @contextmenu="onTextMenu">
        <article v-if="book.format === 'epub'" ref="htmlRoot" class="reader-html mx-auto max-w-3xl text-base leading-8" />
        <div v-else ref="textRoot" class="mx-auto max-w-3xl whitespace-pre-wrap font-sans text-base leading-8"><span v-for="(piece, index) in textPieces" :key="`${index}-${piece.start}`" :class="pieceClass(piece.marks)">{{ piece.text }}</span></div>
      </div>
    </div>

    <div v-if="bookmarkOpen" class="fixed inset-0 z-[80] grid place-items-center bg-black/45 px-4">
      <div class="w-full max-w-md bg-[#fffcf7] p-6">
        <h3 class="text-xl font-semibold text-ink">给这个位置写一句备注</h3>
        <p class="mt-2 text-sm leading-6 text-ink/60">可以留空。书签会记下当前这一行，并按时间排在最上面。</p>
        <textarea v-model="bookmarkNote" class="mt-4 h-24 w-full bg-[#f3efe6] p-3 text-sm outline-none" maxlength="4000" placeholder="备注，可选" />
        <div class="mt-4 flex justify-end gap-2">
          <button type="button" class="h-9 rounded-md px-3 text-sm text-ink/70" @click="bookmarkOpen = false">取消</button>
          <button type="button" class="h-9 rounded-md bg-ink px-4 text-sm font-semibold text-white" @click="addBookmark">记下书签</button>
        </div>
      </div>
    </div>

    <div v-if="noteOpen" class="fixed inset-0 z-[80] grid place-items-center bg-black/45 px-4">
      <div class="w-full max-w-md bg-[#fcfaf5] p-5">
        <p class="text-sm text-ink">给这段文字写笔记</p>
        <p class="mt-2 line-clamp-3 text-xs text-ink/50">{{ pendingSelection?.text }}</p>
        <textarea v-model="noteBody" class="mt-3 h-28 w-full bg-white p-2 text-sm outline-none" maxlength="4000" placeholder="笔记" />
        <div class="mt-3 flex gap-2">
          <button type="button" class="h-8 rounded bg-ink px-3 text-xs text-white" @click="saveNote">保存</button>
          <button type="button" class="h-8 rounded px-3 text-xs text-ink/50" @click="noteOpen = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reader-html :deep(p) {
  margin: 0.85rem 0;
}

.reader-html :deep(img) {
  max-width: 100%;
  height: auto;
}

.reader-html :deep(h1),
.reader-html :deep(h2),
.reader-html :deep(h3) {
  margin-top: 1.4rem;
  font-weight: 650;
}

.reader-html :deep(mark),
.is-gold { background: #f3d36b; }
.is-moss { background: #9dceb0; }
.is-sky { background: #9ec0ee; }
.is-rose { background: #f3b4c8; }
.is-line { text-decoration: underline; text-underline-offset: 3px; background: transparent; }
.is-line-gold { text-decoration-color: #c4922a; }
.is-line-moss { text-decoration-color: #2f6a48; }
.is-line-sky { text-decoration-color: #2d5eaa; }
.is-line-rose { text-decoration-color: #b14b73; }
.is-bookmark { background: #ffe08a; }
.reader-column,
.reader-column :deep(*) {
  cursor: auto;
  -webkit-user-select: text;
  user-select: text;
}
</style>
