<script setup>
import { computed, nextTick, ref, watch } from 'vue'

import { searchLibrary } from '../api/client'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  initialQuery: {
    type: String,
    default: '',
  },
  initialTab: {
    type: String,
    default: 'all',
  },
})

const emit = defineEmits(['close', 'open-nav'])

const TABS = [
  { id: 'all', label: '全部' },
  { id: 'flex', label: '积木页' },
  { id: 'focus', label: '专页' },
  { id: 'core', label: '系统页' },
]
const LAYER_LABEL = { flex: '积木', focus: '专页', core: '系统' }

const query = ref('')
const tab = ref('all')
const input = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const rows = ref([])
let timer = null
let requestId = 0

const hits = computed(() =>
  rows.value.filter((item) => {
    if (tab.value === 'all') {
      return item.matched !== 'tag'
    }
    if (item.layer !== tab.value) {
      return false
    }
    if (tab.value === 'focus') {
      return true
    }
    return item.matched !== 'tag'
  }),
)

watch(
  () => props.open,
  (open) => {
    if (!open) {
      return
    }
    query.value = props.initialQuery || ''
    tab.value = TABS.some((item) => item.id === props.initialTab) ? props.initialTab : 'all'
    rows.value = []
    errorMessage.value = ''
    nextTick(() => {
      input.value?.focus()
      if (query.value.trim()) {
        schedule()
      }
    })
  },
)

function schedule() {
  clearTimeout(timer)
  const text = query.value.trim()
  if (!text) {
    rows.value = []
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
    rows.value = payload.nav || []
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

const nameHits = computed(() => hits.value.filter((item) => item.matched !== 'tag'))
const tagHits = computed(() => (tab.value === 'focus' ? hits.value.filter((item) => item.matched === 'tag') : []))

function pick(item) {
  emit('open-nav', { groupId: item.group_id, navId: item.id })
  emit('close')
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[70] grid place-items-start bg-black/35 px-4 pt-[12vh]" @click.self="emit('close')" @keydown.esc.prevent="emit('close')">
    <div class="w-full max-w-xl rounded-md bg-[#fcfaf5] p-4 shadow-2xl">
      <input
        ref="input"
        v-model="query"
        type="text"
        class="h-11 w-full rounded border border-black/10 bg-white px-3 text-sm outline-none"
        placeholder="搜索页面名称"
        @input="schedule"
      />
      <div class="mt-2 flex gap-1">
        <button
          v-for="item in TABS"
          :key="item.id"
          type="button"
          class="h-7 rounded px-2 text-xs"
          :class="tab === item.id ? 'bg-white text-ink shadow-sm' : 'text-ink/50'"
          @click="tab = item.id"
        >
          {{ item.label }}
        </button>
      </div>
      <p v-if="loading" class="mt-3 text-xs text-ink/45">正在找…</p>
      <p v-else-if="errorMessage" class="mt-3 text-xs text-ember">{{ errorMessage }}</p>
      <p v-else-if="query.trim() && !nameHits.length && !tagHits.length" class="mt-3 text-xs text-ink/45">没有匹配</p>
      <button
        v-for="item in nameHits"
        :key="`name-${item.id}`"
        type="button"
        class="mt-1 flex w-full items-start gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-white"
        @mousedown.prevent
        @click="pick(item)"
      >
        <span class="shrink-0 text-xs text-ink/45">{{ LAYER_LABEL[item.layer] || '页' }}</span>
        <span class="min-w-0">
          <span class="block truncate">{{ item.icon }} {{ item.title }}</span>
          <span class="block truncate text-xs text-ink/45">{{ item.path }}</span>
        </span>
      </button>
      <div v-if="tab === 'focus' && tagHits.length" class="mt-3 border-t border-aurora/40 pt-2">
        <p class="mb-1 text-xs text-aurora">标签</p>
        <button
          v-for="item in tagHits"
          :key="`tag-${item.id}`"
          type="button"
          class="mt-1 flex w-full items-start gap-2 rounded bg-aurora/10 px-2 py-1.5 text-left text-sm hover:bg-aurora/15"
          @mousedown.prevent
          @click="pick(item)"
        >
          <span class="shrink-0 text-xs text-aurora">专页</span>
          <span class="min-w-0">
            <span class="block truncate">{{ item.icon }} {{ item.title }}</span>
            <span class="block truncate text-xs text-aurora/80">{{ (item.tags || []).map((tag) => `#${tag}`).join(' ') }}</span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>
