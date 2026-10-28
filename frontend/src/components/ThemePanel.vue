<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import {
  applyPreset,
  assetFileUrl,
  createPreset,
  deleteAsset,
  deletePreset,
  exportPresetFile,
  getAppearance,
  getAssets,
  getPresets,
  importPresetFile,
  patchSlots,
  updatePreset,
  uploadAssets,
} from '../api/client'

const props = defineProps({
  appearance: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['change'])

const TAB_LABELS = [
  { id: 'presets', label: '预设' },
  { id: 'library', label: '素材库' },
]
const TYPE_LABELS = [
  { id: 'colors', label: '颜色' },
  { id: 'backgrounds', label: '背景' },
  { id: 'splashes', label: '开屏' },
  { id: 'icons', label: '图标' },
]
const SLOT_LABELS = [
  { id: 'colors', label: '界面色', type: 'colors', empty: '暖白' },
  { id: 'background', label: '桌面背景', type: 'backgrounds', empty: '无' },
  { id: 'splash', label: '开屏', type: 'splashes', empty: '默认圆标' },
  { id: 'icons', label: '图标', type: 'icons', empty: '不更换' },
]
const DURATIONS = [2, 3, 5, 10, 14]
const ACCEPT = {
  colors: '.wvtheme,.json,application/json',
  backgrounds: 'image/*,video/mp4,video/webm,.png,.jpg,.jpeg,.webp,.gif,.mp4,.webm',
  splashes: 'image/*,video/mp4,video/webm,.json,.lottie,.png,.jpg,.jpeg,.webp,.gif,.mp4,.webm',
  icons: 'image/*,.zip,.png,.jpg,.jpeg,.webp,.gif',
}

const tab = ref('presets')
const libraryType = ref('colors')
const presets = ref([])
const assets = ref({ colors: [], backgrounds: [], splashes: [], icons: [] })
const message = ref('')
const errorMessage = ref('')
const busy = ref(false)
const fileInput = ref(null)
const importInput = ref(null)
const pendingId = ref('')
const pendingConflict = ref(null)
const saveName = ref('')
const creating = ref(false)
const saveAs = ref(false)
const newName = ref('')
const editingId = ref('')
const draftSlots = ref(null)
const draftConfig = ref(null)
const picked = ref([])
const uploadTarget = ref(null)

const orderedPresets = computed(() => {
  const system = presets.value.filter((item) => item.system)
  const custom = presets.value.filter((item) => !item.system)
  return [...system, ...custom]
})

const editing = computed(() => orderedPresets.value.find((item) => item.id === editingId.value) || null)

const currentName = computed(() => {
  const found = presets.value.find((item) => item.id === props.appearance.current_preset)
  return found?.name || '未绑定预设'
})

const canSave = computed(() => {
  const found = presets.value.find((item) => item.id === props.appearance.current_preset)
  return Boolean(props.appearance.dirty && found && !found.system)
})

const selectableIds = computed(() => (assets.value[libraryType.value] || []).filter((item) => !item.system).map((item) => item.id))

function assetName(type, id) {
  if (!id) {
    return ''
  }
  return assets.value[type]?.find((item) => item.id === id)?.name || id
}

function emptyDraft() {
  return {
    colors: 'warm',
    background: null,
    splash: null,
    icons: null,
  }
}

async function reload() {
  const [presetData, assetData] = await Promise.all([getPresets(), getAssets()])
  presets.value = presetData.presets || []
  assets.value = {
    colors: assetData.colors || [],
    backgrounds: assetData.backgrounds || [],
    splashes: assetData.splashes || [],
    icons: assetData.icons || [],
  }
  picked.value = picked.value.filter((id) => selectableIds.value.includes(id))
}

async function refreshAppearance() {
  emit('change', await getAppearance())
}

onMounted(async () => {
  try {
    await reload()
  } catch (error) {
    errorMessage.value = error.message || '主题列表没有加载出来'
  }
})

watch(() => props.appearance.current_preset, reload)

async function finishApply(id, body) {
  const result = await applyPreset(id, body)
  if (result.conflict) {
    pendingId.value = id
    pendingConflict.value = result.conflict
    saveName.value = ''
    return
  }
  pendingConflict.value = null
  message.value = result.warnings?.length ? `已切换，这些槽没有对上素材：${result.warnings.join('、')}` : '已切换预设'
  await refreshAppearance()
  await reload()
}

async function choosePreset(id) {
  errorMessage.value = ''
  if (id === props.appearance.current_preset && !props.appearance.dirty) {
    return
  }
  try {
    await finishApply(id)
  } catch (error) {
    errorMessage.value = error.message || '切换失败'
  }
}

async function resolve(choice) {
  if (choice === 'cancel') {
    pendingConflict.value = null
    return
  }
  try {
    const body = { resolution: choice }
    if (choice === 'save_as') {
      body.name = saveName.value.trim() || '未命名预设'
    }
    await finishApply(pendingId.value, body)
  } catch (error) {
    errorMessage.value = error.message || '没有保存'
  }
}

async function saveCurrent() {
  if (!canSave.value) {
    creating.value = true
    return
  }
  try {
    const preset = presets.value.find((item) => item.id === props.appearance.current_preset)
    await finishApply(props.appearance.current_preset, { resolution: 'save' })
    message.value = preset ? `已保存到${preset.name}` : '已保存'
  } catch (error) {
    errorMessage.value = error.message || '保存失败'
  }
}

function startEdit(item) {
  editingId.value = item.id
  draftSlots.value = { ...emptyDraft(), ...(item.slots || {}) }
  draftConfig.value = {
    splash: {
      duration: item.slot_config?.splash?.duration || 2,
      slogan: item.slot_config?.splash?.slogan || '',
    },
  }
  message.value = ''
  errorMessage.value = ''
}

function closeEdit() {
  editingId.value = ''
  draftSlots.value = null
}

async function previewIfCurrent(slotId) {
  if (!editing.value || editing.value.id !== props.appearance.current_preset || editing.value.system) {
    return
  }
  await patchSlots({
    [slotId]: draftSlots.value[slotId],
    slot_config: draftConfig.value,
  })
  await refreshAppearance()
}

async function assignDraft(slot, id) {
  draftSlots.value = { ...draftSlots.value, [slot]: id }
  try {
    await previewIfCurrent(slot)
    message.value = editing.value?.system ? '系统预设要另存为才会留下' : '槽位已改，还没写入这套预设'
  } catch (error) {
    errorMessage.value = error.message || '没有换上'
  }
}

async function setDraftDuration(duration) {
  draftConfig.value = { splash: { ...draftConfig.value.splash, duration } }
  try {
    await previewIfCurrent('splash')
  } catch (error) {
    errorMessage.value = error.message || '没有换上'
  }
}

async function setDraftSlogan(event) {
  draftConfig.value = { splash: { ...draftConfig.value.splash, slogan: event.target.value } }
  try {
    await previewIfCurrent('splash')
  } catch (error) {
    errorMessage.value = error.message || '没有换上'
  }
}

async function saveEdited() {
  if (!editing.value || !draftSlots.value) {
    return
  }
  if (editing.value.system) {
    creating.value = true
    saveAs.value = true
    newName.value = `${editing.value.name} 副本`
    return
  }
  busy.value = true
  try {
    await updatePreset(editing.value.id, { slots: draftSlots.value, slot_config: draftConfig.value })
    if (editing.value.id === props.appearance.current_preset) {
      await patchSlots({ ...draftSlots.value, slot_config: draftConfig.value })
      await refreshAppearance()
    }
    message.value = `已保存到${editing.value.name}`
    await reload()
  } catch (error) {
    errorMessage.value = error.message || '保存失败'
  } finally {
    busy.value = false
  }
}

async function makePreset() {
  const name = newName.value.trim()
  if (!name) {
    return
  }
  busy.value = true
  try {
    const extra = saveAs.value && draftSlots.value ? { slots: draftSlots.value, slot_config: draftConfig.value } : {}
    saveAs.value = false
    const created = await createPreset(name, extra)
    creating.value = false
    newName.value = ''
    await finishApply(created.id, { resolution: props.appearance.dirty ? 'discard' : '' })
    editingId.value = created.id
    message.value = `已另存为${name}`
  } catch (error) {
    errorMessage.value = error.message || '没有建成预设'
  } finally {
    busy.value = false
  }
}

async function removePreset(id) {
  try {
    await deletePreset(id)
    if (editingId.value === id) {
      closeEdit()
    }
    message.value = '已删除预设'
    await reload()
    await refreshAppearance()
  } catch (error) {
    errorMessage.value = error.message || '系统预设不能删除'
  }
}

async function exportCurrent() {
  const id = props.appearance.current_preset
  if (!id) {
    errorMessage.value = '先把当前搭配存成一套预设，再导出'
    creating.value = true
    return
  }
  try {
    const file = await exportPresetFile(id)
    const api = window.pywebview?.api
    if (api?.save_binary_file) {
      const saved = await api.save_binary_file(file.base64, file.filename)
      if (saved?.error) {
        throw new Error(saved.error)
      }
      if (saved?.path) {
        message.value = `已保存到 ${saved.path}`
      }
      return
    }
    const bytes = Uint8Array.from(atob(file.base64), (char) => char.charCodeAt(0))
    const url = URL.createObjectURL(new Blob([bytes]))
    const link = document.createElement('a')
    link.href = url
    link.download = file.filename
    link.click()
    URL.revokeObjectURL(url)
    message.value = '已导出预设'
  } catch (error) {
    errorMessage.value = error.message || '导出失败'
  }
}

async function onImport(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    return
  }
  busy.value = true
  try {
    const result = await importPresetFile(file)
    message.value = result.preset ? `已导入${result.preset.name}` : '已导入颜色'
    await reload()
  } catch (error) {
    errorMessage.value = error.message || '导入失败'
  } finally {
    busy.value = false
  }
}

