// Stamp injected by Vite at startup or at `npm run build`.
export const frontendBuiltAt = __WV_BUILD_TIME__

export function formatBuiltAt(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value || '未知'
  }
  const pad = (part) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
