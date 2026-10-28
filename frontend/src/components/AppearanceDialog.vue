<script setup>
import { computed, ref, watch } from 'vue'

import {
  activatePack,
  backgroundUrl,
  clearBackground,
  clearSplash,
  deleteCustomTheme,
  deletePack,
  downloadCurrentTheme,
  importThemeFile,
  packFileUrl,
  splashUrl,
  updateAppearance,
  uploadBackground,
  uploadSplash,
} from '../api/client'
import AiSettings from './AiSettings.vue'
import ThemePanel from './ThemePanel.vue'
import BackupPanel from './BackupPanel.vue'
import PrivacyPanel from './PrivacyPanel.vue'
import RemotePanel from './RemotePanel.vue'

const THEMES = [
  { id: 'warm', label: '暖白', swatch: '#f4efe7' },
  { id: 'mint', label: '薄荷', swatch: '#e5f4ee' },
  { id: 'sky', label: '天蓝', swatch: '#e7f1fb' },
  { id: 'sakura', label: '樱粉', swatch: '#fbeaf0' },
  { id: 'ash', label: '灰调', swatch: '#eceeef' },
]

const SPLASH_SECONDS = [2, 3, 5, 10, 14]

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  appearance: {
    type: Object,
    required: true,
  },
  groupId: {
    type: Number,
    default: null,
  },
  groupName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close', 'change', 'open-guide', 'move-orb', 'opacity'])

const page = ref('look')
const maskArmed = ref(false)
const busy = ref('')
const busyName = ref('')
const errorMessage = ref('')
const statusMessage = ref('')
const imageInput = ref(null)
const videoInput = ref(null)
const groupInput = ref(null)
const splashInput = ref(null)
const themeInput = ref(null)
const themeMenu = ref(null)
const opacityPercent = ref(85)
const captionDraft = ref('正在编织你的宇宙')
let opacityTimer

const groupFile = computed(() => {
  if (props.groupId == null) {
    return ''
  }
  return props.appearance.groups?.[String(props.groupId)] || ''
})

const groupLabel = computed(() => {
  if (props.groupId == null) {
    return ''
  }
  return props.appearance.group_names?.[String(props.groupId)] || groupFile.value
})

const currentThemeName = computed(() => {
  const pack = (props.appearance.packs || []).find((item) => item.id === props.appearance.active_pack)
  if (pack && props.appearance.theme === pack.id) {
    return pack.name
  }
  const builtin = THEMES.find((item) => item.id === props.appearance.theme)
  if (builtin) {
    return builtin.label
  }
  const custom = (props.appearance.custom_themes || []).find((item) => item.id === props.appearance.theme)
  return custom?.name || props.appearance.theme || '暖白'
})

const colorThemes = computed(() => {
  const packIds = new Set((props.appearance.packs || []).map((item) => item.id))
  return (props.appearance.custom_themes || []).filter((item) => !packIds.has(item.id))
})

const splashPreview = computed(() => {
  const file = props.appearance.splash_file
  if (!file || props.appearance.splash_mode === 'default') {
    return ''
  }
  return splashUrl(file)
})

watch(
  () => props.open,
  () => {
    errorMessage.value = ''
    statusMessage.value = ''
    busyName.value = ''
  },
)

watch(
  () => props.appearance.splash_caption,
  (value) => {
    captionDraft.value = value || '正在编织你的宇宙'
  },
  { immediate: true },
)

watch(
  () => props.appearance.bg_opacity,
  (value) => {
    const next = Math.round((value ?? 0.85) * 100)
    if (next !== opacityPercent.value) {
      opacityPercent.value = next
    }
  },
  { immediate: true },
)

async function setTheme(id) {
  emit('change', await updateAppearance({ theme: id }))
}

async function setBar(id) {
  emit('change', await updateAppearance({ bar: id }))
}

async function setPlayer(id) {
  emit('change', await updateAppearance({ player: id }))
}

async function setSpread(id) {
  emit('change', await updateAppearance({ player_spread: id }))
}

async function setProgressStyle(id) {
  emit('change', await updateAppearance({ progress_style: id }))
}

async function setProgressColor(event) {
  emit('change', await updateAppearance({ progress_style: 'solid', progress_color: event.target.value }))
}

async function setLowPower(event) {
  emit('change', await updateAppearance({ low_power: event.target.checked }))
}

async function setSplashDuration(seconds) {
  emit('change', await updateAppearance({ splash_duration: seconds }))
}

