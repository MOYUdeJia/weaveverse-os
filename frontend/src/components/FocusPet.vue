<script setup>
// Desktop pet. One glass bead, the minutes still on the thread.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { bindFocusClock, focusClock, focusCommand, formatClock } from '../focusClock'
import { showToast } from '../toast'

const LINES = [
  '这一轮只做一件事。',
  '线还在，慢慢抽就好。',
  '先把这一分钟织完。',
  '桌面可以很吵，这里不用。',
  '剩下的时间比计划更真。',
]

const menu = ref(false)
const full = ref(false)
const noiseOn = ref(false)
const line = ref(LINES[0])
let audioCtx = null
let noiseSource = null
let noiseGain = null
let drag = null
let moving = false
let peeking = false

const ratio = computed(() => (focusClock.total ? focusClock.left / focusClock.total : 0))
const dash = computed(() => `${Math.max(0, Math.min(1, ratio.value)) * 100} 100`)
const minutesLeft = computed(() => (focusClock.left <= 0 ? 0 : Math.ceil(focusClock.left / 60)))
const clock = computed(() => formatClock(focusClock.left))
const pauseLabel = computed(() => (focusClock.status === 'running' ? '暂停' : '继续'))

function bridge() {
  return window.pywebview?.api || null
}

async function command(action) {
  try {
    await focusCommand(action)
  } catch (error) {
    showToast(error.message || '专注没有改成')
  }
}

function startNoise() {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) {
    noiseOn.value = false
    return
  }
  if (!audioCtx) {
    audioCtx = new Ctx()
  }
  const length = audioCtx.sampleRate * 2
  const buffer = audioCtx.createBuffer(1, length, audioCtx.sampleRate)
  const data = buffer.getChannelData(0)
  for (let index = 0; index < length; index += 1) {
    data[index] = Math.random() * 2 - 1
  }
  noiseSource = audioCtx.createBufferSource()
  noiseSource.buffer = buffer
  noiseSource.loop = true
  noiseGain = audioCtx.createGain()
  noiseGain.gain.value = 0.045
  noiseSource.connect(noiseGain).connect(audioCtx.destination)
  noiseSource.start()
  audioCtx.resume()
  noiseOn.value = true
}

function stopNoise() {
  try {
    noiseSource?.stop()
  } catch {
    // already stopped
  }
  noiseSource = null
  noiseGain = null
  noiseOn.value = false
}

async function openMenu(event) {
  event.preventDefault()
  if (full.value) {
    menu.value = !menu.value
    return
  }
  menu.value = true
  const api = bridge()
  await api?.focus_peek?.(true)
  await api?.focus_resize?.(188, 268)
}

async function closeMenu() {
  menu.value = false
  if (!full.value) {
    await bridge()?.focus_resize?.(160, 160)
  }
}

async function pauseOrResume() {
  await command(focusClock.status === 'running' ? 'pause' : focusClock.status === 'paused' ? 'resume' : 'start')
  await closeMenu()
}

async function abandon() {
  stopNoise()
  await command('abandon')
  if (full.value) {
    await leaveFull()
  }
  await closeMenu()
  await bridge()?.focus_hide?.()
}

async function enterFull() {
  await closeMenu()
  line.value = LINES[Math.floor(Math.random() * LINES.length)]
  full.value = true
  await bridge()?.focus_fullscreen?.(true)
  startNoise()
}

async function leaveFull() {
  stopNoise()
  full.value = false
  menu.value = false
  await bridge()?.focus_fullscreen?.(false)
}

async function hidePet() {
  await closeMenu()
  await bridge()?.focus_hide?.()
}

function onKey(event) {
  if (event.key === 'Escape' && full.value) {
    leaveFull()
  } else if (event.key === 'Escape' && menu.value) {
    closeMenu()
  }
}

