<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, ref, watch } from 'vue'

import { openExternalLink } from '../openExternal.js'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'delete'])

const isEditing = ref(false)
const draft = ref('')
const editor = ref(null)

const renderedHtml = computed(() => {
  const text = props.block.content?.text || ''
  return DOMPurify.sanitize(marked.parse(text, { async: false }))
})

watch(
  () => props.block.id,
  () => {
    isEditing.value = false
    draft.value = props.block.content?.text || ''
  },
  { immediate: true },
)

// 进入编辑并把当前正文放进 textarea。
// Enter edit mode and copy the current text into the textarea.
function startEdit() {
  draft.value = props.block.content?.text || ''
  isEditing.value = true
}

// 保存 Markdown 正文。
// Save the Markdown body.
function save() {
  const text = editor.value?.value ?? draft.value
  draft.value = text
  emit('save', { text })
  isEditing.value = false
}

function cancel() {
  draft.value = props.block.content?.text || ''
  isEditing.value = false
}

function confirmDelete() {
  if (window.confirm('确定删除这个 Markdown 区块吗？')) {
    emit('delete')
  }
}

// 展示态里的链接走系统浏览器 / window.open。
// Route rendered-link clicks through the system browser / window.open.
function onContentClick(event) {
  const anchor = event.target.closest('a')
  if (!anchor || !anchor.href) {
    return
  }
  event.preventDefault()
  openExternalLink(anchor.href)
}
</script>

<template>
  <article class="rounded-md border border-black/10 bg-white/80 p-4 shadow-sm">
    <div class="mb-3 flex items-center justify-between gap-3">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-moss">Markdown</p>
      <div class="flex gap-1">
        <button type="button" class="grid h-8 w-8 place-items-center rounded-md hover:bg-black/5" title="编辑" @click="startEdit">
          ✏️
        </button>
        <button type="button" class="grid h-8 w-8 place-items-center rounded-md hover:bg-black/5" title="删除" @click="confirmDelete">
          🗑️
        </button>
      </div>
    </div>

    <textarea
      v-if="isEditing"
      ref="editor"
      v-model="draft"
      class="min-h-48 w-full rounded-md border border-black/15 bg-white p-3 text-sm leading-6 outline-none focus:border-moss"
      @keydown.ctrl.enter="save"
    />
    <div
      v-else
      class="prose-block min-h-16 cursor-text text-sm leading-7 text-ink/80"
      @click="onContentClick"
      @dblclick="startEdit"
      v-html="renderedHtml || '<p class=&quot;text-ink/40&quot;>双击或点编辑，开始写点什么。</p>'"
    />

    <div v-if="isEditing" class="mt-3 flex justify-end gap-2">
      <button type="button" class="h-9 rounded-md px-3 text-sm text-ink/70 hover:bg-black/5" @click="cancel">取消</button>
      <button type="button" class="h-9 rounded-md bg-moss px-4 text-sm font-semibold text-white hover:bg-ink" @click="save">保存</button>
    </div>
  </article>
</template>
