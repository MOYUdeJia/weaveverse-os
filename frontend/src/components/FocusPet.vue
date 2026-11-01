<script setup>
// Desktop tomato. The fruit stays one size. The menu sits beside it.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { bindFocusClock, focusClock, focusCommand, formatClock } from '../focusClock'
import { claimNoise, noiseKind, rememberNoiseKind, startNoise, stopNoise, unlockNoise } from '../focusNoise'
import { getFocusBackgrounds, uploadFocusBackground } from '../api/client'
import { showToast } from '../toast'

const NOISES = [
  { id: 'rain', label: '雨声' },
  { id: 'cafe', label: '咖啡厅' },
  { id: 'tone', label: '纯音' },
  { id: 'off', label: '安静' },
]
const QUOTES = [
  '这一轮只做一件事',
  '做完再看消息',
  '剩下的比刚才少',
  '坐稳，直到它走完',
  '休息也算这一轮',
]
const STYLES = [
  { id: 'digital', label: '数字' },
  { id: 'flip', label: '翻页' },
  { id: 'black', label: '全黑' },
]
const FIELDS = [
  { id: 'ink', name: '墨', color: '#16201d' },
  { id: 'leaf', name: '叶', color: '#1d3d2e' },
  { id: 'dawn', name: '纸', color: '#f4efe7' },
]

const menu = ref(false)
const settings = ref(false)
const full = ref(false)
const noiseId = ref('rain')
const quoteIndex = ref(0)
const styleId = ref('digital')
const fieldId = ref('ink')
const backgrounds = ref([])
const picture = ref('')
const draft = ref({ focus_minutes: 25, rest_minutes: 5, cycles: 1 })
let quoteTimer = 0

const PET = 132
const RADIUS = 33
const RING = 2 * Math.PI * RADIUS

const clock = computed(() => formatClock(focusClock.left))
const progress = computed(() => {
  const total = Number(focusClock.total) || 1
  return Math.min(1, Math.max(0, Number(focusClock.left) / total))
})
const dash = computed(() => `${(progress.value * RING).toFixed(1)} ${RING.toFixed(1)}`)
const pauseLabel = computed(() => (focusClock.status === 'running' ? '暂停' : '继续'))
const endLabel = computed(() => (focusClock.phase === 'rest' ? '结束休息' : '结束专注'))
const resting = computed(() => focusClock.phase === 'rest')
const faceInk = computed(() => (fieldId.value === 'dawn' && full.value ? '#16201d' : '#fff6ea'))
const field = computed(() => FIELDS.find((item) => item.id === fieldId.value) || FIELDS[0])
const flipDigits = computed(() => clock.value.replace(':', '').split(''))
const flipShown = ref(['0', '0', '0', '0'])
const flipTurn = ref([false, false, false, false])
let flipTimers = []

watch(
  flipDigits,
  (next) => {
    next.forEach((digit, index) => {
      if (digit === flipShown.value[index]) return
      flipTurn.value[index] = false
      window.requestAnimationFrame(() => {
        flipTurn.value[index] = true
      })
      window.clearTimeout(flipTimers[index])
      flipTimers[index] = window.setTimeout(() => {
        flipShown.value[index] = digit
        flipTurn.value[index] = false
      }, 180)
    })
  },
  { immediate: true },
)

function bridge() {
  return window.pywebview?.api || null
}

async function command(action, extra) {
  try {
    await focusCommand(action, extra)
  } catch (error) {
    showToast(error.message || '专注没有改成')
  }
}

function screenBox() {
  return {
    x: window.screen.availLeft || 0,
    y: window.screen.availTop || 0,
    w: window.screen.availWidth || window.screen.width,
    h: window.screen.availHeight || window.screen.height,
  }
}

let drag = null
let docked = null
let placed = null
let quietUntil = 0
let pendingMove = null
let moveFrame = 0

function flushMove() {
  moveFrame = 0
  const point = pendingMove
  pendingMove = null
  if (!point) return
  if (placed && placed.x === point.x && placed.y === point.y) return
  placed = point
  quietUntil = Date.now() + 360
  const api = bridge()
  if (api && typeof api.focus_move === 'function') {
    api.focus_move(point.x, point.y)
    return
  }
  if (typeof window.moveTo === 'function') window.moveTo(point.x, point.y)
}

