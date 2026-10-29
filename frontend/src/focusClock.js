// Shared focus clock. The floating timer and the timeline both read it.
import { reactive } from 'vue'

export const FOCUS_SECONDS = 25 * 60

export const focusClock = reactive({
  status: 'idle',
  left: FOCUS_SECONDS,
  total: FOCUS_SECONDS,
  endsAt: 0,
})

export function formatClock(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0))
  const minutes = Math.floor(value / 60)
  const rest = value % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}
