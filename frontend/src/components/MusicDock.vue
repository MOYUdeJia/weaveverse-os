<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { deleteTrack, listTracks, trackUrl, uploadTrack } from '../api/client'

const props = defineProps({
  place: {
    type: String,
    default: 'bottom',
  },
})

const tracks = ref([])
const index = ref(0)
const audio = ref(null)
const fileInput = ref(null)
const errorMessage = ref('')
const playing = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(0.8)
const playlistOpen = ref(false)
const folded = ref(false)

try {
  folded.value = localStorage.getItem('wv.player.folded') === '1'
} catch {
  folded.value = false
}

const placeClass = computed(() => {
  if (props.place === 'top') {
    return 'fixed left-1/2 top-3 -translate-x-1/2'
  }
  if (props.place === 'corner') {
    return 'fixed bottom-4 right-4'
  }
  return 'fixed bottom-3 left-1/2 -translate-x-1/2'
})

const current = computed(() => tracks.value[index.value] || null)

watch(folded, (value) => {
  try {
    localStorage.setItem('wv.player.folded', value ? '1' : '0')
  } catch {
    // 收起状态写失败时，这次会话里仍然保持当前样子。
  }
})

watch(volume, (value) => {
  if (audio.value) {
    audio.value.volume = value
  }
})

onMounted(async () => {
  try {
    tracks.value = (await listTracks()).tracks || []
  } catch {
    tracks.value = []
  }
  if (audio.value) {
    audio.value.volume = volume.value
  }
  if (tracks.value.length) {
    load(0, false)
  }
})

onBeforeUnmount(() => {
  audio.value?.pause()
})

function load(next, autoplay) {
  const track = tracks.value[next]
  if (!track || !audio.value) {
    return
  }
  index.value = next
  currentTime.value = 0
  audio.value.src = trackUrl(track.filename)
  if (autoplay) {
    audio.value.play()
  }
}

function step(delta) {
  if (!tracks.value.length) {
    return
  }
  const next = (index.value + delta + tracks.value.length) % tracks.value.length
  if (next === index.value && audio.value) {
    audio.value.currentTime = 0
    audio.value.play()
    return
  }
  load(next, true)
}

function togglePlay() {
  if (!audio.value || !current.value) {
    return
  }
  if (audio.value.paused) {
    audio.value.play()
  } else {
    audio.value.pause()
  }
}

function onTime() {
  currentTime.value = audio.value?.currentTime || 0
}

function onMeta() {
  duration.value = Number.isFinite(audio.value?.duration) ? audio.value.duration : 0
}

function seek(event) {
  if (!audio.value) {
    return
  }
  audio.value.currentTime = Number(event.target.value)
}

function clock(seconds) {
  const value = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0
  const minutes = Math.floor(value / 60)
  const rest = String(value % 60).padStart(2, '0')
  return `${minutes}:${rest}`
}

async function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    errorMessage.value = '没有读到音频'
    return
  }
  errorMessage.value = ''
  try {
    const track = await uploadTrack(file)
    tracks.value = [...tracks.value, track]
    playlistOpen.value = true
    folded.value = false
    load(tracks.value.length - 1, true)
  } catch (error) {
    errorMessage.value = error.message || '添加失败'
  }
}

async function removeAt(target) {
  const track = tracks.value[target]
  if (!track) {
    return
  }
  await deleteTrack(track.filename)
  tracks.value = tracks.value.filter((item) => item.filename !== track.filename)
  if (!tracks.value.length) {
    index.value = 0
    playing.value = false
    currentTime.value = 0
    duration.value = 0
    audio.value?.removeAttribute('src')
    return
  }
  load(Math.min(target, tracks.value.length - 1), false)
}
</script>

<template>
  <div class="wv-player flex flex-col" :class="[placeClass, place === 'top' ? 'items-center' : 'wv-player-up items-end']">
    <button v-if="folded" type="button" class="wv-player-fab" title="展开播放器" @click="folded = false">♪</button>
    <template v-else>
      <div class="wv-player-bar" :class="place === 'corner' ? 'wv-player-narrow' : ''">
        <button type="button" class="h-7 w-7 shrink-0 rounded-full text-sm text-ink/55" title="收起" @click="folded = true">–</button>
        <button type="button" class="h-7 w-7 shrink-0 rounded-full bg-white/80 text-sm" title="上一首" @click="step(-1)">‹</button>
        <button type="button" class="h-7 shrink-0 rounded-full bg-ink px-3 text-xs text-white" :title="playing ? '暂停' : '播放'" @click="togglePlay">
          {{ playing ? '暂停' : '播放' }}
        </button>
        <button type="button" class="h-7 w-7 shrink-0 rounded-full bg-white/80 text-sm" title="下一首" @click="step(1)">›</button>
        <div class="min-w-0 flex-1">
          <p class="truncate text-xs text-ink/80">{{ current?.title || '还没有音频' }}</p>
          <input
            class="mt-1 w-full"
            type="range"
            min="0"
            :max="duration || 0"
            step="0.1"
            :value="currentTime"
            @input="seek"
          />
        </div>
        <span class="shrink-0 text-[10px] tabular-nums text-ink/45">{{ clock(currentTime) }} / {{ clock(duration) }}</span>
        <input class="w-14 shrink-0" type="range" min="0" max="1" step="0.05" :value="volume" title="音量" @input="volume = Number($event.target.value)" />
        <button type="button" class="h-7 shrink-0 rounded-full px-2 text-xs" :class="playlistOpen ? 'bg-ink text-white' : 'bg-white/80'" @click="playlistOpen = !playlistOpen">
          歌单
        </button>
        <button type="button" class="h-7 w-7 shrink-0 rounded-full bg-white/80 text-sm" title="添加音频" @click="fileInput.click()">+</button>
      </div>
      <div v-if="playlistOpen" class="wv-player-list" :class="place === 'corner' ? 'wv-player-narrow' : ''">
        <p v-if="!tracks.length" class="px-3 py-3 text-xs text-ink/45">还没有音频。点 + 添加本地文件。</p>
        <button
          v-for="(track, trackIndex) in tracks"
          :key="track.filename"
          type="button"
          class="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-black/5"
          :class="trackIndex === index ? 'text-moss' : 'text-ink/75'"
          @click="load(trackIndex, true)"
        >
          <span class="min-w-0 flex-1 truncate">{{ track.title }}</span>
          <span class="text-ink/35" @click.stop="removeAt(trackIndex)">移除</span>
        </button>
      </div>
      <p v-if="errorMessage" class="mt-1 px-3 text-xs text-ember">{{ errorMessage }}</p>
    </template>
    <audio
      ref="audio"
      class="pointer-events-none absolute h-0 w-0"
      @timeupdate="onTime"
      @loadedmetadata="onMeta"
      @play="playing = true"
      @pause="playing = false"
      @ended="step(1)"
    />
    <input ref="fileInput" class="wv-file-input" type="file" accept="audio/mpeg,audio/ogg,audio/wav,audio/mp4,audio/flac,.mp3,.ogg,.wav,.m4a,.flac" @change="onFile" />
  </div>
</template>
