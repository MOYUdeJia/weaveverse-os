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
const RADIUS = 28
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

function movePet(x, y) {
  const nextX = Math.round(x)
  const nextY = Math.round(y)
  if (typeof window.moveTo === 'function') window.moveTo(nextX, nextY)
  bridge()?.focus_move?.(nextX, nextY)
}

let drag = null
let docked = null

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
  const originX = window.screenX
  const originY = window.screenY
  drag = { x: originX, y: originY, sx: event.screenX, sy: event.screenY }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onMove(event) {
  if (!drag) return
  docked = null
  movePet(drag.x + event.screenX - drag.sx, drag.y + event.screenY - drag.sy)
}

function onUp() {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  const home = parkPoint(window.screenX, window.screenY)
  drag = null
  docked = home
  if (home) movePet(home.x, home.y)
}

function onEnter() {
  if (!docked || drag || full.value || menu.value) return
  const box = screenBox()
  if (docked.x < box.x) movePet(box.x, docked.y)
  else if (docked.x > box.x + box.w - PET) movePet(box.x + box.w - PET, docked.y)
  else if (docked.y < box.y) movePet(docked.x, box.y)
}

function onLeave() {
  if (!docked || drag || full.value || menu.value) return
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
      <p class="quote">{{ QUOTES[quoteIndex] }}</p>
      <p v-if="styleId !== 'flip'" class="clock">{{ clock }}</p>
      <div v-else class="flip" aria-hidden="true">
        <span>{{ flipDigits[0] }}</span>
        <span>{{ flipDigits[1] }}</span>
        <b>:</b>
        <span>{{ flipDigits[2] }}</span>
        <span>{{ flipDigits[3] }}</span>
      </div>
      <p class="round">{{ resting ? '休息' : focusClock.name }} · {{ focusClock.cycle }}/{{ focusClock.cycles }}</p>
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
          <ellipse cx="66" cy="74" rx="52" ry="46" fill="#d4251c" />
          <path d="M66 30c8 8 18 7 24-2-11 2-17 7-24 13-7-6-13-11-24-13 5 9 16 10 24 2z" fill="#2c6b38" />
          <circle cx="66" cy="78" r="28" fill="none" stroke="#9d1c16" stroke-width="5" />
          <circle
            cx="66"
            cy="78"
            r="28"
            fill="none"
            stroke="#fff6ea"
            stroke-width="5"
            stroke-linecap="round"
            :stroke-dasharray="dash"
            :stroke-dashoffset="0"
            transform="rotate(-90 66 78)"
          />
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
  background: transparent;
  color: #fff6ea;
  user-select: none;
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
  background: #3a1412;
  color: #fff6ea;
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
  display: grid;
  min-height: 100vh;
  place-items: center;
  align-content: center;
  background: #16201d center / cover no-repeat;
  color: #fff6ea;
}

.quote {
  font-size: 28px;
  line-height: 1.2;
}

.clock {
  font-size: 18vw;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.05em;
  line-height: 0.9;
}

.flip {
  display: flex;
  gap: 8px;
}

.flip b {
  align-self: center;
  font-size: 12vw;
  font-weight: 700;
}

.flip span {
  min-width: 0.8em;
  padding: 0.08em 0.12em 0.02em;
  background: #101418;
  font-size: 16vw;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 0.9;
  text-align: center;
}

.round,
.hint {
  font-size: 16px;
}

.tools {
  display: grid;
  gap: 12px;
  justify-items: center;
  margin-top: 28px;
}

.tools select,
.tools button,
.upload {
  border: 0;
  background: rgba(255, 246, 234, 0.14);
  color: inherit;
  font: inherit;
  font-size: 14px;
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
  background: #fff6ea;
  color: #16201d;
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
</style>
