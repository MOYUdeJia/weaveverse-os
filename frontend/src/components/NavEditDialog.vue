<script setup>
// 添加导航：先选空白页或模板，再填标题和图标。编辑只改标题和图标。
import { computed, ref, watch } from 'vue'

import { getPageTypes, getTemplates } from '../api/client'
import { specialAdds } from '../specialAdds/registry'
import IconField from './IconField.vue'

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
  navItems: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'save'])

const step = ref('menu')
const title = ref('')
const icon = ref('')
const pageType = ref('markdown')
const pageTypes = ref([])
const templates = ref([])
const selectedTemplate = ref(null)
const loadError = ref('')
const iconField = ref(null)

const dialogTitle = computed(() => {
  if (props.mode === 'edit') {
    return '编辑导航项'
  }
  if (step.value === 'blank') {
    return '新建空白页'
  }
  if (step.value === 'templates' || step.value === 'template') {
    return '从模板创建'
  }
  return '添加导航项'
})
const canSave = computed(() => title.value.trim().length > 0 && icon.value.trim().length > 0)
const specialAddList = computed(() =>
  Object.entries(specialAdds).map(([id, spec]) => ({ id, ...spec })),
)
const creatableTypes = computed(() =>
  pageTypes.value.filter((type) => {
    if (type.multi_instance) {
      return true
    }
    if (type.type !== 'bookshelf') {
      return false
    }
    return !props.navItems.some((item) => item.page_type === 'bookshelf')
  }),
)

watch(
  () => [props.open, props.mode, props.item],
  async () => {
    if (!props.open) {
      return
    }

    title.value = props.item?.title ?? ''
    icon.value = props.item?.icon ?? ''
    pageType.value = props.item?.page_type ?? 'markdown'
    selectedTemplate.value = null
    loadError.value = ''
    step.value = props.mode === 'edit' ? 'edit' : 'menu'
  },
  { immediate: true },
)

function chooseSpecial(add) {
  if (typeof add.create === 'function') {
    add.create()
    return
  }
  loadError.value = '这个添加方式还没实现'
}

async function chooseBlank() {
  selectedTemplate.value = null
  loadError.value = ''
  step.value = 'blank'
  try {
    if (pageTypes.value.length === 0) {
      pageTypes.value = await getPageTypes()
    }
    pageType.value = creatableTypes.value[0]?.type ?? 'markdown'
  } catch (error) {
    console.error('Failed to load page types:', error)
    loadError.value = error.message || '无法加载页面类型'
  }
}

async function chooseTemplates() {
  loadError.value = ''
  step.value = 'templates'
  try {
    if (templates.value.length === 0) {
      templates.value = await getTemplates()
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
    loadError.value = error.message || '无法加载模板'
  }
}

function pickTemplate(template) {
  selectedTemplate.value = template
  title.value = template.label
  icon.value = template.icon
  step.value = 'template'
}

function goBack() {
  loadError.value = ''
  if (step.value === 'template') {
    step.value = 'templates'
    return
  }
  selectedTemplate.value = null
  step.value = 'menu'
}

function save() {
  if (!canSave.value) {
    return
  }

  const payload = {
    title: title.value.trim(),
    icon: icon.value.trim(),
  }
  if (step.value === 'template' && selectedTemplate.value) {
    payload.template_id = selectedTemplate.value.id
  } else if (props.mode === 'create') {
    payload.page_type = pageType.value
  }
  emit('save', payload, (ok) => {
    if (ok) {
      iconField.value?.saved()
    }
  })
}
</script>

<template>
  <teleport to="body">
    <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-black/45 px-4">
      <form class="w-full max-w-lg rounded-md bg-[#fcfaf5] p-6 shadow-2xl" @submit.prevent="save">
        <div class="mb-6 flex items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <button
              v-if="mode === 'create' && step !== 'menu'"
              type="button"
              class="grid h-9 w-9 place-items-center rounded-md text-ink/60 hover:bg-black/5"
              @click="goBack"
            >
              ←
            </button>
            <h2 class="text-xl font-semibold text-ink">{{ dialogTitle }}</h2>
          </div>
          <button type="button" class="grid h-9 w-9 place-items-center rounded-md text-ink/60 hover:bg-black/5" @click="emit('close')">
            ×
          </button>
        </div>

        <p v-if="loadError" class="mb-4 text-sm text-ember">{{ loadError }}</p>

        <div v-if="step === 'menu'" class="grid gap-3">
          <button type="button" class="rounded-md bg-white px-4 py-4 text-left shadow-sm hover:bg-moss hover:text-white" @click="chooseBlank">
            <span class="block text-base font-semibold">新建空白页</span>
            <span class="mt-1 block text-sm opacity-70">选择页面类型，从一块空白开始</span>
          </button>
          <button type="button" class="rounded-md bg-white px-4 py-4 text-left shadow-sm hover:bg-moss hover:text-white" @click="chooseTemplates">
            <span class="block text-base font-semibold">从模板创建</span>
            <span class="mt-1 block text-sm opacity-70">用一套搭好的区块开始</span>
          </button>
          <button
            v-for="add in specialAddList"
            :key="add.id"
            type="button"
            class="rounded-md bg-white px-4 py-4 text-left shadow-sm hover:bg-moss hover:text-white"
            @click="chooseSpecial(add)"
          >
            <span class="block text-base font-semibold">{{ add.icon }} {{ add.label }}</span>
          </button>
        </div>

        <div v-else-if="step === 'templates'" class="grid grid-cols-2 gap-3">
          <button
            v-for="template in templates"
            :key="template.id"
            type="button"
            class="rounded-md bg-white p-4 text-left shadow-sm hover:ring-2 hover:ring-moss"
            @click="pickTemplate(template)"
          >
            <span class="text-2xl">{{ template.icon }}</span>
            <span class="mt-2 block text-sm font-semibold text-ink">{{ template.label }}</span>
            <span class="mt-1 block text-xs leading-5 text-ink/60">{{ template.description }}</span>
          </button>
        </div>

        <template v-else>
          <label class="block text-sm font-medium text-ink/75" for="nav-title">标题</label>
          <input
            id="nav-title"
            v-model="title"
            class="mt-2 h-11 w-full rounded-md border border-black/15 bg-white px-3 text-base outline-none focus:border-moss"
            maxlength="50"
            autocomplete="off"
          />

          <label class="mt-5 block text-sm font-medium text-ink/75" for="nav-icon">图标</label>
          <IconField ref="iconField" v-model="icon" />

          <template v-if="step === 'blank'">
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
        </template>
      </form>
    </div>
  </teleport>
</template>
