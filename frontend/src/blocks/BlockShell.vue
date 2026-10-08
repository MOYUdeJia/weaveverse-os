<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  blockId: {
    type: Number,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['delete'])
const collapsed = ref(false)

function storageKey(id) {
  return `wv.block.collapsed.${id}`
}

watch(
  () => props.blockId,
  (id) => {
    try {
      collapsed.value = localStorage.getItem(storageKey(id)) === '1'
    } catch {
      collapsed.value = false
    }
  },
  { immediate: true },
)

// 点标题栏折叠，并把状态留在本机。
// Collapse from the title bar and remember it on this machine.
function toggle() {
  collapsed.value = !collapsed.value
  try {
    localStorage.setItem(storageKey(props.blockId), collapsed.value ? '1' : '0')
  } catch {
    // 写不了本地存储时，折叠只在这一次查看里生效。
  }
}
</script>

<template>
  <article class="rounded-md border border-black/10 bg-white/80 px-3 py-2 shadow-sm">
    <div class="flex items-center gap-1">
      <button type="button" class="flex min-w-0 flex-1 items-center gap-1.5 py-0.5 text-left" @click="toggle">
        <span class="w-3 text-[10px] leading-none text-ink/40">{{ collapsed ? '▸' : '▾' }}</span>
        <span class="truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-moss">{{ title }}</span>
      </button>
      <slot name="actions" />
      <button type="button" class="grid h-6 w-6 place-items-center rounded text-xs hover:bg-black/5" title="删除" @click="emit('delete')">
        🗑️
      </button>
    </div>
    <div v-show="!collapsed" class="mt-1.5">
      <slot />
    </div>
  </article>
</template>
