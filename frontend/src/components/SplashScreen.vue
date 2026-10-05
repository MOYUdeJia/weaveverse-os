<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

import splashImage from '../assets/splash/splash.png'

const emit = defineEmits(['finished'])

const SPLASH_DURATION_MS = 2000
const isLeaving = ref(false)
let leaveTimer
let finishTimer

onMounted(() => {
  leaveTimer = window.setTimeout(() => {
    isLeaving.value = true
  }, SPLASH_DURATION_MS - 420)

  finishTimer = window.setTimeout(() => {
    emit('finished')
  }, SPLASH_DURATION_MS)
})

onBeforeUnmount(() => {
  window.clearTimeout(leaveTimer)
  window.clearTimeout(finishTimer)
})
</script>

<template>
  <div
    class="fixed inset-0 z-50 grid place-items-center bg-[#121816] transition-opacity duration-500"
    :class="{ 'opacity-0': isLeaving, 'opacity-100': !isLeaving }"
  >
    <div class="flex flex-col items-center gap-7">
      <img
        :src="splashImage"
        alt="Weaveverse OS"
        class="h-40 w-40 animate-[breathe_1.8s_ease-in-out_infinite] rounded-full object-cover shadow-glow"
      />
      <div class="text-center">
        <p class="text-sm uppercase tracking-[0.32em] text-[#e2d9c8]">Weaveverse OS</p>
        <h1 class="mt-3 text-3xl font-semibold text-white">正在编织你的宇宙</h1>
      </div>
    </div>
  </div>
</template>
