import { ref } from 'vue'

export const toastText = ref('')
let timer = null

export function showToast(text) {
  toastText.value = text
  clearTimeout(timer)
  timer = setTimeout(() => {
    toastText.value = ''
  }, 2000)
}
