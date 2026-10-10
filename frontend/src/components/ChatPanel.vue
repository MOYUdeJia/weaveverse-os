<script setup>
import { nextTick, ref, watch } from 'vue'

import { getAiSettings, streamAiChat } from '../api/client'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'open-nav'])

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

function scrollDown() {
  nextTick(() => list.value?.scrollTo?.(0, list.value.scrollHeight))
}

function patch(index, extra) {
  const current = messages.value[index]
  messages.value[index] = { ...current, ...extra }
  scrollDown()
}

async function talk(index, resume) {
  sending.value = true
  patch(index, { confirm: null })
  try {
    await streamAiChat(
      messages.value
        .filter((item) => item.role === 'user' || item.content)
        .map((item) => ({ role: item.role, content: item.content })),
      (event) => {
        const current = messages.value[index]
        if (event.text) {
          patch(index, { content: `${current.content}${event.text}` })
        }
        if (event.status) {
          patch(index, { notes: [...(current.notes || []), event.status] })
        }
        if (event.tool) {
          patch(index, {
            notes: [...(current.notes || []), event.tool.summary || '已完成'],
            link: event.tool.nav_id ? { groupId: event.tool.group_id, navId: event.tool.nav_id } : current.link,
          })
        }
        if (event.confirm) {
          patch(index, { confirm: event.confirm })
        }
      },
      resume,
    )
  } catch (error) {
    const current = messages.value[index]
    patch(index, { content: current.content || error.message || '网络错误，请重试' })
  } finally {
    sending.value = false
  }
}

async function send() {
  const text = draft.value.trim()
  if (!text || sending.value || !hasKey.value) {
    return
  }
  draft.value = ''
  messages.value = [...messages.value, { role: 'user', content: text }, { role: 'assistant', content: '', notes: [], confirm: null, link: null }]
  await talk(messages.value.length - 1, null)
}

function decide(message, approved) {
  const index = messages.value.indexOf(message)
  const confirm = message.confirm
  if (index < 0 || !confirm) {
    return
  }
  talk(index, { id: confirm.id, name: confirm.name, arguments: confirm.arguments, approved })
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
        <div class="max-w-[85%]">
          <p v-for="note in message.notes || []" :key="note" class="mb-1 text-xs text-ink/45">{{ note }}</p>
          <p v-if="message.content" class="whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm" :class="message.role === 'user' ? 'bg-moss text-white' : 'wv-chip'">
            {{ message.content }}
          </p>
          <div v-if="message.confirm" class="mt-2 rounded-md border border-black/10 p-2">
            <p class="text-xs">{{ message.confirm.summary }}？</p>
            <div class="mt-2 flex gap-2">
              <button type="button" class="h-7 rounded bg-moss px-2 text-xs text-white" @click="decide(message, true)">确认</button>
              <button type="button" class="h-7 rounded px-2 text-xs text-ink/60" @click="decide(message, false)">取消</button>
            </div>
          </div>
          <button v-if="message.link" type="button" class="mt-1 text-xs text-moss" @click="emit('open-nav', message.link)">前往查看</button>
        </div>
      </div>
    </div>
    <form class="flex gap-2 border-t border-black/10 p-3" @submit.prevent="send">
      <input v-model="draft" class="wv-chip h-10 min-w-0 flex-1 rounded px-3 text-sm outline-none" placeholder="输入消息" />
      <button type="submit" class="h-10 rounded bg-moss px-3 text-sm text-white" :disabled="sending">发送</button>
    </form>
  </aside>
</template>
