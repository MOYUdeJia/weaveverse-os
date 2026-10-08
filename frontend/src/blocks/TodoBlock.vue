<script setup>
import { ref, watch } from 'vue'

import BlockShell from './BlockShell.vue'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'delete'])

const items = ref([])
const newText = ref('')

watch(
  () => props.block,
  () => {
    items.value = (props.block.content?.items || []).map((item) => ({ ...item }))
  },
  { immediate: true, deep: true },
)

// 立刻把待办列表写回后端。
// Persist the todo list immediately.
function persist(nextItems) {
  items.value = nextItems
  emit('save', { items: nextItems })
}

function toggle(index) {
  const next = items.value.map((item, itemIndex) =>
    itemIndex === index ? { ...item, done: !item.done } : item,
  )
  persist(next)
}

function updateText(index, text) {
  const next = items.value.map((item, itemIndex) => (itemIndex === index ? { ...item, text } : item))
  persist(next)
}

function addItem() {
  const text = newText.value.trim()
  if (!text) {
    return
  }
  persist([...items.value, { text, done: false }])
  newText.value = ''
}

function removeItem(index) {
  persist(items.value.filter((_, itemIndex) => itemIndex !== index))
}

function confirmDelete() {
  if (window.confirm('确定删除这个待办区块吗？')) {
    emit('delete')
  }
}
</script>

<template>
  <BlockShell title="待办" :block-id="block.id" @delete="confirmDelete">

    <ul class="space-y-2">
      <li v-for="(item, index) in items" :key="`${index}-${item.text}`" class="flex items-center gap-2">
        <input type="checkbox" :checked="item.done" @change="toggle(index)" />
        <input
          :value="item.text"
          class="h-8 flex-1 rounded-md border border-transparent bg-transparent px-2 text-sm outline-none focus:border-moss"
          :class="item.done ? 'text-ink/40 line-through' : 'text-ink'"
          @change="updateText(index, $event.target.value)"
        />
        <button type="button" class="text-xs text-ink/50 hover:text-ember" @click="removeItem(index)">删除</button>
      </li>
    </ul>

    <form class="mt-2 flex gap-2" @submit.prevent="addItem">
      <input
        v-model="newText"
        class="h-8 flex-1 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss"
        placeholder="添加待办"
      />
      <button type="submit" class="h-8 rounded-md bg-ink px-3 text-sm font-semibold text-white hover:bg-moss">+</button>
    </form>
  </BlockShell>
</template>