function openUpload(type, slotId = '') {
  uploadTarget.value = { type, slotId }
  if (fileInput.value) {
    fileInput.value.accept = ACCEPT[type] || ''
    fileInput.value.click()
  }
}

async function onUpload(event) {
  const files = [...(event.target.files || [])]
  event.target.value = ''
  const target = uploadTarget.value
  uploadTarget.value = null
  if (!files.length || !target) {
    return
  }
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await uploadAssets(target.type, files)
    message.value = `已添加 ${result.assets?.length || files.length} 个素材`
    if (result.errors?.length) {
      errorMessage.value = result.errors.join('；')
    }
    await reload()
    const created = result.assets?.[0]
    if (target.slotId && created && draftSlots.value) {
      await assignDraft(target.slotId, created.id)
    }
  } catch (error) {
    errorMessage.value = error.message || '上传失败'
  } finally {
    busy.value = false
  }
}

function toggleCreate() {
  creating.value = !creating.value
  if (!creating.value) {
    saveAs.value = false
  }
}

function showLibrary(id) {
  libraryType.value = id
  picked.value = []
}

function togglePicked(id) {
  picked.value = picked.value.includes(id) ? picked.value.filter((item) => item !== id) : [...picked.value, id]
}

function selectAll() {
  picked.value = [...selectableIds.value]
}

