<script setup>
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'

import { showMenu } from '../contextMenu'
import NavIcon from './NavIcon.vue'

const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  groups: {
    type: Array,
    default: () => [],
  },
  groupId: {
    type: Number,
    default: null,
  },
  groupName: {
    type: String,
    default: '',
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

const emit = defineEmits(['select', 'create', 'edit', 'delete', 'reorder', 'pin', 'lock', 'move', 'open-overview', 'search', 'note', 'appearance'])

const localItems = ref([])

watch(
  () => props.items,
  (items) => {
    localItems.value = [...items]
  },
  { immediate: true },
)

function onDragEnd() {
  const ids = localItems.value.map((item) => item.id)
  const previous = props.items.map((item) => item.id)
  if (ids.length === previous.length && ids.every((id, index) => id === previous[index])) {
    return
  }
  emit('reorder', ids)
}

function onItemMenu(event, item) {
  const others = props.groups.filter((group) => group.id !== props.groupId)
  showMenu(event, [
    {
      label: item.pinned ? '取消置顶' : '置顶',
      onClick: () => emit('pin', item),
    },
    {
      label: '移动到...',
      disabled: others.length === 0,
      children: others.map((group) => ({
        label: group.name,
        onClick: () => emit('move', item, group.id),
      })),
    },
    {
      label: item.locked ? '解锁' : '锁定',
      onClick: () => emit('lock', item),
    },
    { label: '编辑', onClick: () => emit('edit', item) },
    {
      label: '删除',
      disabled: Boolean(item.locked),
      onClick: () => {
        if (!item.locked) {
          emit('delete', item)
        }
      },
    },
  ])
}
</script>

<template>
  <aside class="wv-nav flex h-screen w-[240px] shrink-0 flex-col border-r border-black/10 px-4 py-6">
    <div class="mb-6">
      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-moss">Weaveverse</p>
      <button type="button" class="mt-2 block w-full truncate text-left text-xl font-semibold text-ink" @click="emit('open-overview')">
        {{ groupName || '导航' }}
      </button>
    </div>

    <div v-if="loading" class="rounded-md border border-black/10 bg-white/65 px-4 py-3 text-sm text-ink/70">
      正在加载导航...
    </div>

    <div v-else-if="errorMessage" class="rounded-md border border-ember/30 bg-ember/10 px-4 py-3 text-sm text-ink">
      {{ errorMessage }}
    </div>

    <draggable
      v-else
      v-model="localItems"
      item-key="id"
      tag="div"
      class="min-h-0 flex-1 space-y-2 overflow-y-auto"
      handle=".nav-handle"
      filter=".nav-action"
      :prevent-on-filter="false"
      :animation="200"
      @end="onDragEnd"
    >
      <template #item="{ element }">
        <div
          class="group flex h-12 w-full items-center gap-2 rounded-md px-2 text-sm font-medium"
          :class="
            element.id === activeId
              ? 'bg-moss text-white shadow-sm'
              : 'text-ink/72 hover:bg-white/70 hover:text-ink'
          "
          @contextmenu="onItemMenu($event, element)"
        >
          <button type="button" class="flex min-w-0 flex-1 items-center gap-3 text-left" @click="emit('select', element.id)">
            <NavIcon :icon="element.icon" />
            <span class="truncate">{{ element.title }}</span>
          </button>
          <div class="flex shrink-0 items-center gap-1 pr-1 text-sm">
            <span v-if="element.locked" title="已锁定">🔒</span>
            <span v-if="element.pinned" title="已置顶">📌</span>
            <button type="button" class="nav-handle cursor-grab px-0.5 opacity-0 group-hover:opacity-70 active:cursor-grabbing" title="拖动排序">⋮⋮</button>
          </div>
        </div>
      </template>
    </draggable>

    <div class="mt-auto border-t border-black/10 pt-5">
      <div class="mb-3 grid grid-cols-3 gap-2">
        <button type="button" class="h-9 rounded-md bg-white text-xs font-medium text-ink shadow-sm" title="搜索 Ctrl+K" @click="emit('search')">
          搜索
        </button>
        <button type="button" class="h-9 rounded-md bg-white text-xs font-medium text-ink shadow-sm" title="速记 Ctrl+Shift+N" @click="emit('note')">
          速记
        </button>
        <button type="button" class="h-9 rounded-md bg-white text-xs font-medium text-ink shadow-sm" title="设置" @click="emit('appearance')">
          设置
        </button>
      </div>
      <button
        type="button"
        class="mb-5 flex h-11 w-full items-center justify-center gap-2 rounded-md bg-ink text-sm font-semibold text-white transition hover:bg-moss"
        @click="emit('create')"
      >
        <span class="text-lg">+</span>
        <span>添加</span>
      </button>
      <div class="text-xs leading-5 text-ink/55">右键可锁定、置顶、移动或删除</div>
    </div>
  </aside>
</template>
