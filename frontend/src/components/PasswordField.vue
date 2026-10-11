<script setup>
// 自己画的密码框。系统自带的眼睛在失焦后不会跟着输入框回来。
import { ref } from 'vue'

defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'current-password' },
})

const emit = defineEmits(['update:modelValue'])

const root = ref(null)
const revealed = ref(false)

function onBlur() {
  requestAnimationFrame(() => {
    if (!root.value?.contains(document.activeElement)) {
      revealed.value = false
    }
  })
}
</script>

<template>
  <div ref="root" class="wv-pass relative" @focusout="onBlur">
    <input
      :type="revealed ? 'text' : 'password'"
      :value="modelValue"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      class="h-10 w-full rounded border border-black/10 bg-white px-3 pr-10 text-sm outline-none focus:border-moss"
      @input="emit('update:modelValue', $event.target.value)"
    />
    <button
      type="button"
      tabindex="-1"
      class="wv-pass-eye absolute right-1 top-1 grid h-8 w-8 place-items-center rounded text-ink/55 hover:bg-black/5"
      :title="revealed ? '隐藏' : '显示'"
      @mousedown.prevent
      @click="revealed = !revealed"
    >
      <svg v-if="revealed" viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M3 3l18 18" />
        <path d="M10.5 10.7a2 2 0 002.8 2.8" />
        <path d="M9.9 5.2A10.8 10.8 0 0112 5c5 0 8.5 3.5 10 7-0.6 1.4-1.6 2.8-2.8 4" />
        <path d="M6.1 6.3C4.2 7.6 2.8 9.3 2 12c1.2 2.8 4 5.5 8 6.4" />
      </svg>
      <svg v-else viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
input::-ms-reveal,
input::-ms-clear {
  display: none;
}

.wv-pass-eye {
  display: none;
}

.wv-pass:focus-within .wv-pass-eye {
  display: grid;
}
</style>
