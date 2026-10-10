<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: {
    type: String,
    default: '',
  },
  box: {
    type: String,
    default: 'h-8 w-8 bg-white/20 text-base',
  },
  rounded: {
    type: String,
    default: 'rounded-md',
  },
})

const fileId = computed(() => {
  const match = /^@file:([0-9a-f]{12})$/.exec(props.icon || '')
  return match ? match[1] : ''
})
</script>

<template>
  <span class="grid shrink-0 place-items-center overflow-hidden" :class="[rounded, box]">
    <img v-if="fileId" :src="`/api/icons/${fileId}.png`" alt="" class="h-full w-full object-cover" />
    <span v-else class="block max-w-full truncate px-0.5 text-center leading-none">{{ icon || '·' }}</span>
  </span>
</template>
