// Shared focus clock. The main window and the pet window each keep a copy
// and refresh it from the backend, which is the single countdown.
import { reactive } from 'vue'

import { getFocusLive, postFocusLive } from './api/client'

export const FOCUS_SECONDS = 25 * 60

export const focusClock = reactive({
  status: 'idle',
  left: FOCUS_SECONDS,
  total: FOCUS_SECONDS,
  endsAt: 0,
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
  focusClock.left = Number(data.left) || 0
  focusClock.total = Number(data.total) || FOCUS_SECONDS
  focusClock.endsAt = Number(data.ends_at) || 0
}

export async function focusCommand(action) {
  const data = await postFocusLive(action)
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
