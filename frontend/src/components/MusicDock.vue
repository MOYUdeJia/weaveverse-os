<script setup>
// 音乐悬浮球。弧线按钮和面板缩放用 GSAP，节拍来自 AnalyserNode。
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import gsap from 'gsap'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'

import { assignTrackList, deleteTrack, listTracks, trackUrl, uploadTrack } from '../api/client'
import { showMenu } from '../contextMenu'

gsap.registerPlugin(MotionPathPlugin)

const LISTS = [
  { id: 'podcast', label: '播客' },
  { id: 'liked', label: '我喜欢的' },
  { id: 'saved', label: '收藏' },
  { id: 'playlist', label: '播放列表' },
]
const MODES = [
  { id: 'one', label: '单曲循环' },
  { id: 'order', label: '顺序播放' },
  { id: 'shuffle', label: '随机播放' },
]
const STATE_KEY = 'wv.player.state'

const props = defineProps({
  place: { type: String, default: 'corner' },
})

const tracks = ref([])
const listId = ref('playlist')
const mode = ref('order')
const index = ref(0)
const audio = ref(null)
const fileInput = ref(null)
const panelEl = ref(null)
const prevEl = ref(null)
const nextEl = ref(null)
const volEl = ref(null)
const playing = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(0.8)
const panelOpen = ref(false)
const controlsOpen = ref(false)
const overStage = ref(false)
const volHot = ref(false)
const volHold = ref(false)
const notes = ref([])
const errorMessage = ref('')

let audioCtx = null
let analyser = null
let raf = 0
let lastBass = 0
let lastSpawn = 0
let noteSeq = 0
let savedAt = 0

const shown = computed(() => tracks.value.filter((track) => (track.list || 'playlist') === listId.value))
const current = computed(() => shown.value[index.value] || null)
const modeLabel = computed(() => MODES.find((item) => item.id === mode.value)?.label || '顺序播放')
const listLabel = computed(() => LISTS.find((item) => item.id === listId.value)?.label || '播放列表')
const placeClass = computed(() => {
  if (props.place === 'bottom') {
    return 'wv-orb-bottom'
  }
  if (props.place === 'side') {
    return 'wv-orb-side'
  }
  return 'wv-orb-corner'
})

function readState() {
  try {
    return JSON.parse(localStorage.getItem(STATE_KEY) || 'null')
  } catch {
    return null
  }
}

function writeState() {
  try {
    localStorage.setItem(STATE_KEY, JSON.stringify({
      filename: current.value?.filename || '',
      list: listId.value,
      mode: mode.value,
      time: currentTime.value,
      volume: volume.value,
      playing: playing.value,
    }))
  } catch {
    // 记不住进度时，这次仍按当前曲播放。
  }
}

function wireAnalyser() {
  if (audioCtx || !audio.value) {
    return
  }
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) {
    return
  }
  audioCtx = new Ctx()
  const source = audioCtx.createMediaElementSource(audio.value)
  analyser = audioCtx.createAnalyser()
  analyser.fftSize = 256
  source.connect(analyser)
  analyser.connect(audioCtx.destination)
}

function spawnNote() {
  if (notes.value.length >= 6) {
    return
  }
  const id = noteSeq + 1
  noteSeq = id
  const glyph = ['♪', '♫', '♩'][id % 3]
  notes.value = [...notes.value, { id, glyph }]
  nextTick(() => {
    const el = document.querySelector(`[data-note="${id}"]`)
    if (!el) {
      return
    }
    gsap.fromTo(el, { y: 8, x: 0, opacity: 0.95, scale: 0.7 }, {
      y: -72 - Math.random() * 24,
      x: (Math.random() - 0.5) * 28,
      opacity: 0,
      scale: 1,
      duration: 0.9,
      ease: 'power1.out',
      onComplete: () => {
        notes.value = notes.value.filter((item) => item.id !== id)
      },
    })
  })
}