function movePet(x, y) {
  pendingMove = { x: Math.round(x), y: Math.round(y) }
  if (moveFrame) return
  moveFrame = window.requestAnimationFrame(flushMove)
}

function parkPoint(x, y) {
  const box = screenBox()
  if (x <= box.x + 28) return { x: box.x - PET + 18, y }
  if (x + PET >= box.x + box.w - 28) return { x: box.x + box.w - 18, y }
  if (y <= box.y + 28) return { x, y: box.y - PET + 18 }
  return null
}

async function openMenu(event) {
  event.preventDefault()
  unlockNoise()
  settings.value = false
  draft.value = {
    focus_minutes: focusClock.focusMinutes,
    rest_minutes: focusClock.restMinutes,
    cycles: focusClock.cycles,
  }
  menu.value = true
  if (!full.value) await bridge()?.focus_resize?.(300, 220)
}

async function closeMenu() {
  menu.value = false
  settings.value = false
  if (!full.value) await bridge()?.focus_resize?.(PET, PET)
}

async function pauseOrResume() {
  if (focusClock.status !== 'running' && noiseId.value !== 'off' && focusClock.phase !== 'rest') {
    claimNoise(noiseId.value)
  }
  if (focusClock.status === 'running') stopNoise()
  await command(focusClock.status === 'running' ? 'pause' : focusClock.status === 'paused' ? 'resume' : 'start')
  await closeMenu()
}

async function endRound() {
  if (focusClock.phase === 'rest') {
    stopNoise()
    await command('end_rest')
    await closeMenu()
    return
  }
  const record = window.confirm('把这次放弃记下来？')
  stopNoise()
  await command('abandon', { record, interrupt: record ? '自己停下' : '' })
  await closeMenu()
}

function markFull(on) {
  full.value = on
  document.documentElement.classList.toggle('is-pet-full', on)
}

async function enterFull() {
  claimNoise(noiseId.value)
  markFull(true)
  menu.value = false
  await bridge()?.focus_resize?.(PET, PET)
  await bridge()?.focus_fullscreen?.(true)
}

async function leaveFull() {
  stopNoise()
  markFull(false)
  menu.value = false
  await bridge()?.focus_fullscreen?.(false)
}

async function hidePet() {
  stopNoise()
  await closeMenu()
  await bridge()?.focus_hide?.()
}

async function saveDraft() {
  await command('preset', {
    name: focusClock.name,
    category: focusClock.category,
    preset_id: focusClock.presetId,
    focus_minutes: Number(draft.value.focus_minutes),
    rest_minutes: Number(draft.value.rest_minutes),
    cycles: Number(draft.value.cycles),
  })
  settings.value = false
}

function chooseNoise(id) {
  noiseId.value = id
  rememberNoiseKind(id)
  if (full.value && focusClock.status === 'running' && focusClock.phase !== 'rest') claimNoise(id)
  else if (id === 'off') stopNoise()
  else unlockNoise()
}

async function loadBackgrounds() {
  try {
    const data = await getFocusBackgrounds()
    backgrounds.value = data.items || []
  } catch {
    backgrounds.value = FIELDS
  }
}

async function onUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const saved = await uploadFocusBackground(file)
    await loadBackgrounds()
    picture.value = saved.url
    fieldId.value = ''
  } catch (error) {
    showToast(error.message || '背景没有放上去')
  }
}

function pickField(item) {
  fieldId.value = item.color ? item.id : ''
  picture.value = item.url || ''
}

function onDown(event) {
  if (event.button !== 0 || full.value || menu.value) return
  unlockNoise()
  bridge()?.focus_begin_drag?.()
}

function onMove(event) {
  if (!drag) return
  const dx = Math.round(event.screenX - drag.sx)
  const dy = Math.round(event.screenY - drag.sy)
  if (!drag.moved && dx * dx + dy * dy < 9) return
  drag.moved = true
  drag.sx = event.screenX
  drag.sy = event.screenY
  docked = null
  bridge()?.focus_nudge?.(dx, dy)
}