function clearPicked() {
  picked.value = []
}

async function removePicked() {
  if (!picked.value.length) {
    return
  }
  const ids = [...picked.value]
  try {
    for (const id of ids) {
      await deleteAsset(libraryType.value, id)
    }
    picked.value = []
    message.value = `已删除 ${ids.length} 个素材`
    await reload()
  } catch (error) {
    errorMessage.value = error.message || '系统素材不能删除'
    await reload()
  }
}

async function removeAsset(type, id) {
  try {
    await deleteAsset(type, id)
    picked.value = picked.value.filter((item) => item !== id)
    await reload()
  } catch (error) {
    errorMessage.value = error.message || '系统素材不能删除'
  }
}
</script>

<template>
  <div>
    <div class="flex items-end justify-between gap-3">
      <p class="text-sm text-ink">
        {{ currentName }}
        <span v-if="appearance.dirty">，还有未保存的改动</span>
      </p>
      <button v-if="appearance.dirty" type="button" class="h-8 rounded bg-ink px-3 text-xs text-white" @click="saveCurrent">
        {{ canSave ? '保存' : '另存为' }}
      </button>
    </div>
    <div class="mt-3 flex gap-4 border-b border-black/10">
      <button
        v-for="item in TAB_LABELS"
        :key="item.id"
        type="button"
        class="h-8 text-sm"
        :class="tab === item.id ? 'border-b-2 border-ink text-ink' : 'text-ink/45'"
        @click="tab = item.id"
      >
        {{ item.label }}
      </button>
    </div>

    <div v-if="tab === 'presets'" class="mt-3 space-y-1">
      <div v-for="item in orderedPresets" :key="item.id" class="flex items-center gap-2">
        <button
          type="button"
          class="wv-theme-row"
          :class="appearance.current_preset === item.id ? 'is-on' : ''"
          @click="choosePreset(item.id)"
        >
          <span class="wv-theme-swatch" :style="{ background: item.system ? 'var(--wv-dawn)' : '#e6e0f2' }" />
          <span class="min-w-0">
            <span class="block truncate text-sm text-ink">{{ item.name }}</span>
            <span class="block text-xs text-ink/45">{{ item.system ? '系统预设' : '我的预设' }}</span>
          </span>
        </button>
        <button type="button" class="px-2 text-xs text-ink/55" @click="startEdit(item)">编辑</button>
        <button v-if="!item.system" type="button" class="px-2 text-xs text-ink/40" @click="removePreset(item.id)">删除</button>
      </div>

      <div v-if="editing && draftSlots && draftConfig" class="mt-3 border-t border-black/10 pt-3">
        <div class="flex items-center justify-between">
          <p class="text-sm text-ink">编辑「{{ editing.name }}」</p>
          <button type="button" class="text-xs text-ink/40" @click="closeEdit">收起</button>
        </div>
        <section v-for="slot in SLOT_LABELS" :key="slot.id" class="mt-3">
          <p class="text-sm text-ink">{{ slot.label }}</p>
          <p class="text-xs text-ink/45">{{ assetName(slot.type, draftSlots[slot.id]) || slot.empty }}</p>
          <div class="mt-1 max-h-36 space-y-1 overflow-y-auto">
            <button v-if="slot.id !== 'colors'" type="button" class="block h-7 text-sm text-ink/60" @click="assignDraft(slot.id, null)">{{ slot.empty }}</button>
            <button
              v-for="item in assets[slot.type]"
              :key="item.id"
              type="button"
              class="block h-7 max-w-full truncate text-left text-sm"
              :class="draftSlots[slot.id] === item.id ? 'text-ink' : 'text-ink/70'"
              @click="assignDraft(slot.id, item.id)"
            >
              {{ item.name }}
            </button>
          </div>
          <button type="button" class="mt-1 h-7 text-xs text-moss" @click="openUpload(slot.type, slot.id)">+ 上传新素材</button>
        </section>
        <div class="mt-3">
          <p class="text-sm text-ink/60">开屏时长</p>
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="seconds in DURATIONS"
              :key="seconds"
              type="button"
              class="h-8 rounded px-2 text-xs"
              :class="draftConfig.splash.duration === seconds ? 'bg-ink text-white' : 'bg-white'"
              @click="setDraftDuration(seconds)"
            >
              {{ seconds }} 秒
            </button>
          </div>
          <input
            class="mt-2 h-9 w-full bg-white px-2 text-sm outline-none"
            :value="draftConfig.splash.slogan"
            maxlength="40"
            placeholder="开屏底部的一句话"
            @change="setDraftSlogan"
          />
        </div>
        <button type="button" class="mt-3 h-8 rounded bg-ink px-3 text-xs text-white" :disabled="busy" @click="saveEdited">
          {{ editing.system ? '另存为' : '保存' }}
        </button>
      </div>

      <div v-if="creating" class="mt-3 flex gap-2">
        <input v-model="newName" class="h-9 min-w-0 flex-1 bg-white px-2 text-sm outline-none" placeholder="新预设的名字" @keyup.enter="makePreset" />
        <button type="button" class="h-9 rounded bg-ink px-3 text-xs text-white" :disabled="busy" @click="makePreset">保存</button>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="toggleCreate">新建预设</button>
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="importInput.click()">导入</button>
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="exportCurrent">导出当前</button>
      </div>
    </div>

    <div v-else class="mt-3">
      <div class="flex gap-3">
        <button
          v-for="item in TYPE_LABELS"
          :key="item.id"
          type="button"
          class="text-sm"
          :class="libraryType === item.id ? 'text-ink' : 'text-ink/40'"
          @click="showLibrary(item.id)"
        >
          {{ item.label }}
        </button>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <button type="button" class="h-7 rounded bg-white px-2" @click="selectAll">全选</button>
        <button type="button" class="h-7 rounded bg-white px-2" @click="clearPicked">取消选择</button>
        <button type="button" class="h-7 rounded bg-ink px-2 text-white" :disabled="!picked.length" @click="removePicked">批量删除</button>
        <span class="text-ink/40">已选 {{ picked.length }}</span>
      </div>
      <div class="mt-3 space-y-2">
        <div v-for="item in assets[libraryType]" :key="item.id" class="flex items-center gap-3">
          <input v-if="!item.system" type="checkbox" :checked="picked.includes(item.id)" @change="togglePicked(item.id)" />
          <span v-else class="w-4 text-center text-[10px] text-ink/30">锁</span>
          <img
            v-if="item.media === 'image'"
            :src="assetFileUrl(libraryType, item.id)"
            alt=""
            class="h-12 w-16 object-cover"
          />
          <span v-else class="grid h-12 w-16 place-items-center bg-white text-xs text-ink/50">{{ item.media === 'palette' ? '颜色' : item.media === 'video' ? '视频' : item.media === 'pack' ? '图标' : '动画' }}</span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm">{{ item.name }}</span>
            <span class="block text-xs text-ink/40">{{ item.system ? '系统' : '我的' }}</span>
          </span>
          <button v-if="!item.system" type="button" class="text-xs text-ink/40" @click="removeAsset(libraryType, item.id)">删除</button>
        </div>
      </div>
      <button type="button" class="mt-3 h-8 rounded bg-white px-3 text-xs" @click="openUpload(libraryType)">添加素材</button>
    </div>

    <p v-if="message" class="mt-3 text-xs text-moss">{{ message }}</p>
    <p v-if="errorMessage" class="mt-2 text-xs text-ember">{{ errorMessage }}</p>

    <div v-if="pendingConflict" class="fixed inset-0 z-[80] grid place-items-center bg-black/45 px-4">
      <div class="w-full max-w-sm bg-[#fcfaf5] p-5">
        <p class="text-sm text-ink">当前配置有未保存修改</p>
        <input v-if="pendingConflict.choices?.includes('save_as')" v-model="saveName" class="mt-3 h-9 w-full bg-white px-2 text-sm outline-none" placeholder="另存为的名字" />
        <div class="mt-4 flex flex-wrap gap-2">
          <button v-if="pendingConflict.can_save" type="button" class="h-8 rounded bg-ink px-3 text-xs text-white" @click="resolve('save')">保存</button>
          <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="resolve('save_as')">另存为</button>
          <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="resolve('discard')">放弃</button>
          <button type="button" class="h-8 rounded px-3 text-xs text-ink/50" @click="resolve('cancel')">取消</button>
        </div>
      </div>
    </div>

    <input ref="fileInput" class="wv-file-input" type="file" multiple @change="onUpload" />
    <input ref="importInput" class="wv-file-input" type="file" accept=".wvpack,.wvtheme,.json" @change="onImport" />
  </div>
</template>
