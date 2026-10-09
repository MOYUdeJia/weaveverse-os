<script setup>
import { nextTick, ref, watch } from 'vue'

import { searchLibrary } from '../api/client'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'open-nav', 'open-group'])

const query = ref('')
const input = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const result = ref({ nav: [], groups: [], books: [], blocks: [] })
let timer = null
let requestId = 0

const sections = [
  { key: 'nav', label: '导航' },
  { key: 'groups', label: '分组' },
  { key: 'books', label: '书籍' },
  { key: 'blocks', label: '内容' },
]

watch(
  () => props.open,
  (open) => {
    if (!open) {
      return
    }
    query.value = ''
    result.value = { nav: [], groups: [], books: [], blocks: [] }
    errorMessage.value = ''
    nextTick(() => input.value?.focus())
  },
)

function schedule() {
  clearTimeout(timer)
  const text = query.value.trim()
  if (!text) {
    result.value = { nav: [], groups: [], books: [], blocks: [] }
    loading.value = false
    return
  }
  timer = setTimeout(() => run(text), 300)
}

async function run(text) {
  const current = ++requestId
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await searchLibrary(text)
    if (current !== requestId) {
      return
    }
    result.value = payload
  } catch (error) {
    if (current !== requestId) {
      return
    }
    errorMessage.value = error.message || '搜索失败'
  } finally {
    if (current === requestId) {
      loading.value = false
    }
  }
}

function pickNav(item) {
  emit('open-nav', { groupId: item.group_id, navId: item.id })
  emit('close')
}

function pickGroup(item) {
  emit('open-group', item.id)
  emit('close')
}

function pickBook(item) {
  if (item.nav_id == null) {
    return
  }
  emit('open-nav', { groupId: item.group_id, navId: item.nav_id })
  emit('close')
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[70] grid place-items-start bg-black/35 px-4 pt-[12vh]" @click.self="emit('close')">
    <div class="w-full max-w-xl rounded-md bg-[#fcfaf5] p-4 shadow-2xl" @keydown="onKeydown">
      <input
        ref="input"
        v-model="query"
        type="text"
        class="h-11 w-full rounded border border-black/10 bg-white px-3 text-sm outline-none"
        placeholder="搜索导航、分组、书籍、正文"
        @input="schedule"
      />
      <p v-if="loading" class="mt-3 text-xs text-ink/45">正在找…</p>
      <p v-else-if="errorMessage" class="mt-3 text-xs text-ember">{{ errorMessage }}</p>
      <p v-else-if="query.trim() && !sections.some((item) => result[item.key]?.length)" class="mt-3 text-xs text-ink/45">没有匹配</p>
      <div v-for="section in sections" :key="section.key" class="mt-3">
        <template v-if="result[section.key]?.length">
          <p class="mb-1 text-xs font-medium text-ink/45">{{ section.label }}</p>
          <button
            v-for="item in result[section.key]"
            :key="`${section.key}-${item.id || item.block_id}`"
            type="button"
            class="flex w-full items-start gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-white"
            @click="section.key === 'groups' ? pickGroup(item) : section.key === 'books' ? pickBook(item) : pickNav(item)"
          >
            <span class="shrink-0">{{ item.icon || (section.key === 'books' ? '📚' : '•') }}</span>
            <span class="min-w-0">
              <span class="block truncate">{{ item.title || item.name }}</span>
              <span v-if="section.key === 'books' && item.author" class="block truncate text-xs text-ink/45">{{ item.author }}</span>
              <span v-if="section.key === 'blocks'" class="block truncate text-xs text-ink/45">{{ item.snippet }}</span>
            </span>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
