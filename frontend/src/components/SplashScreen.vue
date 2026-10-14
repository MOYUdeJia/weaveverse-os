<script setup>
import lottie from 'lottie-web'
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import splashImage from '../assets/splash/splash.png'
import { splashUrl } from '../api/client'

const props = defineProps({
  appearance: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['finished'])

const isLeaving = ref(false)
const lottieBox = ref(null)
let leaveTimer
let finishTimer
let animation

const mode = props.appearance?.splash_mode || 'default'
const durationMs = Math.max(2, Number(props.appearance?.splash_duration) || 2) * 1000
const file = props.appearance?.splash_file || ''
const loopVideo = props.appearance?.splash_loop !== false
const mediaSrc = file && mode !== 'default' ? splashUrl(file) : ''

function done() {
  if (isLeaving.value) {
    return
  }
  isLeaving.value = true
  finishTimer = window.setTimeout(() => {
    emit('finished')
  }, 520)
}

onMounted(async () => {
  leaveTimer = window.setTimeout(done, Math.max(800, durationMs - 420))
  if (mode === 'lottie' && mediaSrc && lottieBox.value) {
    try {
      const payload = await fetch(mediaSrc).then((response) => response.json())
      await nextTick()
      if (lottieBox.value) {
        animation = lottie.loadAnimation({
          container: lottieBox.value,
          renderer: 'svg',
          loop: true,
          autoplay: true,
          animationData: payload,
        })
      }
    } catch (error) {
      console.error('Failed to play splash lottie:', error)
    }
  }
})

onBeforeUnmount(() => {
  window.clearTimeout(leaveTimer)
  window.clearTimeout(finishTimer)
  if (animation) {
    animation.destroy()
    animation = null
  }
})

function onFadeEnd(event) {
  if (event.propertyName !== 'opacity' || !isLeaving.value) {
    return
  }
  emit('finished')
}
</script>

<template>
  <div
    class="wv-splash fixed inset-0 z-[100] grid place-items-center bg-[#121816] transition-opacity duration-500"
    :class="{ 'opacity-0': isLeaving, 'opacity-100': !isLeaving }"
    @transitionend="onFadeEnd"
  >
    <div class="flex flex-col items-center gap-7">
      <video
        v-if="mode === 'video' && mediaSrc"
        :src="mediaSrc"
        class="max-h-[70vh] max-w-[80vw] rounded-md object-contain"
        autoplay
        muted
        playsinline
        :loop="loopVideo"
      />
      <div v-else-if="mode === 'lottie' && mediaSrc" ref="lottieBox" class="h-52 w-52" />
      <img
        v-else-if="mode === 'image' && mediaSrc"
        :src="mediaSrc"
        alt="Weaveverse OS"
        class="max-h-[70vh] max-w-[80vw] rounded-md object-contain shadow-glow"
      />
      <img
        v-else
        :src="splashImage"
        alt="Weaveverse OS"
        class="h-40 w-40 rounded-full object-cover shadow-glow"
      />
      <div class="text-center">
        <p class="text-sm uppercase tracking-[0.32em] text-[#e2d9c8]">Weaveverse OS</p>
        <h1 class="mt-3 text-3xl font-semibold text-white">正在编织你的宇宙</h1>
      </div>
    </div>
  </div>
</template>
