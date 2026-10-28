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
  { id: 'slots', label: '槽位' },
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

const tab = ref('presets')
const libraryType = ref('colors')
const presets = ref([])
const assets = ref({ colors: [], backgrounds: [], splashes: [], icons: [] })
const openSlot = ref('')
const message = ref('')
const errorMessage = ref('')
const busy = ref(false)
const fileInput = ref(null)
const importInput = ref(null)
const staged = ref([])
const stagedType = ref('backgrounds')
const pendingId = ref('')
const pendingConflict = ref(null)
const saveName = ref('')
const creating = ref(false)
const newName = ref('')

const currentName = computed(() => {
  const found = presets.value.find((item) => item.id === props.appearance.current_preset)
  return found?.name || '未绑定预设'
})

const canSave = computed(() => {
  const found = presets.value.find((item) => item.id === props.appearance.current_preset)
  return Boolean(props.appearance.dirty && found && !found.system)
})

function assetName(type, id) {
  if (!id) {
    return ''
  }
  return assets.value[type]?.find((item) => item.id === id)?.name || id
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

async function makePreset() {
  const name = newName.value.trim()
  if (!name) {
    return
  }
  busy.value = true
  try {
    const created = await createPreset(name)
    creating.value = false
    newName.value = ''
    await finishApply(created.id, { resolution: 'discard' })
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

function guessType(files) {
  const names = files.map((file) => file.name.toLowerCase())
  if (names.every((name) => name.endsWith('.json') || name.endsWith('.wvtheme'))) {
    return 'colors'
  }
  if (names.every((name) => name.endsWith('.zip'))) {
    return 'icons'
  }
  if (names.some((name) => name.endsWith('.mp4') || name.endsWith('.webm'))) {
    return 'backgrounds'
  }
  return 'backgrounds'
}

function stageFiles(event) {
  const files = [...(event.target.files || [])]
  event.target.value = ''
  if (!files.length) {
    return
  }
  staged.value = files
  stagedType.value = guessType(files)
  message.value = ''
}

async function commitUpload() {
  if (!staged.value.length) {
    return
  }
  busy.value = true
  errorMessage.value = ''
  try {
    await uploadAssets(stagedType.value, staged.value)
    message.value = `已添加 ${staged.value.length} 个素材`
    staged.value = []
    libraryType.value = stagedType.value
    await reload()
  } catch (error) {
    errorMessage.value = error.message || '上传失败'
  } finally {
    busy.value = false
  }
}

async function removeAsset(type, id) {
  try {
    await deleteAsset(type, id)
    await reload()
  } catch (error) {
    errorMessage.value = error.message || '系统素材不能删除'
  }
}

async function assignSlot(slot, id) {
  const payload = { [slot]: id }
  try {
    await patchSlots(payload)
    openSlot.value = ''
    message.value = '这个槽已换上，还没有写进预设'
    await refreshAppearance()
  } catch (error) {
    errorMessage.value = error.message || '没有换上'
  }
}

async function setDuration(duration) {
  const config = {
    splash: {
      duration,
      slogan: props.appearance.slot_config?.splash?.slogan || '',
    },
  }
  await patchSlots({ slot_config: config })
  await refreshAppearance()
}

async function setSlogan(event) {
  const config = {
    splash: {
      duration: props.appearance.slot_config?.splash?.duration || props.appearance.splash_duration || 2,
      slogan: event.target.value,
    },
  }
  await patchSlots({ slot_config: config })
  await refreshAppearance()
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
      <div v-for="item in presets" :key="item.id" class="flex items-center gap-2">
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
        <button v-if="!item.system" type="button" class="px-2 text-xs text-ink/40" @click="removePreset(item.id)">删除</button>
      </div>
      <div v-if="creating" class="mt-3 flex gap-2">
        <input v-model="newName" class="h-9 min-w-0 flex-1 bg-white px-2 text-sm outline-none" placeholder="新预设的名字" @keyup.enter="makePreset" />
        <button type="button" class="h-9 rounded bg-ink px-3 text-xs text-white" :disabled="busy" @click="makePreset">保存</button>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="creating = !creating">新建预设</button>
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="importInput.click()">导入</button>
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" @click="exportCurrent">导出当前</button>
      </div>
    </div>

    <div v-else-if="tab === 'library'" class="mt-3">
      <div class="flex gap-3">
        <button
          v-for="item in TYPE_LABELS"
          :key="item.id"
          type="button"
          class="text-sm"
          :class="libraryType === item.id ? 'text-ink' : 'text-ink/40'"
          @click="libraryType = item.id"
        >
          {{ item.label }}
        </button>
      </div>
      <div class="mt-3 space-y-2">
        <div v-for="item in assets[libraryType]" :key="item.id" class="flex items-center gap-3">
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
      <button type="button" class="mt-3 h-8 rounded bg-white px-3 text-xs" @click="fileInput.click()">添加素材</button>
      <div v-if="staged.length" class="mt-3">
        <p class="text-sm text-ink">这 {{ staged.length }} 个文件用作</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <button v-for="item in TYPE_LABELS" :key="item.id" type="button" class="h-8 rounded px-3 text-xs" :class="stagedType === item.id ? 'bg-ink text-white' : 'bg-white'" @click="stagedType = item.id">{{ item.label }}</button>
        </div>
        <button type="button" class="mt-2 h-8 rounded bg-ink px-3 text-xs text-white" :disabled="busy" @click="commitUpload">放入素材库</button>
      </div>
    </div>

    <div v-else class="mt-3 space-y-3">
      <section v-for="slot in SLOT_LABELS" :key="slot.id">
        <button type="button" class="flex w-full items-center justify-between text-left" @click="openSlot = openSlot === slot.id ? '' : slot.id">
          <span class="text-sm text-ink">{{ slot.label }}</span>
          <span class="text-sm text-ink/50">{{ assetName(slot.type, appearance.slots?.[slot.id]) || slot.empty }}</span>
        </button>
        <div v-if="openSlot === slot.id" class="mt-2 space-y-1">
          <button v-if="slot.id !== 'colors'" type="button" class="block h-8 text-sm text-ink/60" @click="assignSlot(slot.id, null)">{{ slot.empty }}</button>
          <button
            v-for="item in assets[slot.type]"
            :key="item.id"
            type="button"
            class="block h-8 max-w-full truncate text-left text-sm"
            :class="appearance.slots?.[slot.id] === item.id ? 'text-ink' : 'text-ink/70'"
            @click="assignSlot(slot.id, item.id)"
          >
            {{ item.name }}
          </button>
        </div>
      </section>
      <div>
        <p class="text-sm text-ink/60">开屏时长</p>
        <div class="mt-2 flex gap-2">
          <button
            v-for="seconds in DURATIONS"
            :key="seconds"
            type="button"
            class="h-8 rounded px-2 text-xs"
            :class="(appearance.slot_config?.splash?.duration || appearance.splash_duration) === seconds ? 'bg-ink text-white' : 'bg-white'"
            @click="setDuration(seconds)"
          >
            {{ seconds }} 秒
          </button>
        </div>
        <input
          class="mt-2 h-9 w-full bg-white px-2 text-sm outline-none"
          :value="appearance.slot_config?.splash?.slogan || appearance.splash_caption || ''"
          maxlength="40"
          placeholder="开屏底部的一句话"
          @change="setSlogan"
        />
      </div>
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

    <input ref="fileInput" class="wv-file-input" type="file" multiple accept=".wvtheme,.json,.png,.jpg,.jpeg,.webp,.gif,.mp4,.webm,.lottie,.zip,video/*,image/*" @change="stageFiles" />
    <input ref="importInput" class="wv-file-input" type="file" accept=".wvpack,.wvtheme,.json" @change="onImport" />
  </div>
</template>