function onUp() {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  drag = null
  docked = null
}

function hoverBlocked() {
  return !docked || drag || full.value || menu.value || Date.now() < quietUntil
}

function onEnter() {
  if (hoverBlocked()) return
  const box = screenBox()
  if (docked.x < box.x) movePet(box.x, docked.y)
  else if (docked.x > box.x + box.w - PET) movePet(box.x + box.w - PET, docked.y)
  else if (docked.y < box.y) movePet(docked.x, box.y)
}

function onLeave() {
  if (hoverBlocked()) return
  movePet(docked.x, docked.y)
}

function onKey(event) {
  if (event.key === 'Escape' && full.value) leaveFull()
  else if (event.key === 'Escape' && menu.value) closeMenu()
}

watch(
  () => focusClock.notice,
  (notice) => {
    if (notice === 'rest') showToast(`记上了。休息 ${focusClock.restMinutes} 分钟`)
  },
)

onMounted(() => {
  noiseId.value = noiseKind()
  bindFocusClock()
  loadBackgrounds()
  window.addEventListener('keydown', onKey)
  bridge()?.focus_ready?.()
  quoteTimer = window.setInterval(() => {
    quoteIndex.value = (quoteIndex.value + 1) % QUOTES.length
  }, 8000)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.clearInterval(quoteTimer)
  document.documentElement.classList.remove('is-pet-full')
  stopNoise()
})
</script>

