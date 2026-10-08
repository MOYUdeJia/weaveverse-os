<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import draggable from 'vuedraggable'

import { showMenu } from '../contextMenu'
import NavIcon from './NavIcon.vue'

const props = defineProps({
  groups: {
    type: Array,
    required: true,
  },
  activeId: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['select', 'create', 'edit', 'remove', 'reorder'])

const locked = ref(false)
const holding = ref(false)
const localGroups = ref([])
let media = null
let onMediaChange = null

watch(
  () => props.groups,
  (groups) => {
    localGroups.value = [...groups]
  },
  { immediate: true },
)

function onGroupMenu(event, group) {
  const items = group.is_system
    ? [{ label: '编辑图标', onClick: () => emit('edit', group) }]
    : [
        { label: '编辑', onClick: () => emit('edit', group) },
        { label: '删除', onClick: () => emit('remove', group) },
      ]
  showMenu(event, items)
}

function onDragEnd() {
  holding.value = false
  const ids = localGroups.value.map((group) => group.id)
  const previous = props.groups.map((group) => group.id)
  if (ids.length === previous.length && ids.every((id, index) => id === previous[index])) {
    return
  }
  emit('reorder', ids)
}

onMounted(() => {
  media = window.matchMedia('(max-width: 899px)')
  onMediaChange = () => {
    locked.value = media.matches
  }
  onMediaChange()
  media.addEventListener('change', onMediaChange)
})

onUnmounted(() => {
  if (media && onMediaChange) {
    media.removeEventListener('change', onMediaChange)
  }
})
</script>

<template>
  <!-- 默认 48px，悬停展开到 200px。窄于 900px 时不再展开。 -->
  <aside
    class="group/folders flex h-screen w-12 shrink-0 flex-col overflow-hidden border-r border-black/10 bg-[#efeae1] transition-[width] duration-300 ease-out"
    :class="locked ? '' : holding ? 'w-[200px]' : 'hover:w-[200px]'"
  >
    <draggable
      v-model="localGroups"
      item-key="id"
      tag="div"
      class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden py-3"
      :animation="200"
      @start="holding = true"
      @end="onDragEnd"
    >
      <template #item="{ element }">
        <div
          class="flex h-12 w-full cursor-grab items-center text-left hover:bg-black/5 active:cursor-grabbing"
          :title="element.name"
          @click="emit('select', element.id)"
          @contextmenu="onGroupMenu($event, element)"
        >
          <span class="grid h-12 w-12 shrink-0 place-items-center">
            <NavIcon
              :icon="element.icon"
              :box="
                element.id === activeId
                  ? 'h-8 w-8 bg-moss text-base text-white'
                  : 'h-8 w-8 bg-white/80 text-base text-ink'
              "
            />
          </span>
          <span
            class="min-w-0 flex-1 truncate whitespace-nowrap pr-3 text-sm font-medium transition-opacity duration-300"
            :class="[
              locked ? 'opacity-0' : 'opacity-0 group-hover/folders:opacity-100',
              element.id === activeId ? 'text-ink' : 'text-ink/70',
            ]"
          >
            {{ element.name }}
          </span>
        </div>
      </template>
    </draggable>

    <div class="border-t border-black/10">
      <button type="button" class="flex h-12 w-full items-center text-left text-ink/80 hover:bg-black/5" title="新建分组" @click="emit('create')">
        <span class="grid h-12 w-12 shrink-0 place-items-center text-xl">+</span>
        <span
          class="truncate whitespace-nowrap text-sm font-medium transition-opacity duration-300"
          :class="locked ? 'opacity-0' : 'opacity-0 group-hover/folders:opacity-100'"
        >
          新建分组
        </span>
      </button>
    </div>
  </aside>
</template>
