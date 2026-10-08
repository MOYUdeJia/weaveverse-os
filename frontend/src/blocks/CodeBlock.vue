<script setup>
import { computed, ref, watch } from 'vue'

import BlockShell from './BlockShell.vue'
import { highlightCode } from './highlight.js'
import { useQueuedSave } from './queuedSave.js'

const LANGUAGES = [
  { value: 'plain', label: '纯文本' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'python', label: 'Python' },
  { value: 'json', label: 'JSON' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'sql', label: 'SQL' },
  { value: 'markdown', label: 'Markdown' },
]

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'delete'])

const language = ref('plain')
const text = ref('')
const highlight = ref(false)

function readContent() {
  return {
    language: language.value,
    text: text.value,
    highlight: highlight.value,
  }
}

const { queue, flush } = useQueuedSave(emit, readContent)

const highlighted = computed(() => (highlight.value ? highlightCode(text.value, language.value) : ''))

function applyBlock(block) {
  language.value = block.content?.language || 'plain'
  text.value = block.content?.text || ''
  highlight.value = Boolean(block.content?.highlight)
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

function onTextInput(value) {
  text.value = value
  queue(props.block.id)
}

function onLanguage(value) {
  language.value = value
  queue(props.block.id)
  flush()
}

function onHighlight(checked) {
  highlight.value = checked
  queue(props.block.id)
  flush()
}

function confirmDelete() {
  if (window.confirm('确定删除这个代码区块吗？')) {
    emit('delete')
  }
}
</script>

<template>
  <BlockShell title="代码" :block-id="block.id" @delete="confirmDelete">
    <div class="mb-1.5 flex flex-wrap items-center gap-2">
      <select
        :value="language"
        class="h-8 rounded-md border border-black/15 bg-white px-2 font-mono text-xs outline-none focus:border-moss"
        @change="onLanguage($event.target.value)"
      >
        <option v-for="option in LANGUAGES" :key="option.value" :value="option.value">{{ option.label }}</option>
      </select>
      <label class="flex items-center gap-1.5 text-xs text-ink/70">
        <input type="checkbox" :checked="highlight" @change="onHighlight($event.target.checked)" />
        语法高亮
      </label>
    </div>
    <textarea
      :value="text"
      spellcheck="false"
      class="min-h-28 w-full rounded-md border border-black/10 bg-dawn/40 p-2 font-mono text-[13px] leading-5 text-ink outline-none focus:border-moss"
      placeholder="写一段代码"
      @input="onTextInput($event.target.value)"
    />
    <pre
      v-if="highlight"
      class="mt-1.5 overflow-x-auto rounded-md bg-ink/[0.04] p-2 font-mono text-[13px] leading-5 text-ink"
      v-html="highlighted || '<span class=&quot;text-ink/35&quot;>高亮预览</span>'"
    />
  </BlockShell>
</template>