async function onDown(event) {
  if (event.button !== 0 || full.value || menu.value) {
    return
  }
  const api = bridge()
  if (!api?.focus_geometry) {
    return
  }
  const geo = await api.focus_geometry()
  if (!geo?.ok) {
    return
  }
  drag = { x: geo.x, y: geo.y, sx: event.screenX, sy: event.screenY }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onMove(event) {
  if (!drag || moving) {
    return
  }
  const api = bridge()
  if (!api?.focus_move) {
    return
  }
  moving = true
  api.focus_move(drag.x + event.screenX - drag.sx, drag.y + event.screenY - drag.sy).finally(() => {
    moving = false
  })
}

async function onUp() {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  drag = null
  await bridge()?.focus_settle?.()
}

async function onEnter() {
  if (drag || full.value || menu.value) {
    return
  }
  peeking = true
  try {
    await bridge()?.focus_peek?.(true)
  } finally {
    peeking = false
  }
}

function onLeave() {
  if (drag || full.value || menu.value || peeking) {
    return
  }
  bridge()?.focus_peek?.(false)
}

onMounted(() => {
  bindFocusClock()
  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  stopNoise()
  audioCtx?.close()
})
</script>

<template>
  <div
    class="pet"
    :class="{ 'is-full': full }"
    @mousedown="onDown"
    @contextmenu="openMenu"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <div v-if="full" class="stage">
      <p class="clock">{{ clock }}</p>
      <p class="line">{{ line }}</p>
      <button type="button" @click="noiseOn ? stopNoise() : startNoise()">
        {{ noiseOn ? '关掉白噪音' : '打开白噪音' }}
      </button>
      <p class="hint">按 Esc 回到小窗</p>
    </div>
    <template v-else>
      <div class="bead" :style="{ '--wv-dash': dash }">
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle cx="60" cy="60" r="52" class="track" />
          <circle cx="60" cy="60" r="52" class="value" pathLength="100" />
        </svg>
        <p>{{ minutesLeft }}</p>
      </div>
      <div v-if="menu" class="menu" @mousedown.stop>
        <button type="button" @click="pauseOrResume">{{ pauseLabel }}</button>
        <button type="button" @click="abandon">放弃</button>
        <button type="button" @click="enterFull">进入全屏专注</button>
        <button type="button" @click="hidePet">隐藏</button>
      </div>
    </template>
    <div v-if="full && menu" class="menu is-full-menu" @mousedown.stop>
      <button type="button" @click="pauseOrResume">{{ pauseLabel }}</button>
      <button type="button" @click="abandon">放弃</button>
      <button type="button" @click="leaveFull">退出全屏</button>
      <button type="button" @click="hidePet">隐藏</button>
    </div>
  </div>
</template>

<style scoped>
.pet {
  min-height: 100%;
  background: transparent;
  color: #16201d;
  user-select: none;
}

.bead {
  position: relative;
  width: 148px;
  height: 148px;
  margin: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
  cursor: grab;
}

.bead:active {
  cursor: grabbing;
}

.bead svg {
  width: 148px;
  height: 148px;
  transform: rotate(-90deg);
}

.track,
.value {
  fill: none;
  stroke-width: 7;
}

.track {
  stroke: rgba(22, 32, 29, 0.12);
}

.value {
  stroke: #3f6f57;
  stroke-dasharray: var(--wv-dash);
  path-length: 100;
}

.bead p,
.clock {
  font-variant-numeric: tabular-nums;
  font-weight: 650;
  letter-spacing: -0.04em;
}

.bead p {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  font-size: 48px;
  line-height: 1;
}

.menu {
  display: grid;
  gap: 6px;
  padding: 0 10px 10px;
}

.menu button,
.stage button {
  min-height: 40px;
  background: rgba(255, 255, 255, 0.72);
  color: #16201d;
  font-weight: 650;
}

.menu button:focus-visible,
.stage button:focus-visible {
  outline: 2px solid #3f6f57;
  outline-offset: 2px;
}

.stage {
  display: grid;
  place-items: center;
  align-content: center;
  min-height: 100vh;
  padding: 32px;
  background: rgba(12, 18, 16, 0.78);
  color: #f6f3ec;
}

.clock {
  margin: 0;
  font-size: 18vw;
  line-height: 0.9;
}

.line {
  max-width: 16em;
  margin: 18px 0 0;
  font-size: 28px;
  line-height: 1.35;
  text-align: center;
}

.stage button {
  margin-top: 28px;
  padding: 0 18px;
  background: #f6f3ec;
}

.hint {
  margin: 14px 0 0;
  font-size: 16px;
}

.is-full-menu {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 220px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.92);
}

@media (prefers-reduced-motion: reduce) {
  .value {
    transition: none;
  }
}
</style>
