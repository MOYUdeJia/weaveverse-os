<script setup>
import { ref, watch } from 'vue'

import { openExternalLink } from '../openExternal.js'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'delete'])

const links = ref([])
const newTitle = ref('')
const newUrl = ref('')

watch(
  () => props.block,
  () => {
    links.value = (props.block.content?.links || []).map((item) => ({ ...item }))
  },
  { immediate: true, deep: true },
)

function persist(nextLinks) {
  links.value = nextLinks
  emit('save', { links: nextLinks })
}

function addLink() {
  const title = newTitle.value.trim()
  let url = newUrl.value.trim()
  if (!title || !url) {
    return
  }
  if (!/^https?:\/\//i.test(url)) {
    url = `https://${url}`
  }
  persist([...links.value, { title, url }])
  newTitle.value = ''
  newUrl.value = ''
}

function removeLink(index) {
  persist(links.value.filter((_, itemIndex) => itemIndex !== index))
}

function confirmDelete() {
  if (window.confirm('确定删除这个链接区块吗？')) {
    emit('delete')
  }
}
</script>

<template>
  <article class="rounded-md border border-black/10 bg-white/80 p-4 shadow-sm">
    <div class="mb-3 flex items-center justify-between gap-3">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-moss">链接</p>
      <button type="button" class="grid h-8 w-8 place-items-center rounded-md hover:bg-black/5" title="删除" @click="confirmDelete">
        🗑️
      </button>
    </div>

    <ul class="space-y-2">
      <li v-for="(item, index) in links" :key="`${item.url}-${index}`" class="flex items-center gap-2">
        <button type="button" class="flex-1 truncate text-left text-sm text-aurora underline" @click="openExternalLink(item.url)">
          {{ item.title }}
        </button>
        <span class="max-w-40 truncate text-xs text-ink/45">{{ item.url }}</span>
        <button type="button" class="text-xs text-ink/50 hover:text-ember" @click="removeLink(index)">删除</button>
      </li>
    </ul>

    <form class="mt-3 grid grid-cols-[1fr_1.4fr_auto] gap-2" @submit.prevent="addLink">
      <input v-model="newTitle" class="h-10 rounded-md border border-black/15 bg-white px-3 text-sm outline-none focus:border-moss" placeholder="标题" />
      <input v-model="newUrl" class="h-10 rounded-md border border-black/15 bg-white px-3 text-sm outline-none focus:border-moss" placeholder="https://" />
      <button type="submit" class="h-10 rounded-md bg-ink px-3 text-sm font-semibold text-white hover:bg-moss">添加</button>
    </form>
  </article>
</template>
