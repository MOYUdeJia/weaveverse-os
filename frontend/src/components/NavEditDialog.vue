<script setup>
import { computed, ref, watch } from 'vue'

import { getPageTypes } from '../api/client'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String,
    default: 'create',
  },
  item: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'save'])

const title = ref('')
const icon = ref('')
const pageType = ref('markdown')
const pageTypes = ref([])

const dialogTitle = computed(() => (props.mode === 'edit' ? '编辑导航项' : '添加导航项'))
const canSave = computed(() => title.value.trim().length > 0 && icon.value.trim().length > 0)
const creatableTypes = computed(() => pageTypes.value.filter((item) => item.multi_instance))

watch(
  () => [props.open, props.item],
  async () => {
    if (!props.open) {
      return
    }

    title.value = props.item?.title ?? ''
    icon.value = props.item?.icon ?? ''
    pageType.value = props.item?.page_type ?? 'markdown'

    if (props.mode === 'create') {
      try {
        if (pageTypes.value.length === 0) {
          pageTypes.value = await getPageTypes()
        }
        pageType.value = creatableTypes.value[0]?.type ?? 'markdown'
      } catch (error) {
        console.error('Failed to load page types:', error)
      }
    }
  },
  { immediate: true },
)

function save() {
  if (!canSave.value) {
    return
  }

  const payload = {
    title: title.value.trim(),
    icon: icon.value.trim(),
  }
  if (props.mode === 'create') {
    payload.page_type = pageType.value
  }
  emit('save', payload)
}
</script>

<template>
  <teleport to="body">
    <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-black/45 px-4">
      <form class="w-full max-w-md rounded-md bg-[#fcfaf5] p-6 shadow-2xl" @submit.prevent="save">
        <div class="mb-6 flex items-center justify-between gap-4">
          <h2 class="text-xl font-semibold text-ink">{{ dialogTitle }}</h2>
          <button type="button" class="grid h-9 w-9 place-items-center rounded-md text-ink/60 hover:bg-black/5" @click="emit('close')">
            ×
          </button>
        </div>

        <label class="block text-sm font-medium text-ink/75" for="nav-title">标题</label>
        <input
          id="nav-title"
          v-model="title"
          class="mt-2 h-11 w-full rounded-md border border-black/15 bg-white px-3 text-base outline-none focus:border-moss"
          maxlength="50"
          autocomplete="off"
        />

        <label class="mt-5 block text-sm font-medium text-ink/75" for="nav-icon">图标</label>
        <input
          id="nav-icon"
          v-model="icon"
          class="mt-2 h-11 w-full rounded-md border border-black/15 bg-white px-3 text-xl outline-none focus:border-moss"
          maxlength="20"
          autocomplete="off"
        />

        <template v-if="mode === 'create'">
          <label class="mt-5 block text-sm font-medium text-ink/75" for="nav-page-type">页面类型</label>
          <select
            id="nav-page-type"
            v-model="pageType"
            class="mt-2 h-11 w-full rounded-md border border-black/15 bg-white px-3 text-base outline-none focus:border-moss"
          >
            <option v-for="option in creatableTypes" :key="option.type" :value="option.type">
              {{ option.label }}
            </option>
          </select>
        </template>

        <div class="mt-7 flex justify-end gap-3">
          <button type="button" class="h-10 rounded-md px-4 text-sm font-medium text-ink/70 hover:bg-black/5" @click="emit('close')">
            取消
          </button>
          <button
            type="submit"
            class="h-10 rounded-md px-5 text-sm font-semibold text-white transition"
            :class="canSave ? 'bg-moss hover:bg-ink' : 'cursor-not-allowed bg-ink/30'"
            :disabled="!canSave"
          >
            确定
          </button>
        </div>
      </form>
    </div>
  </teleport>
</template>
