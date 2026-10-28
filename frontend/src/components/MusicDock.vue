<script setup>
// 通用音乐悬浮球。球的坐标固定，胶囊和按键都相对它展开。
// 进度是上下两根同步的描边。走到圆上就改走外圆弧，不从球内部穿过去。
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import gsap from 'gsap'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'

import { deleteTrack, listTracks, trackUrl, uploadTrack } from '../api/client'

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
const LANES = [-28, -14, 0, 14, 28]
const STATE_KEY = 'wv.player.state'
const shellState = { w: 0 }

const props = defineProps({
  place: { type: String, default: 'corner' },
  originX: { default: null },
  originY: { default: null },
  spread: { type: String, default: '' },
  progressStyle: { type: String, default: 'solid' },
  progressColor: { type: String, default: '#3f6f57' },
  moving: { type: Boolean, default: false },
})

const emit = defineEmits(['move-done', 'move-cancel', 'hide'])

const tracks = ref([])
const listId = ref('playlist')
const mode = ref('order')
const index = ref(0)
const audio = ref(null)
const fileInput = ref(null)
const dockEl = ref(null)
const stageEl = ref(null)
const menuEl = ref(null)
const subEl = ref(null)
const stemEl = ref(null)
const prevEl = ref(null)
const nextEl = ref(null)
const volEl = ref(null)
const panelBtn = ref(null)
const modeBtn = ref(null)
const menu = ref(null)
const playing = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(0.8)
const panelOpen = ref(false)
const controlsOpen = ref(false)
const overStage = ref(false)
const volHot = ref(false)
const volHold = ref(false)
const volDown = ref(false)
const notes = ref([])
const errorMessage = ref('')
const shellWidth = ref(0)
const viewport = ref(0)
const dragPos = ref(null)
const tight = ref(false)
const topPathEl = ref(null)
const botPathEl = ref(null)
const measured = ref({ top: 1, bot: 1 })

let audioCtx = null
let analyser = null
let raf = 0
let lastBass = 0
let lastSpawn = 0
let noteSeq = 0
let savedAt = 0
let wheelUntil = 0
let closeTimer = 0
let dragOffsetX = 0
let dragOffsetY = 0

const shown = computed(() => tracks.value.filter((track) => (track.list || 'playlist') === listId.value))
const current = computed(() => shown.value[index.value] || null)
const modeLabel = computed(() => MODES.find((item) => item.id === mode.value)?.label || '顺序播放')
const ratio = computed(() => (duration.value ? Math.min(1, currentTime.value / duration.value) : 0))

const placeClass = computed(() => {
  if (props.moving || props.place === 'free') {
    return 'is-free'
  }
  if (props.place === 'bottom') {
    return 'wv-orb-bottom'
  }
  if (props.place === 'side') {
    return 'wv-orb-side'
  }
  return 'wv-orb-corner'
})

function freePos() {
  const x = Number(props.originX)
  const y = Number(props.originY)
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return clampPos(window.innerWidth - 88, window.innerHeight - 88)
  }
  return clampPos(x * window.innerWidth - 36, y * window.innerHeight - 36)
}

const dockStyle = computed(() => {
  viewport.value
  const vars = { '--wv-progress': props.progressColor || '#3f6f57' }
  if (props.moving && dragPos.value) {
    return {
      ...vars,
      left: `${dragPos.value.left}px`,
      top: `${dragPos.value.top}px`,
      right: 'auto',
      bottom: 'auto',
      transform: 'none',
    }
  }
  if (props.place === 'free') {
    const pos = freePos()
    return {
      ...vars,
      left: `${pos.left}px`,
      top: `${pos.top}px`,
      right: 'auto',
      bottom: 'auto',
      transform: 'none',
    }
  }
  return vars
})

function ballCenter() {
  if (props.moving && dragPos.value) {
    return { x: dragPos.value.left + 36, y: dragPos.value.top + 36 }
  }
  if (props.place === 'free') {
    const pos = freePos()
    return { x: pos.left + 36, y: pos.top + 36 }
  }
  if (props.place === 'bottom') {
    return { x: window.innerWidth / 2, y: window.innerHeight - 16 - 36 }
  }
  if (props.place === 'side') {
    return { x: window.innerWidth - 16 - 36, y: window.innerHeight / 2 }
  }
  return { x: window.innerWidth - 16 - 36, y: window.innerHeight - 16 - 36 }
}