<template>
  <div class="pet" :class="{ 'is-full': full, 'is-black': full && styleId === 'black' }" @contextmenu="openMenu" @mouseenter="onEnter" @mouseleave="onLeave">
    <div
      v-if="full"
      class="stage"
      :style="picture ? { backgroundImage: `url(${picture})` } : { background: field.color, color: faceInk }"
    >
      <div class="readout">
        <p class="quote">{{ QUOTES[quoteIndex] }}</p>
        <p v-if="styleId !== 'flip'" class="clock">{{ clock }}</p>
        <div v-else class="flip" aria-hidden="true">
          <span class="card" :class="{ 'is-turn': flipTurn[0] }">{{ flipShown[0] }}</span>
          <span class="card" :class="{ 'is-turn': flipTurn[1] }">{{ flipShown[1] }}</span>
          <b>:</b>
          <span class="card" :class="{ 'is-turn': flipTurn[2] }">{{ flipShown[2] }}</span>
          <span class="card" :class="{ 'is-turn': flipTurn[3] }">{{ flipShown[3] }}</span>
        </div>
        <p class="round">{{ resting ? '休息' : focusClock.name }} · {{ focusClock.cycle }}/{{ focusClock.cycles }}</p>
      </div>
      <div class="tools">
        <label>
          声音
          <select :value="noiseId" @change="chooseNoise($event.target.value)">
            <option v-for="item in NOISES" :key="item.id" :value="item.id">{{ item.label }}</option>
          </select>
        </label>
        <div class="choices">
          <button v-for="item in backgrounds" :key="item.id" type="button" @click="pickField(item)">{{ item.name }}</button>
          <label class="upload">
            上传
            <input type="file" accept="image/png,image/jpeg,image/webp" @change="onUpload" />
          </label>
        </div>
        <div class="choices">
          <button v-for="item in STYLES" :key="item.id" type="button" :class="{ 'is-on': styleId === item.id }" @click="styleId = item.id">
            {{ item.label }}
          </button>
        </div>
      </div>
      <p class="hint">按 Esc 回到番茄</p>
    </div>

    <template v-else>
      <div v-if="menu" class="menu-mask" @mousedown.stop @click="closeMenu" />
      <button type="button" class="tomato" :aria-label="`专注倒计时 ${clock}`" @mousedown="onDown">
        <svg viewBox="0 0 132 132" aria-hidden="true">
          <defs>
            <radialGradient id="pet-skin" cx="42%" cy="36%" r="68%">
              <stop offset="0%" stop-color="#ffb2a4" />
              <stop offset="28%" stop-color="#e24b3a" />
              <stop offset="62%" stop-color="#c43228" />
              <stop offset="100%" stop-color="#7c221c" />
            </radialGradient>
            <radialGradient id="pet-shade" cx="70%" cy="78%" r="55%">
              <stop offset="0%" stop-color="#5c1614" stop-opacity="0.45" />
              <stop offset="70%" stop-color="#5c1614" stop-opacity="0" />
            </radialGradient>
            <linearGradient id="pet-leaf" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#6eaf62" />
              <stop offset="100%" stop-color="#1d4a28" />
            </linearGradient>
            <clipPath id="pet-flesh">
              <ellipse cx="66" cy="76" rx="47" ry="41" />
            </clipPath>
          </defs>
          <ellipse cx="66" cy="78" rx="49" ry="43" fill="#6a1a16" />
          <ellipse cx="66" cy="75" rx="48" ry="42" fill="url(#pet-skin)" />
          <ellipse cx="70" cy="86" rx="36" ry="28" fill="url(#pet-shade)" />
          <ellipse cx="48" cy="62" rx="14" ry="8" fill="#fff4ec" opacity="0.55" />
          <g clip-path="url(#pet-flesh)">
            <circle cx="66" cy="78" r="33" fill="none" stroke="#7a1e18" stroke-width="5" />
            <circle
              cx="66"
              cy="78"
              r="33"
              fill="none"
              stroke="#fff6ea"
              stroke-width="5"
              class="ring"
              stroke-linecap="round"
              :stroke-dasharray="dash"
              transform="rotate(-90 66 78)"
            />
          </g>
          <path d="M64 36c2 8 1 14 0 18" fill="none" stroke="#6d8f45" stroke-width="3.5" stroke-linecap="round" />
          <path d="M66 38c-16-2-28 8-30 16 10-2 20-1 30-8z" fill="url(#pet-leaf)" />
          <path d="M66 38c14-8 30-4 34 6-12 1-22 0-34-6z" fill="#2f6a3c" />
          <path d="M66 40c8 6 20 8 28 4-10 1-18-1-28-6z" fill="#8fce78" opacity="0.85" />
        </svg>
        <p class="face">{{ clock }}</p>
        <p v-if="resting" class="badge">休息</p>
      </button>
      <div v-if="menu" class="menu" @mousedown.stop @contextmenu.prevent.stop>
        <template v-if="!settings">
          <button type="button" @click="pauseOrResume">{{ pauseLabel }}</button>
          <button type="button" @click="settings = true">设置</button>
          <button type="button" @click="enterFull">全屏</button>
          <button type="button" @click="endRound">{{ endLabel }}</button>
          <button type="button" @click="hidePet">隐藏</button>
        </template>
        <form v-else class="draft" @submit.prevent="saveDraft">
          <label>专注<input v-model.number="draft.focus_minutes" type="number" min="5" max="180" /></label>
          <label>休息<input v-model.number="draft.rest_minutes" type="number" min="1" max="60" /></label>
          <label>循环<input v-model.number="draft.cycles" type="number" min="1" max="12" /></label>
          <button type="submit">保存</button>
        </form>
      </div>
    </template>
  </div>
</template>

<style scoped>
.pet {
  min-height: 100%;
  background: #010001;
  color: #fff6ea;
  user-select: none;
}

.pet.is-full {
  background: #101418;
}

.tomato {
  position: relative;
  width: 132px;
  height: 132px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: grab;
}

.tomato:active {
  cursor: grabbing;
}

.tomato svg {
  display: block;
  width: 132px;
  height: 132px;
}

.ring {
  transition: stroke-dasharray 0.9s linear;
}

.face,
.clock,
.quote,
.round,
.hint,
.badge {
  margin: 0;
}

.face {
  position: absolute;
  top: 70px;
  right: 0;
  left: 0;
  color: #fff6ea;
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
  line-height: 1;
  text-align: center;
}

.badge {
  position: absolute;
  top: 96px;
  right: 0;
  left: 0;
  color: #fff6ea;
  font-size: 12px;
  text-align: center;
}

