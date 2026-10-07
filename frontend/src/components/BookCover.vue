<script setup>
import { ref } from 'vue'

import { bookCoverUrl } from '../api/client'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
})

const failed = ref(false)

function placeholderClass(bookFormat) {
  if (bookFormat === 'txt') {
    return 'bg-gradient-to-br from-ember to-ink'
  }
  if (bookFormat === 'pdf') {
    return 'bg-gradient-to-br from-aurora to-ink'
  }
  return 'bg-gradient-to-br from-moss to-aurora'
}
</script>

<template>
  <div v-if="book.has_cover && !failed" class="h-44 overflow-hidden rounded-md bg-dawn">
    <img :src="bookCoverUrl(book.id)" alt="" class="h-full w-full object-cover" @error="failed = true" />
  </div>
  <div v-else class="grid h-44 place-items-center rounded-md text-white" :class="placeholderClass(book.format)">
    <div class="text-center">
      <p class="text-3xl font-semibold">{{ (book.title || '书').slice(0, 1) }}</p>
      <p class="mt-2 text-xs tracking-[0.2em]">{{ book.format.toUpperCase() }}</p>
    </div>
  </div>
</template>
