<script setup>
import Plyr from 'plyr'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import 'plyr/dist/plyr.css'

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
let player = null

onMounted(async () => {
  try {
    tracks.value = (await listTracks()).tracks || []
  } catch {
    tracks.value = []
  }
  player = new Plyr(audio.value, {
    controls: ['play', 'progress', 'current-time', 'mute', 'volume'],
  })
  if (tracks.value.length) {
    load(0, false)
  }
})

onBeforeUnmount(() => {
  player?.destroy()
})

function load(next, autoplay) {
  const track = tracks.value[next]
  if (!track || !audio.value) {
    return
  }
  index.value = next
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
  load(next, true)
}

async function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    return
  }
  errorMessage.value = ''
  try {
    const track = await uploadTrack(file)
    tracks.value = [...tracks.value, track]
    load(tracks.value.length - 1, true)
  } catch (error) {
    errorMessage.value = error.message || '添加失败'
  }
}

async function removeCurrent() {
  const track = tracks.value[index.value]
  if (!track) {
    return
  }
  await deleteTrack(track.filename)
  tracks.value = tracks.value.filter((item) => item.filename !== track.filename)
  if (tracks.value.length) {
    load(Math.min(index.value, tracks.value.length - 1), false)
  } else if (audio.value) {
    audio.value.removeAttribute('src')
  }
}
</script>

<template>
  <div
    class="z-40 border border-black/10 bg-[#fcfaf5]/95 px-3 py-2 shadow-lg backdrop-blur"
    :class="
      place === 'top'
        ? 'fixed inset-x-4 top-3 rounded-md'
        : place === 'corner'
          ? 'fixed bottom-4 right-4 w-80 rounded-md'
          : 'fixed inset-x-4 bottom-3 rounded-md'
    "
  >
    <div class="mb-1 flex items-center gap-2 text-xs">
      <button type="button" class="h-7 rounded bg-white px-2" @click="step(-1)">上一首</button>
      <button type="button" class="h-7 rounded bg-white px-2" @click="step(1)">下一首</button>
      <span class="min-w-0 flex-1 truncate text-ink/80">{{ tracks[index]?.title || '还没有音频' }}</span>
      <button type="button" class="h-7 rounded bg-white px-2" @click="fileInput.click()">添加</button>
      <button type="button" class="h-7 rounded px-2 text-ink/45" @click="removeCurrent">移除</button>
    </div>
    <audio ref="audio" />
    <p v-if="errorMessage" class="mt-1 text-xs text-ember">{{ errorMessage }}</p>
    <input ref="fileInput" class="hidden" type="file" accept="audio/mpeg,audio/ogg,audio/wav,audio/mp4,audio/flac,.mp3,.ogg,.wav,.m4a,.flac" @change="onFile" />
  </div>
</template>
