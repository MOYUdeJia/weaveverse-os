<script setup>
import { computed, ref, watch } from 'vue'

import { deleteBook, listBooks, uploadBook } from '../api/client'
import BookCover from './BookCover.vue'
import BookReader from './BookReader.vue'

const SLOW_UPLOAD_BYTES = 50 * 1024 * 1024

defineProps({
  title: {
    type: String,
    default: '书架',
  },
  icon: {
    type: String,
    default: '📚',
  },
  noticeMessage: {
    type: String,
    default: '',
  },
})

const books = ref([])
const sort = ref('recent')
const format = ref('')
const loading = ref(true)
const errorMessage = ref('')
const uploadHint = ref('')
const importing = ref(false)
const fileInput = ref(null)
const activeBook = ref(null)

const sortOptions = [
  { value: 'recent', label: '最近阅读' },
  { value: 'title', label: '书名' },
  { value: 'added', label: '添加时间' },
]
const formatOptions = [
  { value: '', label: '全部' },
  { value: 'epub', label: 'EPUB' },
  { value: 'txt', label: 'TXT' },
  { value: 'pdf', label: 'PDF' },
]

const recentBooks = computed(() =>
  books.value
    .filter((book) => book.last_read_at)
    .slice()
    .sort((a, b) => String(b.last_read_at).localeCompare(String(a.last_read_at))),
)

function percent(book) {
  return Math.round((book.progress_ratio || 0) * 100)
}

async function loadBooks() {
  loading.value = true
  errorMessage.value = ''
  try {
    books.value = await listBooks(sort.value, format.value)
  } catch (error) {
    console.error('Failed to load books:', error)
    errorMessage.value = error.message || '无法加载书架'
  } finally {
    loading.value = false
  }
}

function desktopApi() {
  const api = window.pywebview?.api
  if (api && typeof api.pick_book_file === 'function' && typeof api.import_picked_book === 'function') {
    return api
  }
  return null
}

async function finishImport() {
  const unchanged = sort.value === 'recent' && format.value === ''
  sort.value = 'recent'
  format.value = ''
  if (unchanged) {
    await loadBooks()
  }
}

async function importFromBrowser(file) {
  uploadHint.value = file.size > SLOW_UPLOAD_BYTES ? '这个文件超过 50MB，上传较慢' : ''
  importing.value = true
  try {
    await uploadBook(file)
    await finishImport()
  } catch (error) {
    console.error('Failed to import book:', error)
    alert(error.message || '导入失败')
  } finally {
    importing.value = false
  }
}

async function importBook() {
  const api = desktopApi()
  if (!api) {
    fileInput.value?.click()
    return
  }

  importing.value = true
  uploadHint.value = ''
  try {
    const picked = await api.pick_book_file()
    if (!picked) {
      return
    }
    if (picked.error) {
      alert(picked.error)
      return
    }
    if (picked.size > SLOW_UPLOAD_BYTES) {
      uploadHint.value = '这个文件超过 50MB，上传较慢'
    }
    const imported = await api.import_picked_book()
    if (imported?.error) {
      alert(imported.error)
      return
    }
    await finishImport()
  } catch (error) {
    console.error('Failed to import book from the desktop dialog:', error)
    alert(error.message || '导入失败')
  } finally {
    importing.value = false
  }
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (file) {
    importFromBrowser(file)
  }
}

async function removeBook(book, event) {
  event.stopPropagation()
  if (!window.confirm(`确定删除《${book.title}》吗？`)) {
    return
  }
  try {
    await deleteBook(book.id)
    if (activeBook.value?.id === book.id) {
      activeBook.value = null
    }
    books.value = books.value.filter((item) => item.id !== book.id)
  } catch (error) {
    console.error('Failed to delete book:', error)
    alert(error.message || '删除失败')
  }
}

function applyProgress(updated) {
  books.value = books.value.map((item) => (item.id === updated.id ? { ...item, ...updated } : item))
  if (activeBook.value?.id === updated.id) {
    activeBook.value = { ...activeBook.value, ...updated }
  }
}