function tickEnergy() {
  raf = 0
  if (!playing.value || !analyser) {
    return
  }
  const bins = new Uint8Array(analyser.frequencyBinCount)
  analyser.getByteFrequencyData(bins)
  let sum = 0
  for (let bin = 1; bin <= 6; bin += 1) {
    sum += bins[bin] || 0
  }
  const bass = sum / 6
  const now = performance.now()
  if (bass > 128 && bass - lastBass > 22 && now - lastSpawn > 170) {
    spawnNote()
    lastSpawn = now
  }
  lastBass = lastBass * 0.55 + bass * 0.45
  raf = requestAnimationFrame(tickEnergy)
}

watch(playing, (value) => {
  if (value) {
    audioCtx?.resume()
    if (!raf) {
      raf = requestAnimationFrame(tickEnergy)
    }
  }
  writeState()
})

watch(volume, (value) => {
  if (audio.value) {
    audio.value.volume = value
  }
  writeState()
})

function load(next, autoplay, at = 0) {
  const track = shown.value[next]
  if (!track || !audio.value) {
    return
  }
  index.value = next
  audio.value.src = trackUrl(track.filename)
  const start = () => {
    audio.value.removeEventListener('loadedmetadata', start)
    if (at > 0 && Number.isFinite(audio.value.duration)) {
      audio.value.currentTime = Math.min(at, Math.max(0, audio.value.duration - 0.4))
    }
    if (autoplay) {
      wireAnalyser()
      audio.value.play().catch(() => {})
    }
  }
  audio.value.addEventListener('loadedmetadata', start)
}

function step(delta) {
  const rows = shown.value
  if (!rows.length) {
    return
  }
  const next = (index.value + delta + rows.length) % rows.length
  if (next === index.value && audio.value) {
    audio.value.currentTime = 0
    audio.value.play().catch(() => {})
    return
  }
  load(next, true)
}

function onEnded() {
  if (mode.value === 'one' && audio.value) {
    audio.value.currentTime = 0
    audio.value.play().catch(() => {})
    return
  }
  if (mode.value === 'shuffle' && shown.value.length > 1) {
    let next = index.value
    while (next === index.value) {
      next = Math.floor(Math.random() * shown.value.length)
    }
    load(next, true)
    return
  }
  step(1)
}

function togglePlay() {
  wireAnalyser()
  if (!audio.value || !current.value) {
    return
  }
  if (audio.value.paused) {
    audio.value.play().catch(() => {})
  } else {
    audio.value.pause()
  }
}

function cycleMode() {
  const at = MODES.findIndex((item) => item.id === mode.value)
  mode.value = MODES[(at + 1) % MODES.length].id
  writeState()
}

function travel(el, path) {
  gsap.to(el, {
    duration: 0.42,
    ease: 'power2.out',
    opacity: 1,
    motionPath: { path, curviness: 1.6 },
  })
}

function onMeta() {
  duration.value = Number.isFinite(audio.value?.duration) ? audio.value.duration : 0
}

function openArc() {
  overStage.value = true
  controlsOpen.value = true
  if (!prevEl.value || !nextEl.value || !volEl.value) {
    return
  }
  gsap.killTweensOf([prevEl.value, nextEl.value, volEl.value])
  travel(prevEl.value, [{ x: 0, y: 0 }, { x: -16, y: -22 }, { x: -52, y: 2 }])
  travel(nextEl.value, [{ x: 0, y: 0 }, { x: 16, y: -22 }, { x: 52, y: 2 }])
  travel(volEl.value, [{ x: 0, y: 0 }, { x: 18, y: -18 }, { x: 0, y: -52 }])
}

function closeArc() {
  overStage.value = false
  if (volHold.value || volHot.value) {
    return
  }
  controlsOpen.value = false
  ;[prevEl.value, nextEl.value, volEl.value].forEach((el) => {
    if (!el) {
      return
    }
    gsap.killTweensOf(el)
    gsap.to(el, { x: 0, y: 0, opacity: 0, duration: 0.24, ease: 'power2.in' })
  })
}

function panelOrigin() {
  return props.place === 'bottom' ? '50% 100%' : '100% 50%'
}

