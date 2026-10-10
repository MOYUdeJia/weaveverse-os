<script setup>
// 添加导航：先选积木页、模板或专用页，再填标题和图标。编辑只改标题和图标。
import { computed, ref, watch } from 'vue'

import { getNav, getPageTypes, getTemplates } from '../api/client'
import { focusAdds, specialAdds } from '../specialAdds/registry'
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
const selectedFocus = ref(null)
const pageTags = ref('')
const allNav = ref([])
const loadError = ref('')
const iconField = ref(null)

const dialogTitle = computed(() => {
  if (props.mode === 'edit') {
    return '编辑导航项'
  }
  if (step.value === 'flex' || step.value === 'blank' || step.value === 'template') {
    return '新建积木页'
  }
  if (step.value === 'focus' || step.value === 'focusForm') {
    return '新建专用页'
  }
  if (step.value === 'core' || step.value === 'coreForm') {
    return '新建系统页'
  }
  return '添加导航项'
})
const canSave = computed(() => {
  if (!title.value.trim()) {
    return false
  }
  if (step.value === 'focusForm' || step.value === 'coreForm') {
    return true
  }
  return icon.value.trim().length > 0
})
const focusList = computed(() => focusAdds())
const specialAddList = computed(() =>
  Object.entries(specialAdds)
    .filter(([, spec]) => spec.placement !== 'focus' && spec.placement !== 'hidden')
    .map(([id, spec]) => ({ id, ...spec })),
)
const coreTypes = computed(() => pageTypes.value.filter((type) => type.layer === 'core' && type.type !== 'group_overview'))
const createdSingles = computed(() => new Set(allNav.value.map((item) => item.page_type)))
const editingFocus = computed(() => props.mode === 'edit' && ['doc', 'plain', 'bookmarks', 'canvas', 'inbox'].includes(props.item?.page_type))
const creatableTypes = computed(() =>
  pageTypes.value.filter((type) => type.layer !== 'focus' && type.layer !== 'core' && type.multi_instance),
)

watch(
  () => [props.open, props.mode, props.item],
  async () => {
    if (!props.open) {
      return
    }

    title.value = props.item?.title ?? ''
    icon.value = props.item?.icon ?? ''
    pageTags.value = (props.item?.tags || []).map((tag) => `#${tag}`).join(' ')
    pageType.value = props.item?.page_type ?? 'markdown'
    selectedTemplate.value = null
    selectedFocus.value = null
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

async function chooseFlex() {
  selectedTemplate.value = null
  loadError.value = ''
  step.value = 'flex'
  try {
    if (pageTypes.value.length === 0) {
      pageTypes.value = await getPageTypes()
    }
    if (templates.value.length === 0) {
      templates.value = await getTemplates()
    }
  } catch (error) {
    loadError.value = error.message || '无法加载积木页'
  }
}

async function chooseCore() {
  loadError.value = ''
  step.value = 'core'
  try {
    if (pageTypes.value.length === 0) {
      pageTypes.value = await getPageTypes()
    }
    allNav.value = await getNav()
  } catch (error) {
    loadError.value = error.message || '无法加载系统页'
  }
}

function pickCore(type) {
  if (createdSingles.value.has(type.type)) {
    return
  }
  selectedTemplate.value = null
  selectedFocus.value = null
  pageType.value = type.type
  icon.value = type.default_icon || ''
  step.value = 'coreForm'
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
  selectedFocus.value = null
  title.value = template.label
  icon.value = template.icon
  step.value = 'template'
}

function chooseFocus() {
  selectedTemplate.value = null
  selectedFocus.value = null
  loadError.value = ''
  step.value = 'focus'
}

function pickFocus(add) {
  selectedFocus.value = add
  pageType.value = add.pageType
  title.value = ''
  icon.value = ''
  step.value = 'focusForm'
}

function goBack() {
  loadError.value = ''
  if (step.value === 'blank' || step.value === 'template') {
    step.value = 'flex'
    return
  }
  if (step.value === 'focusForm') {
    step.value = 'focus'
    return
  }
  if (step.value === 'coreForm') {
    step.value = 'core'
    return
  }
  selectedTemplate.value = null
  selectedFocus.value = null
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
  if (editingFocus.value || step.value === 'focusForm') {
    const tags = pageTags.value
      .split(/\s+/)
      .map((tag) => tag.replace(/^#/, '').trim())
      .filter(Boolean)
    payload.tags = [...new Set(tags)]
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
          <button type="button" class="rounded-md bg-white px-4 py-4 text-left shadow-sm hover:bg-moss hover:text-white" @click="chooseFlex">
            <span class="block text-base font-semibold">新建积木页</span>
            <span class="mt-1 block text-sm opacity-70">空白页，或从一套模板开始</span>
          </button>
          <button type="button" class="rounded-md bg-white px-4 py-4 text-left shadow-sm hover:bg-moss hover:text-white" @click="chooseFocus">
            <span class="block text-base font-semibold">新建专用页</span>
            <span class="mt-1 block text-sm opacity-70">长文、笔记、网址集或白板</span>
          </button>
          <button type="button" class="rounded-md bg-white px-4 py-4 text-left shadow-sm hover:bg-moss hover:text-white" @click="chooseCore">
            <span class="block text-base font-semibold">新建系统页</span>
            <span class="mt-1 block text-sm opacity-70">全局只有一个，会放进系统分组</span>
          </button>
        </div>

        <div v-else-if="step === 'flex'" class="grid gap-3">
          <button type="button" class="rounded-md bg-white px-4 py-3 text-left text-sm font-semibold shadow-sm hover:ring-2 hover:ring-moss" @click="chooseBlank">
            空白页
          </button>
          <div class="grid grid-cols-2 gap-3">
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
        </div>

        <div v-else-if="step === 'core'" class="grid gap-3">
          <button
            v-for="type in coreTypes"
            :key="type.type"
            type="button"
            class="rounded-md bg-white px-4 py-4 text-left shadow-sm disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="createdSingles.has(type.type)"
            :title="createdSingles.has(type.type) ? '已创建，只能有一个' : ''"
            @click="pickCore(type)"
          >
            <span class="block text-sm font-semibold">{{ type.default_icon }} {{ type.label }}</span>
          </button>
        </div>

        <div v-else-if="step === 'focus'" class="grid gap-3">
          <button
            v-for="add in focusList"
            :key="add.pageType"
            type="button"
            class="rounded-md bg-white px-4 py-4 text-left shadow-sm hover:ring-2 hover:ring-moss"
            @click="pickFocus(add)"
          >
            <span class="text-2xl">{{ add.icon }}</span>
            <span class="mt-2 block text-sm font-semibold text-ink">{{ add.label }}</span>
            <span class="mt-1 block text-xs leading-5 text-ink/60">{{ add.description }}</span>
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
          <p v-if="step === 'focusForm' && selectedFocus" class="mt-2 text-xs text-ink/50">
            不填图标时使用默认 {{ selectedFocus.icon }}
          </p>
          <template v-if="editingFocus || step === 'focusForm'">
            <label class="mt-5 block text-sm font-medium text-ink/75" for="nav-tags">专页标签</label>
            <input
              id="nav-tags"
              v-model="pageTags"
              class="mt-2 h-11 w-full rounded-md border border-black/15 bg-white px-3 text-base outline-none focus:border-moss"
              placeholder="#游戏 "
            />
            <p class="mt-1 text-xs text-ink/45">写成 #游戏 这样，空格分开。只在「专页」搜索里跨页命中。</p>
          </template>

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
