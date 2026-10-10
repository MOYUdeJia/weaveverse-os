<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'

import { getQuickTags, saveQuickNote, saveQuickTags } from '../api/client'
import { showToast } from '../toast'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'saved'])

const text = ref('')
const picked = ref([])
const quickTags = ref([])
const history = ref([])
const historyOpen = ref(false)
const draft = ref('')
const input = ref(null)
const tagRow = ref(null)
const errorMessage = ref('')
const saving = ref(false)
const tagOverflow = ref(false)

function measureTags() {
  const row = tagRow.value
  tagOverflow.value = Boolean(row && row.scrollWidth > row.clientWidth + 2)
}

function slideTags(direction) {
  tagRow.value?.scrollBy({ left: direction * 120, behavior: 'smooth' })
}

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      return
    }
    text.value = ''
    picked.value = []
    draft.value = ''
    historyOpen.value = false
    errorMessage.value = ''
    try {
      const payload = await getQuickTags()
      quickTags.value = payload.common || payload.tags || []
      history.value = payload.history || []
    } catch {
      quickTags.value = ['工作', '生活', '灵感', '待办']
      history.value = []
    }
    nextTick(() => {
      input.value?.focus()
      measureTags()
    })
  },
)

watch(quickTags, () => nextTick(measureTags))

function toggleTag(name) {
  if (picked.value.includes(name)) {
    picked.value = picked.value.filter((tag) => tag !== name)
    errorMessage.value = ''
    return
  }
  if (picked.value.length >= 3) {
    errorMessage.value = '最多三个标签'
    return
  }
  errorMessage.value = ''
  picked.value = [...picked.value, name]
}

function addDraft() {
  const name = draft.value.trim().replace(/^#/, '')
  draft.value = ''
  if (!name) {
    return
  }
  if (picked.value.includes(name) || quickTags.value.includes(name)) {
    showToast('已存在')
  }
  if (!picked.value.includes(name)) {
    if (picked.value.length >= 3) {
      errorMessage.value = '最多三个标签'
      return
    }
    picked.value = [...picked.value, name]
  }
  errorMessage.value = ''
  if (quickTags.value.includes(name)) {
    return
  }
  if (quickTags.value.length >= 6) {
    showToast('最多 6 个常用标签，可先删一个')
    return
  }
  const next = [...quickTags.value, name]
  quickTags.value = next
  saveQuickTags(next).catch((error) => console.error(error))
}

function promote(name) {
  if (quickTags.value.includes(name)) {
    showToast('已存在')
    return
  }
  if (quickTags.value.length >= 6) {
    showToast('最多 6 个常用标签，可先删一个')
    return
  }
  const next = [...quickTags.value, name]
  quickTags.value = next
  saveQuickTags(next).catch((error) => console.error(error))
}

async function save() {
  const note = text.value.trim()
  if (!note || saving.value) {
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    const saved = await saveQuickNote(note, picked.value)
    emit('saved', saved)
    emit('close')
  } catch (error) {
    errorMessage.value = error.message || '没记下来'
  } finally {
    saving.value = false
  }
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
    return
  }
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    save()
  }
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[70] grid place-items-start bg-black/35 px-4 pt-[14vh]" @click.self="emit('close')">
    <form class="w-full max-w-lg rounded-md bg-[#fcfaf5] p-4 shadow-2xl" @submit.prevent="save">
      <p class="text-sm font-medium text-ink">速记</p>
      <textarea
        ref="input"
        v-model="text"
        rows="4"
        class="mt-2 w-full resize-none rounded border border-black/10 bg-white px-3 py-2 text-sm outline-none"
        placeholder="写一条。Enter 保存，最多三个标签"
        @keydown="onKeydown"
      />
      <div class="mt-2 flex items-center gap-1">
        <button
          v-if="tagOverflow"
          type="button"
          class="grid h-7 w-7 shrink-0 place-items-center rounded bg-black/5 text-sm text-ink/55"
          title="向左"
          @click="slideTags(-1)"
        >
          ‹
        </button>
        <div ref="tagRow" class="flex min-w-0 flex-1 gap-1 overflow-x-auto" @scroll="measureTags">
          <button
            v-for="name in quickTags"
            :key="name"
            type="button"
            class="h-7 shrink-0 rounded px-2 text-xs"
            :class="picked.includes(name) ? 'bg-aurora text-white' : 'bg-black/5 text-ink/70'"
            @click="toggleTag(name)"
          >
            {{ name }}
          </button>
        </div>
        <button
          v-if="tagOverflow"
          type="button"
          class="grid h-7 w-7 shrink-0 place-items-center rounded bg-black/5 text-sm text-ink/55"
          title="向右"
          @click="slideTags(1)"
        >
          ›
        </button>
        <button type="button" class="h-7 shrink-0 rounded bg-black/5 px-2 text-xs text-ink/70" @click="historyOpen = !historyOpen">
          历史
        </button>
      </div>
      <div v-if="historyOpen" class="mt-2 max-h-28 overflow-y-auto rounded bg-black/[0.03] p-2">
        <p v-if="!history.length" class="text-xs text-ink/45">还没有用过的标签</p>
        <div v-for="name in history" :key="name" class="flex items-center justify-between gap-2 py-0.5">
          <button type="button" class="truncate text-left text-xs text-ink/80" @click="toggleTag(name)">#{{ name }}</button>
          <button type="button" class="shrink-0 text-[11px] text-aurora" @click="promote(name)">设为常用</button>
        </div>
      </div>
      <div class="mt-2 flex gap-2">
        <input
          v-model="draft"
          class="h-8 min-w-0 flex-1 rounded border border-black/10 bg-white px-2 text-xs outline-none"
          maxlength="24"
          placeholder="加一个标签，回车。最多三个"
          @keydown.enter.prevent="addDraft"
        />
        <button type="button" class="h-8 rounded bg-black/5 px-3 text-xs text-ink/70" @click="addDraft">添加</button>
      </div>
      <p v-if="picked.length" class="mt-2 text-xs text-aurora">{{ picked.map((tag) => `#${tag}`).join(' ') }}</p>
      <p v-if="errorMessage" class="mt-2 text-xs text-ember">{{ errorMessage }}</p>
      <div class="mt-3 flex justify-end gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs text-ink/55" @click="emit('close')">取消</button>
        <button type="submit" class="h-8 rounded bg-ink px-3 text-xs font-medium text-white" :disabled="saving">保存</button>
      </div>
    </form>
  </div>
</template>