function togglePanel(force) {
  const open = typeof force === 'boolean' ? force : !panelOpen.value
  if (open) {
    panelOpen.value = true
    nextTick(() => {
      if (!panelEl.value) {
        return
      }
      gsap.fromTo(panelEl.value, { scale: 0.35, opacity: 0, x: props.place === 'bottom' ? 0 : 18 }, {
        scale: 1,
        opacity: 1,
        x: 0,
        duration: 0.34,
        ease: 'power2.out',
        transformOrigin: panelOrigin(),
      })
    })
    return
  }
  if (!panelEl.value) {
    panelOpen.value = false
    return
  }
  gsap.to(panelEl.value, {
    scale: 0.35,
    opacity: 0,
    x: props.place === 'bottom' ? 0 : 18,
    duration: 0.24,
    ease: 'power2.in',
    transformOrigin: panelOrigin(),
    onComplete: () => {
      panelOpen.value = false
    },
  })
}

function switchList(id) {
  listId.value = id
  index.value = 0
  writeState()
  if (shown.value.length) {
    load(0, playing.value)
  } else {
    audio.value?.pause()
  }
}

function onMenu(event) {
  showMenu(event, [
    ...LISTS.map((item) => ({
      label: item.id === listId.value ? `✓ ${item.label}` : item.label,
      onClick: () => switchList(item.id),
    })),
    { label: '打开面板', onClick: () => togglePanel(true) },
    { label: '上一首', onClick: () => step(-1) },
    { label: '下一首', onClick: () => step(1) },
    { label: playing.value ? '暂停' : '播放', onClick: togglePlay },
    { label: modeLabel.value, onClick: cycleMode },
    { label: '音量加', onClick: () => { volume.value = Math.min(1, +(volume.value + 0.1).toFixed(2)) } },
    { label: '音量减', onClick: () => { volume.value = Math.max(0, +(volume.value - 0.1).toFixed(2)) } },
  ])
}

function onTime() {
  currentTime.value = audio.value?.currentTime || 0
  if (currentTime.value - savedAt > 2) {
    savedAt = currentTime.value
    writeState()
  }
}

function seek(event) {
  if (!audio.value) {
    return
  }
  audio.value.currentTime = Number(event.target.value)
}