const spreadMode = computed(() => {
  viewport.value
  props.place
  props.originX
  props.originY
  const forced = props.spread === 'center' || props.spread === 'side' ? props.spread : 'auto'
  const ratio = ballCenter().x / Math.max(window.innerWidth, 1)
  if (forced === 'center') {
    return 'center'
  }
  if (ratio < 0.3) {
    return 'right'
  }
  if (ratio > 0.7) {
    return 'left'
  }
  if (forced === 'side') {
    return ratio <= 0.5 ? 'right' : 'left'
  }
  return 'center'
})

const growRight = computed(() => spreadMode.value === 'right')

const fusedClass = computed(() => {
  if (spreadMode.value === 'center') {
    return 'is-center'
  }
  return growRight.value ? 'is-right' : 'is-left'
})

const fusedStyle = computed(() => {
  const width = `${Math.max(shellWidth.value, 0)}px`
  if (spreadMode.value === 'center') {
    return { width, left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }
  }
  if (growRight.value) {
    return { width, left: '36px', top: '50%', transform: 'translateY(-50%)' }
  }
  return { width, right: '36px', top: '50%', transform: 'translateY(-50%)' }
})

const progressGeom = computed(() => {
  const width = Math.max(shellWidth.value, 0)
  if (spreadMode.value === 'center') {
    return { svgW: Math.max(width, 1), ballCx: width / 2, capX: 0, capW: Math.max(width, 1) }
  }
  if (growRight.value) {
    return { svgW: width + 36, ballCx: 36, capX: 36, capW: Math.max(width, 1) }
  }
  return { svgW: width + 36, ballCx: width, capX: 0, capW: Math.max(width, 1) }
})

const progressBox = computed(() => {
  const geom = progressGeom.value
  const common = { width: `${geom.svgW}px`, height: '72px', top: '50%' }
  if (spreadMode.value === 'center') {
    return { ...common, left: '50%', transform: 'translate(-50%, -50%)' }
  }
  if (growRight.value) {
    return { ...common, left: '0', transform: 'translateY(-50%)' }
  }
  return { ...common, left: `${36 - shellWidth.value}px`, transform: 'translateY(-50%)' }
})

function borderPath(y, outward) {
  const geom = progressGeom.value
  const svgW = Math.max(geom.svgW, 1)
  const radius = 36
  const cy = 36
  const dy = y - cy
  const disc = radius * radius - dy * dy
  if (disc <= 4) {
    return { d: `M 0 ${y} H ${svgW}`, len: svgW }
  }
  const dx = Math.sqrt(disc)
  const x1 = geom.ballCx - dx
  const x2 = geom.ballCx + dx
  const sweep = outward < 0 ? 1 : 0
  const dot = (-dx) * dx + dy * dy
  const central = Math.acos(Math.max(-1, Math.min(1, dot / (radius * radius))))
  const left = Math.max(0, Math.min(x1, svgW))
  const right = Math.max(0, Math.min(x2, svgW))
  let d = `M ${left.toFixed(2)} ${y}`
  if (x1 > 0) {
    d = `M 0 ${y} H ${left.toFixed(2)}`
  }
  if (right - left > 0.5) {
    d += ` A ${radius} ${radius} 0 0 ${sweep} ${right.toFixed(2)} ${y}`
  }
  if (x2 < svgW) {
    d += ` H ${svgW}`
  }
  const straight = (x1 > 0 ? left : 0) + (x2 < svgW ? svgW - right : 0)
  return {
    d,
    len: Math.max(1, straight + (right - left > 0.5 ? radius * central : 0)),
  }
}

const topPath = computed(() => borderPath(10, -1))
const botPath = computed(() => borderPath(62, 1))
const strokePaint = computed(() => (props.progressStyle === 'gradient' ? 'url(#wvRainbow)' : (props.progressColor || '#3f6f57')))

