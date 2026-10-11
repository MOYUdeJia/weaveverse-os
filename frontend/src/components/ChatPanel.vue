<script setup>
import { nextTick, ref, watch } from 'vue'

import { getAiSettings, speakText, streamAiChat, transcribeSpeech } from '../api/client'
import { showToast } from '../toast'

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
const listening = ref(false)
const player = ref(null)
let recorder = null
let recordChunks = []
let recordStream = null

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

function encodeWav(audioBuffer) {
  const rate = 16000
  const duration = audioBuffer.duration
  const length = Math.floor(duration * rate)
  const channel = audioBuffer.getChannelData(0)
  const samples = new Int16Array(length)
  for (let index = 0; index < length; index += 1) {
    const source = Math.floor((index * audioBuffer.sampleRate) / rate)
    const value = Math.max(-1, Math.min(1, channel[source] || 0))
    samples[index] = value < 0 ? value * 0x8000 : value * 0x7fff
  }
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const write = (offset, text) => {
    for (let index = 0; index < text.length; index += 1) {
      view.setUint8(offset + index, text.charCodeAt(index))
    }
  }
  write(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  write(8, 'WAVE')
  write(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, rate, true)
  view.setUint32(28, rate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  write(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  new Int16Array(buffer, 44).set(samples)
  return new Blob([buffer], { type: 'audio/wav' })
}

async function startMic(event) {
  event.preventDefault()
  event.currentTarget.setPointerCapture?.(event.pointerId)
  if (listening.value) {
    return
  }
  recordChunks = []
  try {
    recordStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    showToast('没有拿到麦克风')
    return
  }
  recorder = new MediaRecorder(recordStream)
  recorder.ondataavailable = (item) => {
    if (item.data.size) {
      recordChunks.push(item.data)
    }
  }
  recorder.start()
  listening.value = true
  showToast('正在录音。松开后识别，第一次会下载模型')
}

async function stopMic() {
  if (!recorder || !listening.value) {
    return
  }
  listening.value = false
  const finished = new Promise((resolve) => {
    recorder.onstop = resolve
  })
  recorder.stop()
  recordStream?.getTracks().forEach((track) => track.stop())
  await finished
  const blob = new Blob(recordChunks, { type: recorder.mimeType || 'audio/webm' })
  try {
    const context = new AudioContext()
    const decoded = await context.decodeAudioData(await blob.arrayBuffer())
    const wav = encodeWav(decoded)
    await context.close()
    const result = await transcribeSpeech(wav)
    if (result.text) {
      draft.value = `${draft.value} ${result.text}`.trim()
    }
  } catch (error) {
    showToast(error.message || '识别失败。如果是第一次，模型可能还在下载。')
  }
}

async function readAloud(message) {
  if (!message.content) {
    return
  }
  if (player.value) {
    player.value.pause()
    player.value = null
    return
  }
  try {
    const blob = await speakText(message.content)
    const audio = new Audio(URL.createObjectURL(blob))
    player.value = audio
    audio.onended = () => {
      player.value = null
    }
    await audio.play()
  } catch (error) {
    showToast(error.message || '朗读失败')
  }
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
          <button v-if="message.role === 'assistant' && message.content" type="button" class="mt-1 block text-xs text-ink/50" @click="readAloud(message)">
            {{ player ? '停止' : '朗读' }}
          </button>
        </div>
      </div>
    </div>
    <form class="flex gap-2 border-t border-black/10 p-3" @submit.prevent="send">
      <button
        type="button"
        class="h-10 w-10 shrink-0 rounded-full text-sm"
        :class="listening ? 'bg-ember text-white' : 'wv-chip'"
        title="按住说话"
        @pointerdown="startMic"
        @pointerup="stopMic"
        @pointercancel="stopMic"
      >
        麦
      </button>
      <input v-model="draft" class="wv-chip h-10 min-w-0 flex-1 rounded px-3 text-sm outline-none" placeholder="输入消息" />
      <button type="submit" class="h-10 rounded bg-moss px-3 text-sm text-white" :disabled="sending">发送</button>
    </form>
  </aside>
</template>