function clock(seconds) {
  const value = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`
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
    const track = await uploadTrack(file, listId.value)
    tracks.value = [...tracks.value, track]
    const next = shown.value.findIndex((item) => item.filename === track.filename)
    load(next >= 0 ? next : shown.value.length - 1, true)
  } catch (error) {
    errorMessage.value = error.message || '添加失败'
  }
}

async function removeAt(track) {
  await deleteTrack(track.filename)
  tracks.value = tracks.value.filter((item) => item.filename !== track.filename)
  if (!shown.value.length) {
    index.value = 0
    playing.value = false
    audio.value?.removeAttribute('src')
    return
  }
  load(Math.min(index.value, shown.value.length - 1), false)
}

async function moveTrack(track, nextList) {
  const updated = await assignTrackList(track.filename, nextList)
  tracks.value = tracks.value.map((item) => (item.filename === updated.filename ? updated : item))
}

function releaseVolume() {
  volHold.value = false
  if (!overStage.value && !volHot.value) {
    closeArc()
  }
}

onMounted(async () => {
  window.addEventListener('pointerup', releaseVolume)
  try {
    tracks.value = (await listTracks()).tracks || []
  } catch {
    tracks.value = []
  }
  const saved = readState()
  if (saved?.list && LISTS.some((item) => item.id === saved.list)) {
    listId.value = saved.list
  }
  if (saved?.mode && MODES.some((item) => item.id === saved.mode)) {
    mode.value = saved.mode
  }
  if (typeof saved?.volume === 'number') {
    volume.value = saved.volume
  }
  if (audio.value) {
    audio.value.volume = volume.value
  }
  const found = shown.value.findIndex((item) => item.filename === saved?.filename)
  if (shown.value.length) {
    load(found >= 0 ? found : 0, Boolean(saved?.playing), Number(saved?.time) || 0)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('pointerup', releaseVolume)
  cancelAnimationFrame(raf)
  audio.value?.pause()
  writeState()
  audioCtx?.close()
})
</script>

<template>
  <div class="wv-orb-dock" :class="placeClass">
    <div v-show="panelOpen" ref="panelEl" class="wv-orb-panel">
      <div class="mb-2 flex items-center justify-between gap-2">
        <p class="text-xs font-semibold">{{ listLabel }}</p>
        <button type="button" class="rounded bg-white/80 px-2 py-1 text-[11px]" @click="cycleMode">{{ modeLabel }}</button>
        <button type="button" class="text-xs text-ink/45" @click="togglePanel(false)">收起</button>
      </div>
      <div class="mb-2 flex items-center gap-2 text-[10px] text-ink/50">
        <span>{{ clock(currentTime) }}</span>
        <input class="min-w-0 flex-1" type="range" min="0" :max="duration || 0" step="0.1" :value="currentTime" @input="seek" />
        <span>{{ clock(duration) }}</span>
      </div>
      <p v-if="!shown.length" class="py-3 text-xs text-ink/45">这个歌单还没有音频</p>
      <button
        v-for="track in shown"
        :key="track.filename"
        type="button"
        class="flex w-full items-center gap-2 py-1.5 text-left text-xs"
        :class="track.filename === current?.filename ? 'text-moss' : 'text-ink/75'"
        @click="load(shown.findIndex((item) => item.filename === track.filename), true)"
      >
        <span class="min-w-0 flex-1 truncate">{{ track.title }}</span>
        <select class="max-w-[5.5rem] bg-transparent text-[10px]" :value="track.list || 'playlist'" @click.stop @change="moveTrack(track, $event.target.value)">
          <option v-for="item in LISTS" :key="item.id" :value="item.id">{{ item.label }}</option>
        </select>
        <span class="text-ink/35" @click.stop="removeAt(track)">移除</span>
      </button>
      <button type="button" class="mt-2 h-7 rounded bg-white/80 px-2 text-xs" @click="fileInput.click()">添加音频</button>
      <p v-if="errorMessage" class="mt-1 text-xs text-ember">{{ errorMessage }}</p>
    </div>

    <div class="wv-orb-stage" :class="controlsOpen ? 'is-open' : ''" @mouseenter="openArc" @mouseleave="closeArc">
      <div class="wv-orb-pad" />
      <span v-for="note in notes" :key="note.id" :data-note="note.id" class="wv-orb-note">{{ note.glyph }}</span>
      <button ref="prevEl" type="button" class="wv-orb-btn" title="上一首" @click="step(-1)">‹</button>
      <button ref="nextEl" type="button" class="wv-orb-btn" title="下一首" @click="step(1)">›</button>
      <div
        ref="volEl"
        class="wv-orb-btn wv-orb-vol"
        @mouseenter="volHot = true"
        @mouseleave="volHot = false"
      >
        <input
          v-show="volHot || volHold"
          class="wv-orb-slider"
          type="range"
          min="0"
          max="1"
          step="0.05"
          :value="volume"
          title="音量"
          @pointerdown="volHold = true"
          @input="volume = Number($event.target.value)"
        />
        <button type="button" title="音量">♫</button>
      </div>
      <button type="button" class="wv-orb-ball" :title="current?.title || '还没有音频'" @click="togglePlay" @contextmenu="onMenu">
        <span class="wv-orb-title"><span>{{ current?.title || '♪' }}</span></span>
        <span class="wv-orb-state">{{ playing ? '暂停' : '播放' }}</span>
      </button>
    </div>
    <audio
      ref="audio"
      class="pointer-events-none absolute h-0 w-0"
      @timeupdate="onTime"
      @loadedmetadata="onMeta"
      @play="playing = true"
      @pause="playing = false"
      @ended="onEnded"
    />
    <input ref="fileInput" class="wv-file-input" type="file" accept="audio/mpeg,audio/ogg,audio/wav,audio/mp4,audio/flac,.mp3,.ogg,.wav,.m4a,.flac" @change="onFile" />
  </div>
</template>