const songClass = computed(() => {
  viewport.value
  const center = ballCenter()
  const classes = []
  if (window.innerHeight - (center.y + 36) < 40) {
    classes.push('is-above')
  }
  if (center.x > window.innerWidth - 130) {
    classes.push('is-end')
  } else if (center.x < 130) {
    classes.push('is-start')
  }
  return classes
})

function measurePaths() {
  nextTick(() => {
    const top = topPathEl.value?.getTotalLength?.()
    const bot = botPathEl.value?.getTotalLength?.()
    measured.value = {
      top: top > 1 ? top : topPath.value.len,
      bot: bot > 1 ? bot : botPath.value.len,
    }
  })
}

function clampPos(left, top) {
  return {
    left: Math.min(Math.max(8, window.innerWidth - 80), Math.max(8, left)),
    top: Math.min(Math.max(8, window.innerHeight - 80), Math.max(8, top)),
  }
}

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
  analyser.fftSize = 1024
  analyser.smoothingTimeConstant = 0.55
  source.connect(analyser)
  analyser.connect(audioCtx.destination)
  audioCtx.resume()
}

function spawnNote() {
  if (notes.value.length >= 18) {
    return
  }
  const id = noteSeq + 1
  noteSeq = id
  const lane = LANES[id % LANES.length]
  const glyph = ['♪', '♫', '♩', '♬'][id % 4]
  const rise = 120 + Math.random() * 36
  const durationSec = 1.65 + Math.random() * 0.55
  notes.value = [...notes.value, { id, glyph }]
  nextTick(() => {
    const el = document.querySelector(`[data-note="${id}"]`)
    if (!el) {
      return
    }
    gsap.fromTo(el, { y: 4, x: lane, opacity: 0.2, scale: 0.84 }, {
      y: -rise,
      x: lane + (Math.random() - 0.5) * 12,
      scale: 1.02,
      duration: durationSec,
      ease: 'power1.out',
      onComplete: () => {
        notes.value = notes.value.filter((item) => item.id !== id)
      },
    })
    gsap.to(el, { opacity: 0.74, duration: 0.16, ease: 'power1.out' })
    gsap.to(el, { opacity: 0, duration: 0.5, delay: durationSec - 0.5, ease: 'power1.in' })
  })
}