async function setSplashLoop(event) {
  emit('change', await updateAppearance({ splash_loop: event.target.checked }))
}

async function saveCaption() {
  const text = captionDraft.value.trim() || '正在编织你的宇宙'
  emit('change', await updateAppearance({ splash_caption: text }))
}

async function usePack(packId) {
  errorMessage.value = ''
  try {
    emit('change', await activatePack(packId))
    statusMessage.value = '已切换主题包，开屏下次启动时播放'
  } catch (error) {
    errorMessage.value = error.message || '无法切换主题包'
  }
}

function onOpacityInput(event) {
  const next = Number(event.target.value)
  opacityPercent.value = next
  emit('opacity', next / 100)
  window.clearTimeout(opacityTimer)
  opacityTimer = window.setTimeout(async () => {
    emit('change', await updateAppearance({ bg_opacity: next / 100 }))
  }, 180)
}

async function sendFile(file, kind, groupId) {
  busy.value = kind
  busyName.value = file.name || '文件'
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    emit('change', await uploadBackground(file, kind, groupId))
    statusMessage.value = `已上传 ${file.name || '文件'}`
  } catch (error) {
    errorMessage.value = error.message || '上传失败'
  } finally {
    busy.value = ''
  }
}

function takeFile(event, kind, groupId) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    errorMessage.value = '没有读到文件'
    statusMessage.value = ''
    return
  }
  sendFile(file, kind, groupId)
}

function onImage(event) {
  takeFile(event, 'image', null)
}

function onVideo(event) {
  takeFile(event, 'video', null)
}

function onMaskDown(event) {
  maskArmed.value = event.target === event.currentTarget
}

function onMaskUp(event) {
  const close = maskArmed.value && event.target === event.currentTarget
  maskArmed.value = false
  if (close) {
    emit('close')
  }
}

function onGroupImage(event) {
  if (props.groupId == null) {
    return
  }
  takeFile(event, 'image', props.groupId)
}

async function onSplash(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    errorMessage.value = '没有读到文件'
    return
  }
  busy.value = 'splash'
  busyName.value = file.name
  errorMessage.value = ''
  try {
    emit('change', await uploadSplash(file))
    statusMessage.value = `封面已替换为 ${file.name}`
  } catch (error) {
    errorMessage.value = error.message || '封面上传失败'
  } finally {
    busy.value = ''
  }
}

async function resetSplash() {
  try {
    emit('change', await clearSplash())
    statusMessage.value = '已恢复默认封面'
  } catch (error) {
    errorMessage.value = error.message || '无法恢复默认封面'
  }
}

async function onThemeFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    return
  }
  busy.value = 'theme'
  busyName.value = file.name
  errorMessage.value = ''
  try {
    emit('change', await importThemeFile(file))
    statusMessage.value = `已导入 ${file.name}`
  } catch (error) {
    errorMessage.value = error.message || '导入主题失败'
  } finally {
    busy.value = ''
  }
}

