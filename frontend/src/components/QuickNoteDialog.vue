<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'

import { getQuickTags, saveQuickNote, saveQuickTags } from '../api/client'

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
const draft = ref('')
const input = ref(null)
const errorMessage = ref('')
const saving = ref(false)

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      return
    }
    text.value = ''
    picked.value = []
    draft.value = ''
    errorMessage.value = ''
    try {
      const payload = await getQuickTags()
      quickTags.value = payload.tags || []
    } catch {
      quickTags.value = ['工作', '生活', '灵感', '待办']
    }
    nextTick(() => input.value?.focus())
  },
)

onMounted(() => {})

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
  if (!picked.value.includes(name)) {
    if (picked.value.length >= 3) {
      errorMessage.value = '最多三个标签'
      return
    }
    picked.value = [...picked.value, name]
  }
  errorMessage.value = ''
  if (quickTags.value.includes(name) || quickTags.value.length >= 6) {
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
      <div class="mt-2 flex flex-wrap gap-1">
        <button
          v-for="name in quickTags"
          :key="name"
          type="button"
          class="h-7 rounded px-2 text-xs"
          :class="picked.includes(name) ? 'bg-aurora text-white' : 'bg-black/5 text-ink/70'"
          @click="toggleTag(name)"
        >
          {{ name }}
        </button>
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
