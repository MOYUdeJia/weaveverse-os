<script setup>
import { nextTick, ref, watch } from 'vue'

import { saveQuickNote } from '../api/client'

const CATEGORIES = ['工作', '生活', '想法', '待办']

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'saved'])

const text = ref('')
const category = ref('')
const input = ref(null)
const errorMessage = ref('')
const saving = ref(false)

watch(
  () => props.open,
  (open) => {
    if (!open) {
      return
    }
    text.value = ''
    category.value = ''
    errorMessage.value = ''
    nextTick(() => input.value?.focus())
  },
)

function toggleCategory(name) {
  category.value = category.value === name ? '' : name
}

async function save() {
  const note = text.value.trim()
  if (!note || saving.value) {
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    const saved = await saveQuickNote(note, category.value)
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
        placeholder="写一条。Enter 保存，Shift+Enter 换行，也可以直接写 #标签"
        @keydown="onKeydown"
      />
      <div class="mt-2 flex flex-wrap gap-1">
        <button
          v-for="name in CATEGORIES"
          :key="name"
          type="button"
          class="h-7 rounded px-2 text-xs"
          :class="category === name ? 'bg-moss text-white' : 'bg-black/5 text-ink/70'"
          @click="toggleCategory(name)"
        >
          #{{ name }}
        </button>
      </div>
      <p v-if="errorMessage" class="mt-2 text-xs text-ember">{{ errorMessage }}</p>
      <div class="mt-3 flex justify-end gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs text-ink/55" @click="emit('close')">取消</button>
        <button type="submit" class="h-8 rounded bg-ink px-3 text-xs font-medium text-white" :disabled="saving">保存</button>
      </div>
    </form>
  </div>
</template>