async function exportTheme() {
  try {
    const { text, filename } = await downloadCurrentTheme()
    const api = window.pywebview?.api
    if (api?.save_theme_file) {
      const saved = await api.save_theme_file(text, filename)
      if (saved?.error) {
        throw new Error(saved.error)
      }
      if (saved?.path) {
        statusMessage.value = `已保存到 ${saved.path}`
      }
      return
    }
    const blob = new Blob([text], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    statusMessage.value = '已导出当前主题'
  } catch (error) {
    errorMessage.value = error.message || '导出失败'
  }
}

function openThemeMenu(event, item) {
  event.preventDefault()
  themeMenu.value = {
    x: event.clientX,
    y: event.clientY,
    id: item.id,
    kind: item.kind,
  }
}

function closeThemeMenu() {
  themeMenu.value = null
}

async function dropTheme(themeId) {
  closeThemeMenu()
  try {
    emit('change', await deleteCustomTheme(themeId))
  } catch (error) {
    errorMessage.value = error.message || '无法删除主题'
  }
}

async function dropPack(packId) {
  closeThemeMenu()
  try {
    emit('change', await deletePack(packId))
    statusMessage.value = '已删除主题包'
  } catch (error) {
    errorMessage.value = error.message || '无法删除主题包'
  }
}

async function clear(kind, groupId) {
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    emit('change', await clearBackground(kind, groupId))
  } catch (error) {
    errorMessage.value = error.message || '清除失败'
  }
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[70] grid place-items-center bg-black/40 px-4" @pointerdown="onMaskDown" @pointerup="onMaskUp">
    <div class="wv-surface max-h-[86vh] w-full max-w-lg overflow-y-auto rounded-md p-5 shadow-2xl">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-ink">设置</h2>
        <button type="button" class="text-ink/50" @click="emit('close')">×</button>
      </div>
      <div class="mb-4 flex flex-wrap gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'look' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'look'">外观</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'theme' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'theme'">主题</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'ai' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'ai'">AI</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'remote' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'remote'">远程</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'backup' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'backup'">备份</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'privacy' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'privacy'">隐私</button>
      </div>
      <AiSettings v-if="page === 'ai'" />
      <RemotePanel v-else-if="page === 'remote'" />
      <BackupPanel v-else-if="page === 'backup'" @need-privacy="page = 'privacy'" />
      <ThemePanel v-else-if="page === 'theme'" :appearance="appearance" @change="emit('change', $event)" />
      <template v-else>
      <p class="text-xs text-ink/45">背景不透明度</p>
      <div class="mt-2 flex items-center gap-3">
        <input type="range" min="0" max="100" :value="opacityPercent" class="flex-1" @input="onOpacityInput" />
        <span class="w-10 text-right text-xs text-ink/70">{{ opacityPercent }}%</span>
      </div>
      <p class="mt-1 text-xs text-ink/40">100% 时界面盖住背景，0% 只留界面底色。</p>
      <p class="mt-4 text-xs text-ink/45">分组栏</p>
      <div class="mt-2 flex gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.bar === 'push' ? 'bg-ink text-white' : 'bg-white'" @click="setBar('push')">推栏</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.bar === 'overlay' ? 'bg-ink text-white' : 'bg-white'" @click="setBar('overlay')">名字浮出</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.bar === 'stack' ? 'bg-ink text-white' : 'bg-white'" @click="setBar('stack')">图标在上</button>
      </div>
      <p class="mt-4 text-xs text-ink/45">悬浮球位置</p>
      <div class="mt-2 flex gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player === 'corner' || !appearance.player ? 'bg-ink text-white' : 'bg-white'" @click="setPlayer('corner')">右下角</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player === 'bottom' ? 'bg-ink text-white' : 'bg-white'" @click="setPlayer('bottom')">正下方</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player === 'side' ? 'bg-ink text-white' : 'bg-white'" @click="setPlayer('side')">右侧中间</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player === 'free' ? 'bg-ink text-white' : 'bg-white'" @click="emit('move-orb')">移动悬浮球</button>
      </div>
      <p class="mt-4 text-xs text-ink/45">面板展开</p>
      <div class="mt-2 flex gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="!appearance.player_spread || appearance.player_spread === 'auto' ? 'bg-ink text-white' : 'bg-white'" @click="setSpread('auto')">自动</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player_spread === 'center' ? 'bg-ink text-white' : 'bg-white'" @click="setSpread('center')">强制从中间</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player_spread === 'side' ? 'bg-ink text-white' : 'bg-white'" @click="setSpread('side')">强制从一侧</button>
      </div>
      <p class="mt-4 text-xs text-ink/45">进度条</p>
      <div class="mt-2 flex items-center gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.progress_style !== 'gradient' ? 'bg-ink text-white' : 'bg-white'" @click="setProgressStyle('solid')">单色</button>
        <input type="color" :value="appearance.progress_color || '#3f6f57'" title="进度颜色" @change="setProgressColor" />
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.progress_style === 'gradient' ? 'bg-ink text-white' : 'bg-white'" @click="setProgressStyle('gradient')">彩色</button>
      </div>
      <label class="mt-4 flex items-center gap-2 text-sm text-ink/80">
        <input type="checkbox" :checked="appearance.low_power" @change="setLowPower" />
        低性能模式（不播视频背景）
      </label>
      <div class="mt-4 flex flex-wrap gap-2">
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" :disabled="busy === 'image'" @click="imageInput.click()">上传全局背景图</button>
        <button type="button" class="h-8 rounded px-3 text-xs text-ink/50" @click="clear('image', null)">清除</button>
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" :disabled="busy === 'video'" @click="videoInput.click()">上传 MP4 背景</button>
        <button type="button" class="h-8 rounded px-3 text-xs text-ink/50" @click="clear('video', null)">清除视频</button>
      </div>
      <p v-if="busy" class="mt-2 text-xs text-moss">正在上传 {{ busyName }}…</p>
      <p v-else-if="statusMessage" class="mt-2 text-xs text-moss">{{ statusMessage }}</p>
      <p v-if="appearance.global_image" class="mt-2 text-xs text-ink/70">当前图片 {{ appearance.global_image_name || appearance.global_image }}</p>
      <img v-if="appearance.global_image" :src="backgroundUrl(appearance.global_image)" alt="" class="mt-2 h-20 w-full rounded object-cover" />
      <p v-if="appearance.global_video" class="mt-2 text-xs text-ink/70">当前视频 {{ appearance.global_video_name || appearance.global_video }}</p>
      <video
        v-if="appearance.global_video"
        :src="backgroundUrl(appearance.global_video)"
        class="mt-2 h-20 w-full rounded object-cover"
        muted
        playsinline
      />
      <div v-if="groupId != null" class="mt-4">
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" :disabled="busy === 'image'" @click="groupInput.click()">上传「{{ groupName || '当前分组' }}」背景</button>
        <button type="button" class="ml-2 h-8 rounded px-3 text-xs text-ink/50" @click="clear('image', groupId)">清除分组背景</button>
        <p v-if="groupFile" class="mt-2 text-xs text-ink/70">分组背景 {{ groupLabel }}</p>
        <img v-if="groupFile" :src="backgroundUrl(groupFile)" alt="" class="mt-2 h-20 w-full rounded object-cover" />
      </div>
      <p class="mt-5 text-xs text-ink/45">欢迎封面</p>
      <p class="mt-1 text-xs text-ink/70">
        {{ appearance.splash_mode === 'default' ? '默认封面' : `当前：${appearance.splash_name || appearance.splash_file}（${appearance.splash_mode}）` }}
      </p>
      <img v-if="appearance.splash_mode === 'image' && splashPreview" :src="splashPreview" alt="" class="mt-2 h-20 w-full rounded object-cover" />
      <video
        v-else-if="appearance.splash_mode === 'video' && splashPreview"
        :src="splashPreview"
        class="mt-2 h-20 w-full rounded object-cover"
        muted
        playsinline
      />
      <p v-else-if="appearance.splash_mode === 'lottie'" class="mt-2 text-xs text-ink/50">Lottie 动画已保存，下次启动播放。</p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button type="button" class="h-8 rounded bg-white px-3 text-xs" :disabled="busy === 'splash'" @click="splashInput.click()">替换封面</button>
        <button type="button" class="h-8 rounded px-3 text-xs text-ink/50" @click="resetSplash">恢复默认</button>
      </div>
      <p class="mt-3 text-xs text-ink/45">播放时长</p>
      <div class="mt-2 flex gap-2">
        <button
          v-for="seconds in SPLASH_SECONDS"
          :key="seconds"
          type="button"
          class="h-8 rounded px-3 text-xs"
          :class="(appearance.splash_duration || 2) === seconds ? 'bg-ink text-white' : 'bg-white'"
          @click="setSplashDuration(seconds)"
        >
          {{ seconds }} 秒
        </button>
      </div>
      <label class="mt-3 block text-xs text-ink/45">
        底部标语
        <input v-model="captionDraft" class="mt-1 h-9 w-full bg-white px-2 text-sm text-ink outline-none" maxlength="40" @change="saveCaption" />
      </label>
      <label class="mt-3 flex items-center gap-2 text-sm text-ink/80">
        <input type="checkbox" :checked="appearance.splash_loop !== false" @change="setSplashLoop" />
        视频循环到时长结束
      </label>
      <p v-if="errorMessage" class="mt-3 text-xs text-ember">{{ errorMessage }}</p>
      <button type="button" class="mt-5 text-sm text-moss" @click="emit('open-guide')">再次显示使用说明</button>
      </template>
      <input ref="imageInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif" @change="onImage" />
      <input ref="videoInput" class="wv-file-input" type="file" accept="video/mp4,.mp4" @change="onVideo" />
      <input ref="groupInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif" @change="onGroupImage" />
      <input ref="splashInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,video/webm,video/mp4,application/json,.png,.jpg,.jpeg,.webp,.gif,.webm,.mp4,.json,.lottie" @change="onSplash" />
      <input ref="themeInput" class="wv-file-input" type="file" accept=".wvtheme,.wvpack,.json,application/json,application/zip" @change="onThemeFile" />
    </div>
  </div>
</template>
