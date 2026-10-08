<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: '',
  },
  message: {
    type: String,
    default: '',
  },
  confirmLabel: {
    type: String,
    default: '删除',
  },
  busy: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['cancel', 'confirm'])

const canConfirm = computed(() => props.open && !props.busy)

function onKeydown(event) {
  if (!props.open || event.key !== 'Escape') {
    return
  }
  emit('cancel')
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      window.addEventListener('keydown', onKeydown)
      return
    }
    window.removeEventListener('keydown', onKeydown)
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 grid place-items-center bg-black/45 px-4">
    <div class="w-full max-w-md rounded-md bg-[#fcfaf5] p-6 shadow-2xl">
      <h2 class="text-xl font-semibold text-ink">{{ title }}</h2>
      <p class="mt-3 text-sm leading-6 text-ink/75">{{ message }}</p>
      <div class="mt-6 flex justify-end gap-3">
        <button type="button" class="h-10 rounded-md px-4 text-sm text-ink/70 hover:bg-black/5" :disabled="busy" @click="emit('cancel')">
          取消
        </button>
        <button
          type="button"
          class="h-10 rounded-md bg-ember px-4 text-sm font-semibold text-white disabled:opacity-60"
          :disabled="!canConfirm"
          @click="emit('confirm')"
        >
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>