.menu-mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  background: transparent;
}

.menu {
  position: absolute;
  top: 28px;
  left: 140px;
  z-index: 1000;
  width: 148px;
  overflow: hidden;
  border-radius: 14px;
  background: #3a1412;
  color: #fff6ea;
  animation: menu-in 180ms cubic-bezier(0.2, 0, 0, 1);
}

.menu button,
.draft label {
  display: block;
  width: 100%;
  margin: 0;
  padding: 8px 10px;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 14px;
  line-height: 1.2;
  text-align: left;
}

.menu button:hover,
.menu button:focus-visible {
  background: #5a221c;
}

.menu button {
  transition:
    background-color 120ms ease,
    transform 120ms cubic-bezier(0.2, 0, 0, 1);
}

.menu button:active {
  transform: scale(0.97);
}

@keyframes menu-in {
  from {
    opacity: 0;
    transform: translateX(-8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

.draft input {
  width: 52px;
  margin-left: 8px;
  border: 0;
  background: #5a221c;
  color: inherit;
  font: inherit;
  font-variant-numeric: tabular-nums;
}

.menu button:focus-visible,
.draft input:focus-visible,
.tools select:focus-visible,
.tools button:focus-visible {
  outline: 2px solid #fff6ea;
  outline-offset: -2px;
}

.stage {
  position: relative;
  z-index: 1;
  isolation: isolate;
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 28px;
  padding: 32px 16px;
  background: #16201d center / cover no-repeat;
  color: #fff6ea;
}

.readout {
  position: relative;
  z-index: 1;
  display: flex;
  max-width: 100%;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.quote {
  font-size: 28px;
  line-height: 1.2;
}

.clock {
  max-width: 100%;
  font-size: clamp(72px, 14vw, 168px);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.05em;
  line-height: 0.9;
}

.flip {
  display: flex;
  max-width: 100%;
  align-items: center;
  gap: 8px;
  perspective: 900px;
}

.flip b {
  align-self: center;
  font-size: clamp(40px, 8vw, 96px);
  font-weight: 700;
}

.card {
  position: relative;
  display: grid;
  min-width: 0.78em;
  place-items: center;
  overflow: hidden;
  padding: 0.06em 0.1em 0;
  background: #241816;
  color: #fff6ea;
  font-size: clamp(56px, 12vw, 140px);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 0.9;
  text-align: center;
  transform-origin: center center;
  transform-style: preserve-3d;
}

.card::after {
  content: '';
  position: absolute;
  right: 0;
  left: 0;
  top: 50%;
  height: 4px;
  background: #100c0b;
}

.card.is-turn {
  animation: card-turn 0.36s ease-in;
}

@keyframes card-turn {
  0% { transform: rotateX(0deg); }
  48% { transform: rotateX(-90deg); }
  52% { transform: rotateX(-90deg); }
  100% { transform: rotateX(0deg); }
}

.round,
.hint {
  font-size: 16px;
}

.tools {
  position: relative;
  z-index: 4;
  display: grid;
  gap: 12px;
  justify-items: center;
  padding: 16px;
  background: #16201d;
}

.tools select,
.tools button,
.upload {
  position: relative;
  z-index: 5;
  border: 0;
  background: #fff6ea;
  color: #16201d;
  font: inherit;
  font-size: 14px;
}

.tools select {
  min-height: 36px;
  padding: 0 8px;
  color-scheme: light;
}

.tools option {
  background: #fff6ea;
  color: #16201d;
}

.choices {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.tools button,
.upload {
  padding: 6px 10px;
}

.upload input {
  display: none;
}

.tools button.is-on {
  background: #c43228;
  color: #fff6ea;
}

.is-black .quote,
.is-black .round,
.is-black .tools,
.is-black .hint {
  opacity: 0;
}

.is-black:hover .quote,
.is-black:hover .round,
.is-black:hover .tools,
.is-black:hover .hint {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .ring {
    transition: none;
  }

  .card.is-turn {
    animation: none;
  }

  .menu {
    animation: none;
  }

  .menu button {
    transition: none;
  }
}
</style>