watch([sort, format], loadBooks, { immediate: true })
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-8 py-8">
    <div class="mx-auto flex w-full max-w-6xl flex-col">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="flex items-center gap-4">
          <span class="grid h-14 w-14 place-items-center rounded-md bg-dawn text-3xl shadow-sm">{{ icon }}</span>
          <div>
            <p class="text-sm font-semibold uppercase tracking-[0.28em] text-aurora">Bookshelf</p>
            <h2 class="mt-1 text-4xl font-semibold text-ink">{{ title }}</h2>
          </div>
        </div>
        <button
          type="button"
          class="h-11 rounded-md bg-moss px-5 text-sm font-semibold text-white hover:bg-ink disabled:bg-ink/30"
          :disabled="importing"
          @click="importBook"
        >
          {{ importing ? '请稍候...' : '导入书籍' }}
        </button>
        <input
          ref="fileInput"
          class="hidden"
          type="file"
          accept=".epub,.txt,.pdf,application/epub+zip,application/pdf,text/plain"
          @change="onFileChange"
        />
      </div>

      <p v-if="noticeMessage" class="mt-4 rounded-md border border-moss/25 bg-moss/10 px-4 py-3 text-sm text-moss">
        {{ noticeMessage }}
      </p>
      <p v-if="uploadHint" class="mt-4 rounded-md border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ember">
        {{ uploadHint }}
      </p>
      <p v-if="errorMessage" class="mt-4 text-sm text-ember">{{ errorMessage }}</p>
      <p v-else-if="loading" class="mt-8 text-sm text-ink/60">正在加载书架...</p>

      <template v-else>
        <div v-if="books.length > 0 || format" class="mt-6 flex flex-wrap items-center gap-3">
          <label class="text-sm text-ink/60" for="book-sort">排序</label>
          <select id="book-sort" v-model="sort" class="h-10 rounded-md border border-black/15 bg-white px-3 text-sm">
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
          <div class="flex gap-2">
            <button
              v-for="option in formatOptions"
              :key="option.value || 'all'"
              type="button"
              class="h-10 rounded-md px-3 text-sm font-medium"
              :class="format === option.value ? 'bg-moss text-white' : 'bg-white text-ink/70'"
              @click="format = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <p v-if="books.length === 0" class="mt-10 text-lg text-ink/70">
          {{ format ? '没有符合条件的书。' : '书架还是空的。点「导入书籍」放入 EPUB、TXT 或 PDF。' }}
        </p>

        <section v-if="books.length > 0" class="mt-8">
          <h3 class="text-sm font-semibold tracking-wide text-ink/50">最近阅读</h3>
          <p v-if="recentBooks.length === 0" class="mt-3 text-sm text-ink/50">还没有读过的书。</p>
          <div v-else class="mt-3 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
            <article
              v-for="book in recentBooks"
              :key="`recent-${book.id}`"
              class="cursor-pointer rounded-md bg-white p-3 shadow-sm"
              @click="activeBook = book"
            >
              <BookCover :book="book" />
              <h4 class="mt-3 truncate text-base font-semibold">{{ book.title }}</h4>
              <p class="truncate text-xs text-ink/50">{{ book.author || '未知作者' }}</p>
              <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-black/10">
                <div class="h-full bg-moss" :style="{ width: `${percent(book)}%` }" />
              </div>
            </article>
          </div>
        </section>

        <section v-if="books.length > 0" class="mt-10">
          <h3 class="text-sm font-semibold tracking-wide text-ink/50">全部书籍</h3>
          <div class="mt-3 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
            <article
              v-for="book in books"
              :key="book.id"
              class="cursor-pointer rounded-md bg-white p-3 shadow-sm"
              @click="activeBook = book"
            >
              <BookCover :book="book" />
              <div class="mt-3 flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <h4 class="truncate text-base font-semibold">{{ book.title }}</h4>
                  <p class="truncate text-xs text-ink/50">{{ book.author || '未知作者' }} · {{ book.format.toUpperCase() }}</p>
                </div>
                <button type="button" class="shrink-0 text-xs text-ink/40 hover:text-ember" @click="removeBook(book, $event)">
                  删除
                </button>
              </div>
              <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-black/10">
                <div class="h-full bg-moss" :style="{ width: `${percent(book)}%` }" />
              </div>
              <p class="mt-1 text-right text-xs text-ink/40">{{ percent(book) }}%</p>
            </article>
          </div>
        </section>
      </template>
    </div>

    <BookReader v-if="activeBook" :book="activeBook" @close="activeBook = null" @progress="applyProgress" />
  </div>
</template>
