<script setup>
const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  activeId: {
    type: Number,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  errorMessage: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select', 'create', 'edit', 'delete', 'reorder'])

// 开始拖拽时写入被拖项的 id。
// Store the dragged item id when a drag starts.
function onDragStart(item, event) {
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(item.id))
}

// 允许在其他导航项上释放。
// Allow dropping onto another navigation item.
function onDragOver(event) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

// 把拖动项插到目标项前面，然后通知父组件保存顺序。
// Insert the dragged item before the drop target, then persist the new order.
function onDrop(target, event) {
  event.preventDefault()
  const sourceId = Number(event.dataTransfer.getData('text/plain'))
  if (!sourceId || sourceId === target.id) {
    return
  }

  const ids = props.items.map((item) => item.id)
  const from = ids.indexOf(sourceId)
  const to = ids.indexOf(target.id)
  if (from < 0 || to < 0) {
    return
  }

  ids.splice(from, 1)
  ids.splice(to, 0, sourceId)
  emit('reorder', ids)
}
</script>

<template>
  <aside class="flex w-72 shrink-0 flex-col border-r border-black/10 bg-[#f8f5ee]/88 px-5 py-6">
    <div class="mb-8">
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-moss">Weaveverse</p>
      <h1 class="mt-2 text-2xl font-semibold text-ink">个人宇宙</h1>
    </div>

    <div v-if="loading" class="rounded-md border border-black/10 bg-white/65 px-4 py-3 text-sm text-ink/70">
      正在加载导航...
    </div>

    <div v-else-if="errorMessage" class="rounded-md border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ink">
      {{ errorMessage }}
    </div>

    <nav v-else class="space-y-2">
      <div
        v-for="item in items"
        :key="item.id"
        draggable="true"
        class="group flex h-12 w-full cursor-grab items-center gap-2 rounded-md px-3 text-sm font-medium transition active:cursor-grabbing"
        :class="
          item.id === activeId
            ? 'bg-moss text-white shadow-sm'
            : 'text-ink/72 hover:bg-white/70 hover:text-ink'
        "
        @dragstart="onDragStart(item, $event)"
        @dragover="onDragOver"
        @drop="onDrop(item, $event)"
      >
        <button type="button" class="flex min-w-0 flex-1 items-center gap-3 text-left" @click="$emit('select', item.id)">
          <span class="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-white/20 text-lg">{{ item.icon }}</span>
          <span class="truncate">{{ item.title }}</span>
        </button>
        <div class="flex shrink-0 gap-1 opacity-0 transition group-hover:opacity-100">
          <button
            type="button"
            class="grid h-8 w-8 place-items-center rounded-md hover:bg-white/25"
            title="编辑"
            @click.stop="$emit('edit', item)"
          >
            ✏️
          </button>
          <button
            type="button"
            class="grid h-8 w-8 place-items-center rounded-md hover:bg-white/25"
            title="删除"
            @click.stop="$emit('delete', item)"
          >
            🗑️
          </button>
        </div>
      </div>
    </nav>

    <div class="mt-auto border-t border-black/10 pt-5">
      <button
        type="button"
        class="mb-5 flex h-11 w-full items-center justify-center gap-2 rounded-md bg-ink text-sm font-semibold text-white transition hover:bg-moss"
        @click="$emit('create')"
      >
        <span class="text-lg">+</span>
        <span>添加</span>
      </button>
      <div class="text-xs leading-5 text-ink/55">
        M2 pages + blocks<br />
        拖拽可排序
      </div>
    </div>
  </aside>
</template>
