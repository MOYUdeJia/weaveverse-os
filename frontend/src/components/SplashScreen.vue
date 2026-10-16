<script setup>
import lottie from 'lottie-web'
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import splashImage from '../assets/splash/splash.png'
import { packFileUrl, splashUrl } from '../api/client'

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
let startupAudio

const mode = props.appearance?.splash_mode || 'default'
const durationMs = Math.max(2, Number(props.appearance?.splash_duration) || 2) * 1000
const file = props.appearance?.splash_file || ''
const loopVideo = props.appearance?.splash_loop !== false
const fromPack = props.appearance?.splash_owner === 'pack' && props.appearance?.active_pack
const mediaSrc = file && mode !== 'default'
  ? (fromPack ? packFileUrl(props.appearance.active_pack, file) : splashUrl(file))
  : ''
const caption = (fromPack && props.appearance?.pack_caption) || props.appearance?.splash_caption || '正在编织你的宇宙'

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
  const sound = props.appearance?.startup_sound
  if (fromPack && sound) {
    startupAudio = new Audio(packFileUrl(props.appearance.active_pack, sound))
    startupAudio.play().catch(() => {})
  }
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
  if (startupAudio) {
    startupAudio.pause()
    startupAudio = null
  }
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
    class="wv-splash fixed inset-0 z-[100] transition-opacity duration-500"
    :class="{ 'opacity-0': isLeaving, 'opacity-100': !isLeaving }"
    @transitionend="onFadeEnd"
  >
    <div class="wv-splash-stage">
      <video
        v-if="mode === 'video' && mediaSrc"
        :src="mediaSrc"
        class="wv-splash-media"
        autoplay
        muted
        playsinline
        :loop="loopVideo"
      />
      <div v-else-if="mode === 'lottie' && mediaSrc" ref="lottieBox" class="wv-splash-lottie" />
      <img
        v-else-if="mode === 'image' && mediaSrc"
        :src="mediaSrc"
        alt=""
        class="wv-splash-media"
      />
      <img
        v-else
        :src="splashImage"
        alt="Weaveverse OS"
        class="wv-splash-media wv-splash-mark"
      />
    </div>
    <footer class="wv-splash-caption">
      <p class="text-sm tracking-[0.18em] text-[#e2d9c8]">Weaveverse OS</p>
      <h1 class="mt-1 text-2xl font-semibold text-white">{{ caption }}</h1>
    </footer>
  </div>
</template>
