<script setup>
// Floating 25-minute focus timer. Finished rounds are written to the timeline.
import { computed, onMounted, ref, watch } from 'vue'

import { focusClock, focusCommand, formatClock } from '../focusClock'
import { showToast } from '../toast'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'expand'])

const noiseOn = ref(false)
const doneOpen = ref(false)
const desktop = ref(false)
let audioCtx = null
let noiseSource = null
let noiseGain = null

const ratio = computed(() => (focusClock.total ? focusClock.left / focusClock.total : 0))
const dash = computed(() => `${Math.max(0, Math.min(1, ratio.value)) * 100} 100`)
const label = computed(() => formatClock(focusClock.left))
const running = computed(() => focusClock.status === 'running' || focusClock.status === 'paused')

async function start() {
  try {
    await focusCommand(focusClock.status === 'paused' ? 'resume' : 'start')
  } catch (error) {
    showToast(error.message || '这一轮没有开始')
    return
  }
  if (noiseOn.value) {
    startNoise()
  }
}

async function pause() {
  if (focusClock.status !== 'running') {
    return
  }
  try {
    await focusCommand('pause')
  } catch (error) {
    showToast(error.message || '没有暂停')
  }
  stopNoise()
}

async function abandon() {
  stopNoise()
  noiseOn.value = false
  try {
    await focusCommand('abandon')
  } catch (error) {
    showToast(error.message || '没有放弃这一轮')
  }
  emit('close')
}

async function acknowledge() {
  doneOpen.value = false
  try {
    await focusCommand('acknowledge')
  } catch (error) {
    showToast(error.message || '没有记下这一轮')
  }
}

function startNoise() {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) {
    showToast('这个环境播不了白噪音')
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
  noiseGain.gain.value = 0.04
  noiseSource.connect(noiseGain).connect(audioCtx.destination)
  noiseSource.start()
  audioCtx.resume()
}

function stopNoise() {
  try {
    noiseSource?.stop()
  } catch {
    // already stopped
  }
  noiseSource = null
  noiseGain = null
}

function toggleNoise() {
  noiseOn.value = !noiseOn.value
  if (noiseOn.value && focusClock.status === 'running') {
    startNoise()
    return
  }
  stopNoise()
}

function chime() {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) {
    return
  }
  const ctx = new Ctx()
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.frequency.value = 784
  gain.gain.setValueAtTime(0.0001, ctx.currentTime)
  gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.02)
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.7)
  osc.connect(gain).connect(ctx.destination)
  osc.start()
  osc.stop(ctx.currentTime + 0.75)
}

watch(
  () => focusClock.status,
  (status, previous) => {
    if (status === 'done' && previous === 'running') {
      stopNoise()
      chime()
      doneOpen.value = true
    }
    if (status === 'idle') {
      doneOpen.value = false
    }
  },
)

onMounted(() => {
  desktop.value = Boolean(window.pywebview?.api?.open_focus_pet)
})
</script>

<template>
  <div class="wv-focus-root">
    <button
      v-if="!open && running && !desktop"
      type="button"
      class="wv-focus-chip"
      @click="emit('expand')"
    >
      <span aria-hidden="true">⏱️</span>
      {{ label }}
    </button>
    <section v-if="open" class="wv-focus" aria-label="专注">
      <div class="wv-focus-ring" :style="{ '--wv-dash': dash }">
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle cx="60" cy="60" r="52" class="wv-focus-track" />
          <circle cx="60" cy="60" r="52" class="wv-focus-value" />
        </svg>
        <p>{{ label }}</p>
      </div>
      <p class="wv-focus-caption">一轮 25 分钟</p>
      <div class="wv-focus-actions">
        <button v-if="focusClock.status !== 'running'" type="button" class="is-go" @click="start">
          {{ focusClock.status === 'paused' ? '继续' : '开始' }}
        </button>
        <button v-else type="button" @click="pause">暂停</button>
        <button type="button" :class="noiseOn ? 'is-on' : ''" @click="toggleNoise">白噪音</button>
        <button type="button" class="is-stop" :disabled="focusClock.status === 'idle'" @click="abandon">放弃</button>
      </div>
      <button type="button" class="wv-focus-close" @click="emit('close')">收起</button>
    </section>

    <div v-if="doneOpen" class="wv-focus-done" role="dialog" aria-modal="true" aria-labelledby="focus-done-title">
      <div>
        <h2 id="focus-done-title">专注结束，休息一下吧</h2>
        <p>这一轮已经记到时间线。</p>
        <button type="button" @click="acknowledge">知道了</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wv-focus {
  position: fixed;
  z-index: 46;
  right: 108px;
  bottom: 24px;
  width: 220px;
  padding: 18px 16px 14px;
  background: #fffcf7;
  color: #16201d;
}

.wv-focus-chip {
  position: fixed;
  z-index: 46;
  right: 108px;
  bottom: 28px;
  min-height: 44px;
  padding: 0 14px;
  background: #16201d;
  color: #fffcf7;
  font-weight: 650;
}

.wv-focus-ring {
  position: relative;
  width: 148px;
  height: 148px;
  margin: 0 auto;
}

.wv-focus-ring svg {
  width: 148px;
  height: 148px;
  transform: rotate(-90deg);
}

.wv-focus-track,
.wv-focus-value {
  fill: none;
  stroke-width: 8;
}

.wv-focus-track {
  stroke: #e7e1d6;
}

.wv-focus-value {
  stroke: #3f6f57;
  stroke-linecap: butt;
  stroke-dasharray: var(--wv-dash);
  pathLength: 100;
  transition: stroke-dasharray 0.9s linear;
}

.wv-focus-ring p {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  font-size: 32px;
  font-weight: 650;
  letter-spacing: -0.04em;
  font-variant-numeric: tabular-nums;
}

.wv-focus-caption {
  margin: 8px 0 0;
  text-align: center;
  font-size: 14px;
}

.wv-focus-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 14px;
}

.wv-focus-actions button,
.wv-focus-close,
.wv-focus-done button {
  min-height: 44px;
  background: #e7e1d6;
  font-weight: 650;
}

.wv-focus-actions .is-go,
.wv-focus-done button {
  background: #16201d;
  color: #fffcf7;
}

.wv-focus-actions .is-on {
  background: #3f6f57;
  color: #fffcf7;
}

.wv-focus-actions .is-stop {
  color: #9a4036;
}

.wv-focus-close {
  width: 100%;
  margin-top: 8px;
  background: transparent;
}

.wv-focus-done {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(22, 32, 29, 0.45);
}

.wv-focus-done div {
  width: min(420px, 100%);
  padding: 28px 24px;
  background: #fffcf7;
}

.wv-focus-done h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.15;
  letter-spacing: -0.03em;
}

.wv-focus-done p {
  margin: 10px 0 18px;
  font-size: 16px;
}

@media (max-width: 768px) {
  .wv-focus,
  .wv-focus-chip {
    right: auto;
    left: 50%;
    bottom: 96px;
    transform: translateX(-50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .wv-focus-value {
    transition: none;
  }
}

.wv-focus-actions button:focus-visible,
.wv-focus-close:focus-visible,
.wv-focus-chip:focus-visible,
.wv-focus-done button:focus-visible {
  outline: 2px solid #3f6f57;
  outline-offset: 2px;
}
</style>
