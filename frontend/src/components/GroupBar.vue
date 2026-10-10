<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
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
  bar: {
    type: String,
    default: 'push',
  },
})

const emit = defineEmits(['select', 'create', 'edit', 'remove', 'reorder', 'lock'])

const narrow = ref(false)
const holding = ref(false)
const menuOpen = ref(false)
const localGroups = ref([])
let media = null
let onMediaChange = null

const floated = ref(null)
const systemGroup = computed(() => localGroups.value.find((group) => group.is_system) || null)

const asideClass = computed(() => {
  if (props.bar === 'stack') {
    return 'w-[4.75rem]'
  }
  if (props.bar === 'overlay' || narrow.value) {
    return 'w-12'
  }
  if (holding.value || menuOpen.value) {
    return 'w-[200px]'
  }
  return 'w-12 hover:w-[200px]'
})

function floatName(event, group) {
  if (props.bar !== 'overlay') {
    return
  }
  floated.value = {
    name: group.name,
    icon: group.icon,
    top: event.currentTarget.getBoundingClientRect().top,
  }
}

function clearFloat() {
  floated.value = null
}
const otherGroups = computed({
  get: () => localGroups.value.filter((group) => !group.is_system),
  set: (rows) => {
    localGroups.value = systemGroup.value ? [systemGroup.value, ...rows] : rows
  },
})

watch(
  () => props.groups,
  (groups) => {
    localGroups.value = [...groups]
  },
  { immediate: true },
)

function onGroupMenu(event, group) {
  const items = [
    {
      label: group.locked ? '解锁' : '锁定',
      onClick: () => emit('lock', group),
    },
  ]
  if (group.is_system) {
    items.push({ label: '编辑图标', onClick: () => emit('edit', group) })
  } else {
    items.push(
      { label: '编辑', onClick: () => emit('edit', group) },
      {
        label: '删除',
        disabled: Boolean(group.locked),
        onClick: () => {
          if (!group.locked) {
            emit('remove', group)
          }
        },
      },
    )
  }
  menuOpen.value = true
  showMenu(event, items)
  window.setTimeout(() => {
    window.addEventListener('click', closeGroupMenu, true)
    window.addEventListener('keydown', closeGroupMenuOnEscape, true)
  }, 0)
}

function closeGroupMenu() {
  menuOpen.value = false
  window.removeEventListener('click', closeGroupMenu, true)
  window.removeEventListener('keydown', closeGroupMenuOnEscape, true)
}

function closeGroupMenuOnEscape(event) {
  if (event.key === 'Escape') {
    closeGroupMenu()
  }
}

function onDragEnd() {
  holding.value = false
  const ids = [systemGroup.value?.id, ...localGroups.value.filter((group) => !group.is_system).map((group) => group.id)].filter((id) => id != null)
  const previous = props.groups.map((group) => group.id)
  if (ids.length === previous.length && ids.every((id, index) => id === previous[index])) {
    return
  }
  emit('reorder', ids)
}

onMounted(() => {
  media = window.matchMedia('(max-width: 899px)')
  onMediaChange = () => {
    narrow.value = media.matches
  }
  onMediaChange()
  media.addEventListener('change', onMediaChange)
})

onUnmounted(() => {
  closeGroupMenu()
  if (media && onMediaChange) {
    media.removeEventListener('change', onMediaChange)
  }
})
</script>

<template>
  <!-- 默认 48px，悬停展开到 200px。窄于 900px 时不再展开。 -->
  <aside
    class="wv-group group/folders relative z-[1] flex h-screen w-12 shrink-0 flex-col overflow-hidden border-r border-black/10 transition-[width] duration-300 ease-out"
    :class="asideClass"
  >
    <button
      v-if="systemGroup"
      type="button"
      class="flex w-full items-center text-left hover:bg-black/5"
      :class="bar === 'stack' ? 'h-auto flex-col gap-1 py-2' : 'h-12'"
      :title="systemGroup.name"
      @click="emit('select', systemGroup.id)"
      @contextmenu="onGroupMenu($event, systemGroup)"
      @mouseenter="floatName($event, systemGroup)"
      @mouseleave="clearFloat"
    >
      <span class="relative grid h-12 w-12 shrink-0 place-items-center">
        <NavIcon
          :icon="systemGroup.icon"
          rounded="rounded-full"
          :box="systemGroup.id === activeId ? 'h-8 w-8 bg-moss text-base text-white' : 'h-8 w-8 bg-transparent text-base text-ink'"
        />
      </span>
      <span
        class="min-w-0 flex-1 truncate whitespace-nowrap pr-3 text-sm font-medium"
        :class="bar === 'overlay' ? 'hidden' : bar === 'stack' ? 'w-full truncate px-1 text-center text-[10px] text-ink/70' : narrow ? 'opacity-0' : menuOpen ? 'opacity-100' : 'opacity-0 group-hover/folders:opacity-100'"
      >
        {{ systemGroup.name }}
      </span>
    </button>
    <draggable
      v-model="otherGroups"
      item-key="id"
      tag="div"
      class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden py-3"
      :animation="200"
      @start="holding = true"
      @end="onDragEnd"
    >
      <template #item="{ element }">
        <div
          class="flex w-full cursor-grab items-center text-left hover:bg-black/5 active:cursor-grabbing"
          :class="bar === 'stack' ? 'h-auto flex-col gap-1 py-2' : 'h-12'"
          :title="element.name"
          @click="emit('select', element.id)"
          @contextmenu="onGroupMenu($event, element)"
          @mouseenter="floatName($event, element)"
          @mouseleave="clearFloat"
        >
          <span class="relative grid h-12 w-12 shrink-0 place-items-center">
            <NavIcon
              :icon="element.icon"
              rounded="rounded-full"
              :box="
                element.id === activeId
                  ? 'h-8 w-8 bg-moss text-base text-white'
                  : 'h-8 w-8 bg-transparent text-base text-ink'
              "
            />
            <span v-if="element.locked" class="absolute bottom-0.5 right-0.5 text-[11px] leading-none" title="已锁定">🔒</span>
          </span>
          <span
            class="min-w-0 flex-1 truncate whitespace-nowrap pr-3 text-sm font-medium transition-opacity duration-300"
            :class="[
              bar === 'overlay' ? 'hidden' : bar === 'stack' ? 'w-full truncate px-1 text-center text-[10px]' : narrow ? 'opacity-0' : menuOpen ? 'opacity-100' : 'opacity-0 group-hover/folders:opacity-100',
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
          :class="bar === 'overlay' || bar === 'stack' ? 'hidden' : narrow ? 'opacity-0' : menuOpen ? 'opacity-100' : 'opacity-0 group-hover/folders:opacity-100'"
        >
          新建分组
        </span>
      </button>
    </div>
  </aside>
  <Teleport to="body">
    <Transition name="wv-float">
      <div
        v-if="bar === 'overlay' && floated"
        class="wv-float-name"
        :style="{ top: `${floated.top + 8}px`, left: '8px' }"
      >
        <NavIcon :icon="floated.icon" rounded="rounded-full" box="h-6 w-6 bg-transparent text-sm" />
        <span class="wv-float-label truncate">{{ floated.name }}</span>
      </div>
    </Transition>
  </Teleport>
</template>
