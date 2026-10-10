<script setup>
import { nextTick, ref, watch } from 'vue'

import { getAiSettings, streamAiChat } from '../api/client'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close'])

const messages = ref([])
const draft = ref('')
const sending = ref(false)
const modelName = ref('')
const hasKey = ref(false)
const loaded = ref(false)
const list = ref(null)

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      return
    }
    try {
      const settings = await getAiSettings()
      modelName.value = settings.model || ''
      hasKey.value = Boolean(settings.has_key)
      loaded.value = true
    } catch {
      hasKey.value = false
      loaded.value = true
    }
    nextTick(() => {
      list.value?.scrollTo?.(0, list.value.scrollHeight)
    })
  },
)

async function send() {
  const text = draft.value.trim()
  if (!text || sending.value) {
    return
  }
  if (!hasKey.value) {
    return
  }
  draft.value = ''
  messages.value = [...messages.value, { role: 'user', content: text }, { role: 'assistant', content: '' }]
  const index = messages.value.length - 1
  sending.value = true
  try {
    await streamAiChat(
      messages.value.slice(0, -1).map((item) => ({ role: item.role, content: item.content })),
      (piece) => {
        const current = messages.value[index]
        messages.value[index] = { ...current, content: `${current.content}${piece}` }
        nextTick(() => list.value?.scrollTo?.(0, list.value.scrollHeight))
      },
    )
  } catch (error) {
    const current = messages.value[index]
    const hint = error.message || '网络错误，请重试'
    messages.value[index] = { ...current, content: current.content || hint }
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <aside v-if="open" class="wv-chat wv-surface">
    <header class="flex items-center justify-between border-b border-black/10 px-4 py-3">
      <div>
        <p class="text-sm font-semibold">AI</p>
        <p class="text-xs text-ink/45">{{ modelName || '未选择模型' }}</p>
      </div>
      <button type="button" class="text-ink/50" @click="emit('close')">×</button>
    </header>
    <div ref="list" class="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
      <p v-if="loaded && !hasKey" class="text-sm text-ink/60">还没有可用的 Key。打开设置里的 AI，保存后再来。</p>
      <p v-else-if="loaded && !messages.length" class="text-sm text-ink/45">直接问我就行。我目前只能聊天。</p>
      <div v-for="(message, index) in messages" :key="index" class="flex" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
        <p class="max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm" :class="message.role === 'user' ? 'bg-moss text-white' : 'wv-chip'">
          {{ message.content }}
        </p>
      </div>
    </div>
    <form class="flex gap-2 border-t border-black/10 p-3" @submit.prevent="send">
      <input v-model="draft" class="wv-chip h-10 min-w-0 flex-1 rounded px-3 text-sm outline-none" placeholder="输入消息" />
      <button type="submit" class="h-10 rounded bg-moss px-3 text-sm text-white" :disabled="sending">发送</button>
    </form>
  </aside>
</template>
