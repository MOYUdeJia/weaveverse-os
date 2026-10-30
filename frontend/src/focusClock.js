// Shared focus clock. The main window and the pet window each keep a copy
// and refresh it from the backend, which is the single countdown.
import { reactive } from 'vue'

import { getFocusLive, postFocusLive } from './api/client'

export const FOCUS_SECONDS = 25 * 60

export const focusClock = reactive({
  status: 'idle',
  phase: 'focus',
  left: FOCUS_SECONDS,
  total: FOCUS_SECONDS,
  endsAt: 0,
  name: '番茄',
  category: '学习',
  presetId: null,
  focusMinutes: 25,
  restMinutes: 5,
  cycle: 1,
  cycles: 1,
  notice: '',
})

let started = false
let completing = false

export function formatClock(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0))
  const minutes = Math.floor(value / 60)
  const rest = value % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

function applyLive(data) {
  if (!data) {
    return
  }
  focusClock.status = data.status || 'idle'
  focusClock.phase = data.phase || 'focus'
  focusClock.left = Number(data.left) || 0
  focusClock.total = Number(data.total) || FOCUS_SECONDS
  focusClock.endsAt = Number(data.ends_at) || 0
  focusClock.name = data.name || '番茄'
  focusClock.category = data.category || '学习'
  focusClock.presetId = data.preset_id ?? null
  focusClock.focusMinutes = Number(data.focus_minutes) || 25
  focusClock.restMinutes = Number(data.rest_minutes) || 5
  focusClock.cycle = Number(data.cycle) || 1
  focusClock.cycles = Number(data.cycles) || 1
  focusClock.notice = data.notice || ''
}

export async function focusCommand(action, extra = {}) {
  const data = await postFocusLive(action, extra)
  applyLive(data)
  return data
}

async function pull() {
  try {
    applyLive(await getFocusLive())
  } catch {
    // The next poll retries. A missed tick should not blank the clock.
  }
}

function tick() {
  if (focusClock.status !== 'running' || !focusClock.endsAt) {
    return
  }
  const left = Math.max(0, Math.round((focusClock.endsAt - Date.now()) / 1000))
  focusClock.left = left
  if (left > 0 || completing) {
    return
  }
  completing = true
  focusCommand('complete')
    .then((data) => {
      if (data?.status === 'done') {
        window.dispatchEvent(new CustomEvent('wv-timeline-refresh'))
      }
    })
    .catch(() => {})
    .finally(() => {
      completing = false
    })
}

export function bindFocusClock() {
  if (started) {
    return
  }
  started = true
  pull()
  window.setInterval(pull, 1000)
  window.setInterval(tick, 250)
}
