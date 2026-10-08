<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, ref, watch } from 'vue'

import { useQueuedSave } from '../blocks/queuedSave.js'
import { openExternalLink } from '../openExternal.js'

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

const text = ref('')
const mode = ref('split')

function readContent() {
  return { text: text.value }
}

const { queue, flush } = useQueuedSave(emit, readContent, 500)

const renderedHtml = computed(() => DOMPurify.sanitize(marked.parse(text.value || '', { async: false })))

function viewKey(id) {
  return `wv.doc.view.${id}`
}

function applyBlock(block) {
  text.value = block.content?.text || ''
  try {
    const stored = localStorage.getItem(viewKey(block.id))
    mode.value = MODES.some((item) => item.id === stored) ? stored : 'split'
  } catch {
    mode.value = 'split'
  }
}

watch(
  () => props.block.id,
  (_id, previous) => {
    if (previous != null) {
      flush()
    }
    applyBlock(props.block)
  },
  { immediate: true },
)

function onInput(value) {
  text.value = value
  queue(props.block.id)
}

function chooseMode(next) {
  mode.value = next
  try {
    localStorage.setItem(viewKey(props.block.id), next)
  } catch {
    // 视图偏好写失败时，这次切换仍然生效。
  }
}

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
  <div class="flex min-h-full flex-col">
    <div class="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-black/10 bg-[#fcfaf5]/95 px-6 py-2 backdrop-blur-sm">
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
      <p class="text-xs text-ink/40">自动保存</p>
    </div>

    <div class="grid min-h-0 flex-1" :class="mode === 'split' ? 'lg:grid-cols-2' : 'grid-cols-1'">
      <textarea
        v-show="mode !== 'preview'"
        :value="text"
        class="doc-editor min-h-[70vh] w-full resize-none border-0 bg-transparent px-8 py-7 outline-none"
        :class="mode === 'split' ? 'lg:border-r lg:border-black/10' : ''"
        placeholder="从这里开始写。右侧会按 Markdown 排版。"
        @input="onInput($event.target.value)"
      />
      <article
        v-show="mode !== 'edit'"
        class="doc-prose min-h-[70vh] px-8 py-7"
        @click="onContentClick"
        v-html="renderedHtml || '<p class=&quot;doc-empty&quot;>还没有文字。切到编辑或分栏开始写。</p>'"
      />
    </div>
  </div>
</template>
