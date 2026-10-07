<script setup>
import DOMPurify from 'dompurify'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import { getBook, getBookContent, updateBook } from '../api/client'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close', 'progress'])

const detail = ref(null)
const content = ref(null)
const chapter = ref(0)
const loading = ref(true)
const errorMessage = ref('')
const openError = ref('')
const scroller = ref(null)
let suspendScroll = false
let pending = null
let timer = 0

const safeHtml = computed(() => DOMPurify.sanitize(content.value?.html || ''))
const toc = computed(() => detail.value?.toc ?? [])

// 节流把阅读位置写回书架。切章时立刻保存。
// Throttle reading position writes. Chapter changes flush immediately.
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

async function loadChapter(index, offset) {
  suspendScroll = true
  loading.value = true
  errorMessage.value = ''
  try {
    chapter.value = index
    content.value = await getBookContent(props.book.id, index)
    await nextTick()
    restoreScroll(offset)
  } catch (error) {
    errorMessage.value = error.message || '无法打开这一章'
  } finally {
    loading.value = false
    await nextTick()
    suspendScroll = false
  }
}

async function goTo(index) {
  if (index === chapter.value || index < 0 || index >= toc.value.length) {
    return
  }
  await loadChapter(index, 0)
  queueProgress({ progress_chapter: index, progress_offset: 0 }, true)
}

function onScroll(event) {
  if (suspendScroll || props.book.format === 'pdf') {
    return
  }
  const el = event.target
  const max = el.scrollHeight - el.clientHeight
  const offset = max <= 0 ? 0 : el.scrollTop / max
  queueProgress({ progress_offset: Number(offset.toFixed(6)) })
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
      <template v-if="book.format === 'epub' && toc.length">
        <button
          type="button"
          class="h-10 rounded-md px-3 text-sm font-medium text-moss disabled:text-ink/30"
          :disabled="chapter <= 0"
          @click="goTo(chapter - 1)"
        >
          上一章
        </button>
        <select
          class="h-10 max-w-xs rounded-md border border-black/15 bg-white px-2 text-sm"
          :value="chapter"
          @change="goTo(Number($event.target.value))"
        >
          <option v-for="item in toc" :key="item.index" :value="item.index">{{ item.title }}</option>
        </select>
        <button
          type="button"
          class="h-10 rounded-md px-3 text-sm font-medium text-moss disabled:text-ink/30"
          :disabled="chapter >= toc.length - 1"
          @click="goTo(chapter + 1)"
        >
          下一章
        </button>
      </template>
    </header>

    <p v-if="loading" class="px-8 py-10 text-sm text-ink/60">正在打开...</p>
    <p v-else-if="errorMessage" class="px-8 py-10 text-sm text-ember">{{ errorMessage }}</p>

    <div
      v-else-if="book.format === 'pdf'"
      class="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center"
    >
      <p class="text-2xl font-semibold">{{ book.title }}</p>
      <p class="text-sm text-ink/60">{{ detail?.page_count || 0 }} 页 · PDF 用系统应用阅读</p>
      <button type="button" class="h-11 rounded-md bg-moss px-5 text-sm font-semibold text-white hover:bg-ink" @click="openSystem">
        用系统应用打开
      </button>
      <p v-if="openError" class="text-sm text-ember">{{ openError }}</p>
    </div>

    <div v-else ref="scroller" class="flex-1 overflow-y-auto px-8 py-8" @scroll="onScroll">
      <article
        v-if="book.format === 'epub'"
        class="reader-html mx-auto max-w-3xl text-base leading-8"
        v-html="safeHtml"
      />
      <pre v-else class="mx-auto max-w-3xl whitespace-pre-wrap font-sans text-base leading-8">{{ content?.text || '' }}</pre>
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
</style>
