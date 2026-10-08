<script setup>
// 进度追踪区块：用 CSS 宽度画进度条，编辑后立刻保存。
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
const draft = ref({ label: '', current: 0, total: 100, unit: '%' })

watch(
  () => props.block,
  () => {
    items.value = (props.block.content?.items || []).map((item) => ({
      label: item.label || '',
      current: Number(item.current) || 0,
      total: Number(item.total) || 0,
      unit: item.unit ?? '%',
    }))
  },
  { immediate: true, deep: true },
)

function percent(item) {
  const total = Number(item.total)
  const current = Number(item.current)
  if (!Number.isFinite(total) || total <= 0 || !Number.isFinite(current)) {
    return 0
  }
  return Math.min(100, Math.max(0, (current / total) * 100))
}

function persist(nextItems) {
  items.value = nextItems
  emit('save', {
    items: nextItems.map(({ label, current, total, unit }) => ({
      label,
      current: Number(current),
      total: Number(total),
      unit,
    })),
  })
}

function updateItem(index, patch) {
  persist(items.value.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)))
}

function addItem() {
  const label = draft.value.label.trim()
  if (!label) {
    return
  }
  persist([
    ...items.value,
    {
      label,
      current: Number(draft.value.current) || 0,
      total: Number(draft.value.total) || 0,
      unit: draft.value.unit.trim() || '%',
    },
  ])
  draft.value = { label: '', current: 0, total: 100, unit: '%' }
}

function removeItem(index) {
  persist(items.value.filter((_, itemIndex) => itemIndex !== index))
}

function confirmDelete() {
  if (window.confirm('确定删除这个进度区块吗？')) {
    emit('delete')
  }
}
</script>

<template>
  <BlockShell title="进度" :block-id="block.id" @delete="confirmDelete">

    <p v-if="items.length === 0" class="text-sm text-ink/50">还没有进度项</p>

    <ul v-else class="space-y-2">
      <li v-for="(item, index) in items" :key="index">
        <div class="mb-1 flex items-center justify-between gap-3 text-sm">
          <span class="truncate font-medium text-ink">{{ item.label }}</span>
          <span class="shrink-0 text-ink/60">{{ item.current }}/{{ item.total }} {{ item.unit }}</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-black/10">
          <div class="h-full rounded-full bg-moss" :style="{ width: `${percent(item)}%` }" />
        </div>
        <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-[1fr_5rem_5rem_4rem_auto]">
          <input
            :value="item.label"
            class="h-9 rounded-md border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss"
            @change="updateItem(index, { label: $event.target.value.trim() })"
          />
          <input
            :value="item.current"
            type="number"
            step="any"
            class="h-9 rounded-md border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss"
            @change="updateItem(index, { current: Number($event.target.value) })"
          />
          <input
            :value="item.total"
            type="number"
            step="any"
            class="h-9 rounded-md border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss"
            @change="updateItem(index, { total: Number($event.target.value) })"
          />
          <input
            :value="item.unit"
            class="h-9 rounded-md border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss"
            @change="updateItem(index, { unit: $event.target.value })"
          />
          <button type="button" class="h-9 text-xs text-ink/50 hover:text-ember" @click="removeItem(index)">删除</button>
        </div>
      </li>
    </ul>

    <form class="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-[1fr_5rem_5rem_4rem_auto]" @submit.prevent="addItem">
      <input v-model="draft.label" class="h-8 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss" placeholder="标签" />
      <input v-model.number="draft.current" type="number" step="any" class="h-8 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss" />
      <input v-model.number="draft.total" type="number" step="any" class="h-8 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss" />
      <input v-model="draft.unit" class="h-8 rounded-md border border-black/15 bg-white px-2 text-sm outline-none focus:border-moss" />
      <button type="submit" class="h-8 rounded-md bg-ink px-3 text-sm font-semibold text-white hover:bg-moss">+ 添加进度项</button>
    </form>
  </BlockShell>
</template>