function tickEnergy() {
  raf = 0
  if (!playing.value || !analyser) {
    return
  }
  if (controlsOpen.value || panelOpen.value) {
    raf = requestAnimationFrame(tickEnergy)
    return
  }
  const wave = new Uint8Array(analyser.fftSize)
  analyser.getByteTimeDomainData(wave)
  let peak = 0
  for (let bin = 0; bin < wave.length; bin += 8) {
    peak = Math.max(peak, Math.abs(wave[bin] - 128))
  }
  const now = performance.now()
  const loud = peak > 8 && peak - lastBass > 3 && now - lastSpawn > 90
  const steady = now - lastSpawn > 420 && notes.value.length < 8
  if (loud || steady) {
    spawnNote()
    lastSpawn = now
  }
  lastBass = lastBass * 0.4 + peak * 0.6
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

watch([spreadMode, viewport], () => {
  if (!panelOpen.value) {
    return
  }
  tweenShell(targetWidth(), true)
})

watch([topPath, botPath, panelOpen], () => {
  if (panelOpen.value) {
    measurePaths()
  }
})

watch(volume, (value) => {
  if (audio.value) {
    audio.value.volume = value
  }
  writeState()
})

watch(() => props.moving, (value) => {
  menu.value = null
  controlsOpen.value = false
  panelOpen.value = false
  shellWidth.value = 0
  shellState.w = 0
  if (!value) {
    dragPos.value = null
    return
  }
  const center = ballCenter()
  dragPos.value = { left: center.x - 36, top: center.y - 36 }
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
  if (props.moving) {
    return
  }
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

function arcButtons() {
  return [prevEl.value, nextEl.value, volEl.value, panelBtn.value, modeBtn.value].filter(Boolean)
}

function arcPoints() {
  const rect = stageEl.value?.getBoundingClientRect()
  const left = rect ? rect.left : 200
  const right = rect ? window.innerWidth - rect.right : 200
  const top = rect ? rect.top : 200
  const bottom = rect ? window.innerHeight - rect.bottom : 200
  tight.value = Math.min(left, right, top, bottom) < 88
  const btn = tight.value ? 30 : 36
  const pad = 8
  const roomL = Math.max(24, left - pad - btn / 2)
  const roomR = Math.max(24, right - pad - btn / 2)
  const roomT = Math.max(24, top - pad - btn / 2)
  const roomB = Math.max(24, bottom - pad - btn / 2)
  volDown.value = roomT < (tight.value ? 110 : 150)
  const reach = tight.value ? 48 : 64
  const drop = tight.value ? 36 : 46
  const points = {
    prev: { x: -Math.min(reach, roomL), y: roomL < 44 ? -Math.min(28, roomT) : 0 },
    next: { x: Math.min(reach, roomR), y: roomR < 44 ? -Math.min(28, roomT) : 0 },
    vol: { x: 0, y: volDown.value ? Math.min(58, roomB) : -Math.min(58, roomT) },
    panel: { x: -Math.min(drop, roomL), y: Math.min(drop, roomB) },
    mode: { x: Math.min(drop, roomR), y: Math.min(drop, roomB) },
  }
  const names = Object.keys(points)
  const gap = btn + 6
  for (let pass = 0; pass < 4; pass += 1) {
    for (let i = 0; i < names.length; i += 1) {
      for (let j = i + 1; j < names.length; j += 1) {
        const a = points[names[i]]
        const b = points[names[j]]
        const dx = b.x - a.x
        const dy = b.y - a.y
        const dist = Math.hypot(dx, dy) || 0.01
        if (dist >= gap) {
          continue
        }
        const push = (gap - dist) / 2
        const ux = dx / dist
        const uy = dy / dist
        a.x -= ux * push
        a.y -= uy * push
        b.x += ux * push
        b.y += uy * push
      }
    }
  }
  return points
}

function openArc() {
  if (panelOpen.value || props.moving) {
    return
  }
  overStage.value = true
  controlsOpen.value = true
  const buttons = arcButtons()
  if (buttons.length < 5) {
    return
  }
  const points = arcPoints()
  gsap.killTweensOf(buttons)
  const bend = (point) => [{ x: 0, y: 0 }, { x: point.x * 0.4, y: point.y * 0.2 - 10 }, point]
  travel(prevEl.value, bend(points.prev))
  travel(nextEl.value, bend(points.next))
  travel(volEl.value, bend(points.vol))
  travel(panelBtn.value, bend(points.panel))
  travel(modeBtn.value, bend(points.mode))
}

function reallyClose() {
  const hovering = stageEl.value?.matches(':hover') || volEl.value?.matches(':hover')
  if (hovering || volHold.value || menu.value) {
    overStage.value = Boolean(stageEl.value?.matches(':hover'))
    volHot.value = Boolean(volEl.value?.matches(':hover'))
    return
  }
  if (performance.now() < wheelUntil) {
    return
  }
  controlsOpen.value = false
  volHot.value = false
  arcButtons().forEach((el) => {
    gsap.killTweensOf(el)
    gsap.to(el, { x: 0, y: 0, opacity: 0, duration: 0.28, ease: 'power2.in' })
  })
}

function tryClose() {
  window.clearTimeout(closeTimer)
  if (performance.now() < wheelUntil) {
    closeTimer = window.setTimeout(tryClose, 80)
    return
  }
  reallyClose()
}

function closeArc() {
  overStage.value = false
  tryClose()
}

function targetWidth() {
  const center = ballCenter()
  const leftRoom = Math.max(0, center.x)
  const rightRoom = Math.max(0, window.innerWidth - center.x)
  if (spreadMode.value === 'center') {
    const span = Math.max(0, Math.min(leftRoom, rightRoom) - 16) * 2
    return Math.max(0, Math.min(window.innerWidth * 0.6, span))
  }
  const room = spreadMode.value === 'right' ? rightRoom : leftRoom
  return Math.max(0, Math.min(window.innerWidth * 0.45, room - 24))
}

function tweenShell(width, open) {
  gsap.killTweensOf(shellState)
  gsap.to(shellState, {
    w: width,
    duration: open ? 0.46 : 0.28,
    ease: open ? 'power3.out' : 'power2.in',
    onUpdate: () => {
      shellWidth.value = shellState.w
    },
    onComplete: () => {
      if (!open) {
        panelOpen.value = false
      }
    },
  })
}

function togglePanel(force) {
  if (props.moving) {
    return
  }
  const open = typeof force === 'boolean' ? force : !panelOpen.value
  menu.value = null
  controlsOpen.value = false
  volHot.value = false
  arcButtons().forEach((el) => {
    gsap.killTweensOf(el)
    gsap.set(el, { x: 0, y: 0, opacity: 0 })
  })
  if (open) {
    panelOpen.value = true
    tweenShell(targetWidth(), true)
    return
  }
  tweenShell(0, false)
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
  event.preventDefault()
  event.stopPropagation()
  if (props.moving) {
    return
  }
  const pad = 8
  menu.value = { x: event.clientX, y: event.clientY, modes: false, flip: false, subShift: 0 }
  nextTick(() => {
    const width = menuEl.value?.offsetWidth || 168
    const height = menuEl.value?.offsetHeight || 180
    let x = event.clientX
    let y = event.clientY
    if (x + width > window.innerWidth - pad) {
      x = window.innerWidth - width - pad
    }
    if (y + height > window.innerHeight - pad) {
      y = window.innerHeight - height - pad
    }
    menu.value = {
      x: Math.max(pad, x),
      y: Math.max(pad, y),
      modes: false,
      flip: false,
      subShift: 0,
    }
  })
}

function openModes() {
  if (!menu.value || !menuEl.value) {
    return
  }
  const pad = 8
  const subWidth = 112
  const subHeight = MODES.length * 30 + 12
  const menuRect = menuEl.value.getBoundingClientRect()
  const spaceRight = window.innerWidth - menuRect.right
  const spaceLeft = menuRect.left
  const flip = spaceRight < subWidth + pad && spaceLeft >= spaceRight
  const rowTop = menuRect.bottom - 32
  const overflow = rowTop + subHeight - (window.innerHeight - pad)
  menu.value = { ...menu.value, modes: true, flip, subShift: overflow > 0 ? overflow : 0 }
  nextTick(() => {
    const box = subEl.value?.getBoundingClientRect()
    if (!box || !menu.value) {
      return
    }
    let nextFlip = menu.value.flip
    if (box.right > window.innerWidth - pad && spaceLeft >= subWidth) {
      nextFlip = true
    }
    if (box.left < pad && spaceRight >= subWidth) {
      nextFlip = false
    }
    const extra = box.bottom - (window.innerHeight - pad)
    const subShift = extra > 0 ? menu.value.subShift + extra : menu.value.subShift
    if (nextFlip !== menu.value.flip || subShift !== menu.value.subShift) {
      menu.value = { ...menu.value, flip: nextFlip, subShift: Math.max(0, subShift) }
    }
  })
}

function hideOrb() {
  menu.value = null
  emit('hide')
}

function setMode(id) {
  mode.value = id
  writeState()
  if (menu.value) {
    menu.value = { ...menu.value, modes: false }
  }
}

function onVolWheel(event) {
  event.preventDefault()
  event.stopPropagation()
  wheelUntil = performance.now() + 700
  const delta = event.deltaY > 0 ? -0.04 : 0.04
  volume.value = Math.min(1, Math.max(0, +(volume.value + delta).toFixed(2)))
}

function onVolEnter() {
  volHot.value = true
}

function onVolLeave() {
  volHot.value = false
  tryClose()
}

function volumeFromPointer(event) {
  const rect = stemEl.value?.getBoundingClientRect()
  if (!rect || rect.height <= 0) {
    return
  }
  const next = volDown.value
    ? (event.clientY - rect.top) / rect.height
    : (rect.bottom - event.clientY) / rect.height
  volume.value = Math.min(1, Math.max(0, +next.toFixed(2)))
}

function onStemDown(event) {
  volHold.value = true
  event.currentTarget.setPointerCapture?.(event.pointerId)
  volumeFromPointer(event)
}

function onStemMove(event) {
  if (!volHold.value) {
    return
  }
  volumeFromPointer(event)
}

function onTime() {
  currentTime.value = audio.value?.currentTime || 0
  if (currentTime.value - savedAt > 2) {
    savedAt = currentTime.value
    writeState()
  }
}

function seekAt(event) {
  if (!audio.value || !duration.value) {
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  const next = (event.clientX - rect.left) / Math.max(rect.width, 1)
  audio.value.currentTime = Math.min(duration.value, Math.max(0, next * duration.value))
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

function releaseVolume() {
  volHold.value = false
  tryClose()
}

function onPointerMove(event) {
  dragPos.value = clampPos(event.clientX - dragOffsetX, event.clientY - dragOffsetY)
}

function onPointerUp() {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
}

function startDrag(event) {
  if (!props.moving || !dockEl.value) {
    return
  }
  const rect = dockEl.value.getBoundingClientRect()
  dragOffsetX = event.clientX - rect.left
  dragOffsetY = event.clientY - rect.top
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

function finishMove() {
  const pos = dragPos.value || freePos()
  emit('move-done', {
    player: 'free',
    player_x: (pos.left + 36) / window.innerWidth,
    player_y: (pos.top + 36) / window.innerHeight,
  })
}

function onKey(event) {
  if (event.key === 'Escape' && props.moving) {
    emit('move-cancel')
  }
}

function onResize() {
  viewport.value += 1
}

onMounted(async () => {
  window.addEventListener('pointerup', releaseVolume)
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
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
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.clearTimeout(closeTimer)
  cancelAnimationFrame(raf)
  audio.value?.pause()
  writeState()
  audioCtx?.close()
})
</script>

<template>
  <div>
    <div v-if="moving" class="wv-move-mask" />
    <button v-if="moving" type="button" class="wv-move-done" @click="finishMove">完成</button>
    <div ref="dockEl" class="wv-orb-dock" :class="[placeClass, panelOpen ? 'is-panel' : '', moving ? 'is-moving' : '']" :style="dockStyle">
      <div v-show="panelOpen" class="wv-fused" :class="fusedClass" :style="fusedStyle">
        <div class="wv-fused-body">
          <template v-if="spreadMode === 'center'">
            <div class="wv-fused-side">
              <button type="button" class="wv-icon-btn" title="收回" @click="togglePanel(false)">
                <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 6l-6 6 6 6" /></svg>
              </button>
              <button type="button" class="wv-icon-btn" title="上一首" @click="step(-1)">‹</button>
              <button type="button" class="wv-icon-btn" title="播放" @click="togglePlay">{{ playing ? '❚❚' : '▶' }}</button>
              <button type="button" class="wv-icon-btn" title="下一首" @click="step(1)">›</button>
              <p class="wv-cap-title" :title="current?.title || ''">{{ current?.title || '还没有音频' }}</p>
            </div>
            <div class="wv-fused-gap" />
            <div class="wv-fused-side">
              <span class="wv-cap-time">{{ clock(currentTime) }} / {{ clock(duration) }}</span>
              <input class="wv-cap-range" type="range" min="0" max="1" step="0.01" :value="volume" title="音量" @input="volume = Number($event.target.value)" />
              <select class="wv-cap-select" :value="listId" title="歌单" @change="switchList($event.target.value)">
                <option v-for="item in LISTS" :key="item.id" :value="item.id">{{ item.label }}</option>
              </select>
              <button type="button" class="wv-icon-btn" :title="modeLabel" @click="cycleMode">↻</button>
              <button type="button" class="wv-icon-btn" title="添加" @click="fileInput.click()">+</button>
            </div>
          </template>
          <template v-else>
            <button type="button" class="wv-icon-btn" title="收回" @click="togglePanel(false)">
              <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
            <button type="button" class="wv-icon-btn" title="上一首" @click="step(-1)">‹</button>
            <button type="button" class="wv-icon-btn" title="播放" @click="togglePlay">{{ playing ? '❚❚' : '▶' }}</button>
            <button type="button" class="wv-icon-btn" title="下一首" @click="step(1)">›</button>
            <p class="wv-cap-title" :title="current?.title || ''">{{ current?.title || '还没有音频' }}</p>
            <span class="wv-cap-time">{{ clock(currentTime) }} / {{ clock(duration) }}</span>
            <input class="wv-cap-range" type="range" min="0" max="1" step="0.01" :value="volume" title="音量" @input="volume = Number($event.target.value)" />
            <select class="wv-cap-select" :value="listId" title="歌单" @change="switchList($event.target.value)">
              <option v-for="item in LISTS" :key="item.id" :value="item.id">{{ item.label }}</option>
            </select>
            <button type="button" class="wv-icon-btn" :title="modeLabel" @click="cycleMode">↻</button>
            <button type="button" class="wv-icon-btn" title="添加" @click="fileInput.click()">+</button>
            <button v-if="current" type="button" class="wv-icon-btn" title="移除" @click="removeAt(current)">×</button>
          </template>
        </div>
      </div>

      <div
        v-show="panelOpen"
        class="wv-progress"
        :style="progressBox"
      >
        <svg class="wv-progress-svg" :viewBox="`0 0 ${progressGeom.svgW} 72`">
          <defs>
            <linearGradient id="wvRainbow" gradientUnits="userSpaceOnUse" x1="0" y1="0" :x2="progressGeom.svgW" y2="0">
              <stop offset="0" stop-color="#e85d4c" />
              <stop offset="0.35" stop-color="#f2c14e" />
              <stop offset="0.68" stop-color="#3f6f57" />
              <stop offset="1" stop-color="#4c7fe8" />
            </linearGradient>
            <clipPath id="wvFuseClip">
              <rect :x="progressGeom.capX" y="8" :width="progressGeom.capW" height="56" rx="28" />
              <circle :cx="progressGeom.ballCx" cy="36" r="37" />
            </clipPath>
          </defs>
          <g clip-path="url(#wvFuseClip)">
            <path :d="topPath.d" class="wv-line-track" />
            <path :d="botPath.d" class="wv-line-track" />
            <path ref="topPathEl" :d="topPath.d" :stroke="strokePaint" :stroke-dasharray="measured.top" :stroke-dashoffset="measured.top * (1 - ratio)" class="wv-line-fill" />
            <path ref="botPathEl" :d="botPath.d" :stroke="strokePaint" :stroke-dasharray="measured.bot" :stroke-dashoffset="measured.bot * (1 - ratio)" class="wv-line-fill" />
          </g>
        </svg>
        <button type="button" class="wv-seek is-top" title="进度" @pointerdown="seekAt" />
        <button type="button" class="wv-seek is-bottom" title="进度" @pointerdown="seekAt" />
      </div>

      <div ref="stageEl" class="wv-orb-stage" :class="{ 'is-open': controlsOpen, 'is-playing': playing, 'is-tight': tight }" @mouseenter="openArc" @mouseleave="closeArc">
        <div class="wv-orb-pad" />
        <span v-for="note in notes" :key="note.id" :data-note="note.id" class="wv-orb-note">{{ note.glyph }}</span>
        <button ref="prevEl" type="button" class="wv-orb-btn" title="上一首" @click="step(-1)">‹</button>
        <button ref="nextEl" type="button" class="wv-orb-btn" title="下一首" @click="step(1)">›</button>
        <div
          ref="volEl"
          class="wv-orb-btn wv-orb-vol"
          :class="[(volHot || volHold) ? 'is-hot' : '', volDown ? 'is-down' : 'is-up']"
          @mouseenter="onVolEnter"
          @mouseleave="onVolLeave"
          @wheel.prevent="onVolWheel"
        >
          <div
            v-show="volHot || volHold"
            ref="stemEl"
            class="wv-stem"
            :class="volDown ? 'is-down' : 'is-up'"
            @pointerdown="onStemDown"
            @pointermove="onStemMove"
            @wheel.prevent="onVolWheel"
          >
            <span class="wv-stem-fill" :style="{ height: `${volume * 100}%` }" />
          </div>
          <button type="button" title="音量">
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10h3l4-3v10l-4-3H4z" /><path d="M15 9a4 4 0 010 6" /></svg>
          </button>
        </div>
        <button ref="panelBtn" type="button" class="wv-orb-btn" title="打开面板" @click="togglePanel(true)">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 8h14" /><path d="M5 12h14" /><path d="M5 16h10" /></svg>
        </button>
        <button ref="modeBtn" type="button" class="wv-orb-btn" :title="modeLabel" @click="cycleMode">
          <svg v-if="mode === 'shuffle'" viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h4l10 10" /><path d="M4 17h4L18 7" /><path d="M16 6h4v4" /><path d="M16 18h4v-4" /></svg>
          <svg v-else-if="mode === 'one'" viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 7h10v4" /><path d="M17 17H7v-4" /><path d="M12 11v2h2" /></svg>
          <svg v-else viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 7h10v4" /><path d="M17 17H7v-4" /><path d="M14 4l3 3-3 3" /><path d="M10 20l-3-3 3-3" /></svg>
        </button>
        <button type="button" class="wv-orb-ball" :class="moving ? 'is-drag' : ''" @pointerdown="startDrag" @click="togglePlay" @contextmenu="onMenu">
          <svg v-show="!((controlsOpen || panelOpen) && !moving)" class="wv-orb-glyph" :class="playing && !controlsOpen && !panelOpen ? 'is-spin' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M9 18V6l10-2v12" /><circle cx="7" cy="18" r="2.2" /><circle cx="17" cy="16" r="2.2" /></svg>
          <span v-show="(controlsOpen || panelOpen) && !moving" class="wv-orb-veil" :class="panelOpen ? 'is-same' : ''">
            <svg v-if="playing" viewBox="0 0 24 24" class="h-6 w-6 fill-white"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
            <svg v-else viewBox="0 0 24 24" class="h-6 w-6 fill-white"><path d="M8 5.2v13.6c0 .7.8 1.1 1.4.7l10.2-6.8c.6-.4.6-1.3 0-1.7L9.4 4.5C8.8 4.1 8 4.5 8 5.2z" /></svg>
          </span>
        </button>
      </div>
      <p v-show="!controlsOpen && !panelOpen && !moving" class="wv-song" :class="songClass"><span>{{ current?.title || '还没有音频' }}</span></p>
      <p v-if="errorMessage" class="wv-orb-error">{{ errorMessage }}</p>
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
    <Teleport to="body">
      <div v-if="menu" ref="menuEl" class="wv-orb-menu" :style="{ left: `${menu.x}px`, top: `${menu.y}px` }" @mouseleave="menu = null" @contextmenu.prevent>
        <button type="button" class="wv-menu-main" @click="togglePanel(!panelOpen)">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 8h14" /><path d="M5 12h14" /><path d="M5 16h10" /></svg>
          <span>{{ panelOpen ? '关闭面板' : '打开面板' }}</span>
        </button>
        <p class="wv-menu-title" :title="current?.title || ''">{{ current?.title || '还没有音频' }}</p>
        <div class="wv-menu-row">
          <button type="button" title="上一首" @click="step(-1)">⏮</button>
          <button type="button" title="播放" @click="togglePlay">{{ playing ? '⏸' : '▶' }}</button>
          <button type="button" title="下一首" @click="step(1)">⏭</button>
        </div>
        <div class="wv-menu-row">
          <span class="text-xs">音量</span>
          <input type="range" min="0" max="1" step="0.05" :value="volume" @input="volume = Number($event.target.value)" />
        </div>
        <div class="wv-menu-mode" @mouseenter="openModes">
          <span>播放方式 · {{ modeLabel }}</span>
          <div v-if="menu.modes" ref="subEl" class="wv-menu-sub" :class="menu.flip ? 'is-flip' : ''" :style="{ top: `${-(menu.subShift || 0)}px` }">
            <button v-for="item in MODES" :key="item.id" type="button" @click="setMode(item.id)">{{ item.label }}</button>
          </div>
        </div>
        <button type="button" class="wv-menu-main" @click="hideOrb">隐藏悬浮球</button>
      </div>
    </Teleport>
  </div>
</template>
