<script setup>
import { ref, watch } from 'vue'

import NavIcon from './NavIcon.vue'

const props = defineProps({
  group: {
    type: Object,
    required: true,
  },
  items: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['open', 'rename', 'describe'])

const nameDraft = ref('')
const descriptionDraft = ref('')

watch(
  () => [props.group.id, props.group.name, props.group.description],
  () => {
    nameDraft.value = props.group.name
    descriptionDraft.value = props.group.description || ''
  },
  { immediate: true },
)

function commitName() {
  const next = nameDraft.value.trim()
  if (props.group.is_system || !next || next === props.group.name) {
    nameDraft.value = props.group.name
    return
  }
  emit('rename', next, (ok) => {
    if (!ok) {
      nameDraft.value = props.group.name
    }
  })
}

function commitDescription() {
  const next = descriptionDraft.value.trim()
  if (next === (props.group.description || '')) {
    descriptionDraft.value = props.group.description || ''
    return
  }
  emit('describe', next, (ok) => {
    if (!ok) {
      descriptionDraft.value = props.group.description || ''
    }
  })
}
</script>

<template>
  <div class="mx-auto w-full max-w-3xl">
    <p class="text-sm font-semibold uppercase tracking-[0.28em] text-aurora">分组导览</p>
    <div class="mt-5 flex items-center gap-4">
      <NavIcon :icon="group.icon" box="h-16 w-16 bg-dawn text-2xl shadow-sm" />
      <div class="min-w-0 flex-1">
        <input
          v-if="!group.is_system"
          v-model="nameDraft"
          class="w-full bg-transparent text-4xl font-semibold text-ink outline-none"
          maxlength="50"
          @blur="commitName"
          @keydown.enter.prevent="$event.target.blur()"
        />
        <h2 v-else class="text-4xl font-semibold text-ink">{{ group.name }}</h2>
        <p class="mt-1 text-sm text-ink/50">{{ items.length }} 个导航项</p>
      </div>
    </div>

    <label class="mt-8 block text-sm font-medium text-ink/70" for="group-overview-description">简介</label>
    <textarea
      id="group-overview-description"
      v-model="descriptionDraft"
      class="mt-2 h-28 w-full resize-none rounded-md border border-black/10 bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-moss"
      maxlength="2000"
      placeholder="写一点这个分组是做什么的"
      @blur="commitDescription"
    />

    <div class="mt-8">
      <h3 class="text-sm font-semibold text-ink/70">导航项</h3>
      <p v-if="items.length === 0" class="mt-3 text-sm text-ink/50">这个分组还没有导航项。</p>
      <div v-else class="mt-3 grid gap-2">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="flex h-12 items-center gap-3 rounded-md bg-white px-3 text-left shadow-sm hover:bg-moss hover:text-white"
          @click="emit('open', item.id)"
        >
          <NavIcon :icon="item.icon" />
          <span class="min-w-0 flex-1 truncate text-sm font-medium">{{ item.title }}</span>
          <span v-if="item.pinned" class="text-xs opacity-70">置顶</span>
        </button>
      </div>
    </div>
  </div>
</template>
