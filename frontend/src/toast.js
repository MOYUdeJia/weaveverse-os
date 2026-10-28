import { ref } from 'vue'

export const toastText = ref('')
let timer = null

export function showToast(text, duration = 2000) {
  toastText.value = text
  clearTimeout(timer)
  timer = setTimeout(() => {
    toastText.value = ''
  }, duration)
}
