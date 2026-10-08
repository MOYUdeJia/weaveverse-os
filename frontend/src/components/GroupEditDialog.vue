<script setup>
import { computed, ref, watch } from 'vue'

import IconField from './IconField.vue'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  group: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'save'])

const name = ref('')
const icon = ref('📁')
const description = ref('')
const iconField = ref(null)

const isSystem = computed(() => Boolean(props.group?.is_system))
const dialogTitle = computed(() => {
  if (!props.group) {
    return '新建分组'
  }
  return isSystem.value ? '编辑系统分组' : '编辑分组'
})
const canSave = computed(() => name.value.trim().length > 0 && icon.value.trim().length > 0)

watch(
  () => [props.open, props.group],
  () => {
    if (!props.open) {
      return
    }
    name.value = props.group?.name || ''
    icon.value = props.group?.icon || '📁'
    description.value = props.group?.description || ''
  },
)

function save() {
  if (!canSave.value) {
    return
  }
  emit(
    'save',
    {
      name: name.value.trim(),
      icon: icon.value.trim(),
      description: description.value.trim(),
    },
    (ok) => {
      if (ok) {
        iconField.value?.saved()
      }
    },
  )
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-black/45 px-4">
    <form class="w-full max-w-lg rounded-md bg-[#fcfaf5] p-6 shadow-2xl" @submit.prevent="save">
      <div class="mb-6 flex items-center justify-between gap-4">
        <h2 class="text-xl font-semibold text-ink">{{ dialogTitle }}</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-md text-ink/60 hover:bg-black/5" @click="emit('close')">
          ×
        </button>
      </div>
      <p v-if="isSystem" class="mb-4 text-sm text-ink/60">系统分组不能改名，也不能删除。这里只能改图标和简介。</p>

      <label class="block text-sm font-medium text-ink/75" for="group-name">分组名</label>
      <input
        id="group-name"
        v-model="name"
        class="mt-2 h-11 w-full rounded-md border border-black/15 bg-white px-3 text-base outline-none focus:border-moss disabled:bg-black/5 disabled:text-ink/50"
        maxlength="50"
        autocomplete="off"
        :disabled="isSystem"
      />

      <label class="mt-5 block text-sm font-medium text-ink/75" for="group-icon">图标</label>
      <IconField ref="iconField" v-model="icon" />

      <label class="mt-5 block text-sm font-medium text-ink/75" for="group-description">简介</label>
      <textarea
        id="group-description"
        v-model="description"
        class="mt-2 h-24 w-full resize-none rounded-md border border-black/15 bg-white px-3 py-2 text-sm outline-none focus:border-moss"
        maxlength="2000"
      />

      <div class="mt-7 flex justify-end gap-3">
        <button type="button" class="h-10 rounded-md px-4 text-sm text-ink/70 hover:bg-black/5" @click="emit('close')">取消</button>
        <button
          type="submit"
          class="h-10 rounded-md px-5 text-sm font-semibold text-white"
          :class="canSave ? 'bg-moss hover:bg-ink' : 'cursor-not-allowed bg-ink/30'"
          :disabled="!canSave"
        >
          确定
        </button>
      </div>
    </form>
  </div>
</template>
