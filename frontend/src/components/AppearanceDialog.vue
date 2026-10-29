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
  getAutostart,
  getDataDir,
  getSystemStatus,
  moveDataDir,
  setAutostart,
  updateAppearance,
  uploadBackground,
  uploadSplash,
} from '../api/client'
import { formatBuiltAt, frontendBuiltAt } from '../buildInfo'
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
const autostart = ref(false)
const autostartNote = ref('')
const dataPath = ref('')
const dataNote = ref('')
const dataBusy = ref(false)
const systemStatus = ref({ version: '', revision: '' })
const systemNote = ref('')
const glassNote = ref('')
const builtLabel = formatBuiltAt(frontendBuiltAt)
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
  (open) => {
    if (open) {
      loadDataDir()
      loadStatus()
    }
    errorMessage.value = ''
    statusMessage.value = ''
    busyName.value = ''
    if (open) {
      loadAutostart()
    }
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

async function setGlass(event) {
  const next = event.target.checked
  glassNote.value = ''
  try {
    emit('change', await updateAppearance({ glass: next }))
    glassNote.value = '正在重新打开窗口。'
    const bridge = window.pywebview?.api
    if (bridge && typeof bridge.relaunch === 'function') {
      await bridge.relaunch()
      return
    }
    glassNote.value = '已保存。用桌面窗口重新打开后才会生效。'
  } catch (error) {
    event.target.checked = !next
    glassNote.value = error.message || '没有保存'
  }
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
  if (!window.confirm('确定删除这个主题吗？')) {
    return
  }
  try {
    emit('change', await deleteCustomTheme(themeId))
  } catch (error) {
    errorMessage.value = error.message || '无法删除主题'
  }
}

async function dropPack(packId) {
  closeThemeMenu()
  if (!window.confirm('确定删除这个主题包吗？')) {
    return
  }
  try {
    emit('change', await deletePack(packId))
    statusMessage.value = '已删除主题包'
  } catch (error) {
    errorMessage.value = error.message || '无法删除主题包'
  }
}

async function setOrbHidden(event) {
  try {
    emit('change', await updateAppearance({ player_hidden: event.target.checked }))
  } catch (error) {
    errorMessage.value = error.message || '没有保存'
  }
}

async function loadAutostart() {
  try {
    const data = await getAutostart()
    autostart.value = Boolean(data.enabled)
    autostartNote.value = ''
  } catch (error) {
    autostartNote.value = error.message || '读不到开机自启'
  }
}

async function loadStatus() {
  systemNote.value = ''
  try {
    systemStatus.value = await getSystemStatus()
  } catch (error) {
    systemNote.value = error.message || '读不到系统状态'
  }
}

async function loadDataDir() {
  dataNote.value = ''
  try {
    const data = await getDataDir()
    dataPath.value = data.path || ''
  } catch (error) {
    dataNote.value = error.message || '读不到数据目录'
  }
}

async function changeDataDir() {
  if (dataBusy.value) {
    return
  }
  let path = ''
  const bridge = window.pywebview?.api
  if (bridge && typeof bridge.pick_folder === 'function') {
    const picked = await bridge.pick_folder()
    if (!picked) {
      return
    }
    if (picked.error) {
      dataNote.value = picked.error
      return
    }
    path = picked.path || ''
  } else {
    path = window.prompt('填写新的数据目录绝对路径', dataPath.value) || ''
  }
  path = path.trim()
  if (!path) {
    return
  }
  if (!window.confirm('应用将关闭，数据将迁移至新位置。核对成功之前，原来的数据不会删除。')) {
    return
  }
  dataBusy.value = true
  dataNote.value = ''
  try {
    await moveDataDir(path)
    dataNote.value = '已复制并核对。正在重新打开。'
    if (bridge && typeof bridge.relaunch === 'function') {
      await bridge.relaunch()
      return
    }
    dataNote.value = '目录已切换。请关闭并重新启动 Weaveverse。'
  } catch (error) {
    dataNote.value = error.message || '没有迁走，原来的数据还在'
  } finally {
    dataBusy.value = false
  }
}

async function toggleAutostart(event) {
  const next = event.target.checked
  try {
    const data = await setAutostart(next)
    autostart.value = Boolean(data.enabled)
    autostartNote.value = data.enabled ? '下次登录会自动打开' : '已取消开机自启'
  } catch (error) {
    event.target.checked = autostart.value
    autostartNote.value = error.message || '没有写上启动项'
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
    <div class="wv-settings shadow-2xl" @pointerdown.stop>
      <nav class="wv-settings-nav">
        <button type="button" :class="page === 'general' ? 'is-on' : ''" @click="page = 'general'">通用</button>
        <button type="button" :class="page === 'look' ? 'is-on' : ''" @click="page = 'look'">外观</button>
        <button type="button" :class="page === 'theme' ? 'is-on' : ''" @click="page = 'theme'">主题</button>
        <button type="button" :class="page === 'ai' ? 'is-on' : ''" @click="page = 'ai'">AI</button>
        <button type="button" :class="page === 'remote' ? 'is-on' : ''" @click="page = 'remote'">远程</button>
        <button type="button" :class="page === 'backup' ? 'is-on' : ''" @click="page = 'backup'">备份</button>
        <button type="button" :class="page === 'privacy' ? 'is-on' : ''" @click="page = 'privacy'">隐私</button>
      </nav>
      <div class="wv-settings-main">
      <div class="mb-6 flex items-start justify-between gap-4">
        <h2 class="wv-settings-title">设置</h2>
        <button type="button" class="wv-btn-ghost" @click="emit('close')">关闭</button>
      </div>
      <div v-if="page === 'general'" class="wv-card">
        <h3>开机自启</h3>
        <p class="wv-quiet">登录 Windows 时打开 Weaveverse。打包后的程序和这个开发目录会写成不同的启动命令。</p>
        <label class="mt-4 flex items-center gap-3 text-base font-semibold">
          <input type="checkbox" :checked="autostart" @change="toggleAutostart" />
          登录后自动打开
        </label>
        <p v-if="autostartNote" class="mt-3 text-sm text-moss">{{ autostartNote }}</p>
      </div>
      <div v-if="page === 'general'" class="wv-card">
        <h3>数据存储</h3>
        <p class="wv-quiet">笔记、书籍和图片都在这个文件夹里。更改后会先完整复制并核对，成功才改配置。</p>
        <p class="mt-3 break-all text-sm">{{ dataPath || '正在读取' }}</p>
        <button type="button" class="wv-btn wv-btn-primary mt-4" :disabled="dataBusy" @click="changeDataDir">
          {{ dataBusy ? '正在迁移' : '更改目录' }}
        </button>
        <p v-if="dataNote" class="mt-3 text-sm">{{ dataNote }}</p>
      </div>
      <div v-else-if="page === 'ai'" class="wv-card"><AiSettings /></div>
      <div v-else-if="page === 'remote'" class="wv-card"><RemotePanel /></div>
      <div v-else-if="page === 'backup'" class="wv-card"><BackupPanel @need-privacy="page = 'privacy'" /></div>
      <div v-else-if="page === 'privacy'" class="wv-card"><PrivacyPanel /></div>
      <ThemePanel v-else-if="page === 'theme'" :appearance="appearance" @change="emit('change', $event)" />
      <template v-else>
      <section class="wv-card">
      <h3>透明玻璃模式</h3>
      <p class="wv-quiet">窗口变成无边框。面板是磨砂玻璃，能看见桌面。打开或关掉都会重新打开窗口。</p>
      <label class="mt-4 flex items-center gap-3 text-base font-semibold">
        <input type="checkbox" :checked="appearance.glass" @change="setGlass" />
        使用透明玻璃
      </label>
      <p v-if="glassNote" class="mt-3 text-sm">{{ glassNote }}</p>
      </section>
      <section class="wv-card">
      <h3>背景不透明度</h3>
      <p class="wv-quiet">100% 时界面盖住背景，0% 只留界面底色。</p>
      <div class="mt-4 flex items-center gap-3">
        <input type="range" min="0" max="100" :value="opacityPercent" class="flex-1" @input="onOpacityInput" />
        <span class="w-12 text-right text-sm font-semibold">{{ opacityPercent }}%</span>
      </div>
      </section>
      <section class="wv-card">
      <h3>分组栏</h3>
      <div class="mt-3 flex flex-wrap gap-2">
        <button type="button" class="wv-choice" :class="appearance.bar === 'push' ? 'is-on' : ''" @click="setBar('push')">推栏</button>
        <button type="button" class="wv-choice" :class="appearance.bar === 'overlay' ? 'is-on' : ''" @click="setBar('overlay')">名字浮出</button>
        <button type="button" class="wv-choice" :class="appearance.bar === 'stack' ? 'is-on' : ''" @click="setBar('stack')">图标在上</button>
      </div>
      </section>
      <section class="wv-card">
      <h3>悬浮球</h3>
      <label class="mt-3 flex items-center gap-3 text-base font-semibold">
        <input type="checkbox" :checked="appearance.player_hidden" @change="setOrbHidden" />
        隐藏悬浮球
      </label>
      <p class="mt-4 text-sm font-semibold">位置</p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button type="button" class="wv-choice" :class="appearance.player === 'corner' || !appearance.player ? 'is-on' : ''" @click="setPlayer('corner')">右下角</button>
        <button type="button" class="wv-choice" :class="appearance.player === 'bottom' ? 'is-on' : ''" @click="setPlayer('bottom')">正下方</button>
        <button type="button" class="wv-choice" :class="appearance.player === 'side' ? 'is-on' : ''" @click="setPlayer('side')">右侧中间</button>
        <button type="button" class="wv-choice" :class="appearance.player === 'free' ? 'is-on' : ''" @click="emit('move-orb')">移动悬浮球</button>
      </div>
      <p class="mt-4 text-sm font-semibold">面板展开</p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button type="button" class="wv-choice" :class="!appearance.player_spread || appearance.player_spread === 'auto' ? 'is-on' : ''" @click="setSpread('auto')">自动</button>
        <button type="button" class="wv-choice" :class="appearance.player_spread === 'center' ? 'is-on' : ''" @click="setSpread('center')">强制从中间</button>
        <button type="button" class="wv-choice" :class="appearance.player_spread === 'side' ? 'is-on' : ''" @click="setSpread('side')">强制从一侧</button>
      </div>
      </section>
      <section class="wv-card">
      <h3>进度条</h3>
      <div class="mt-3 flex items-center gap-2">
        <button type="button" class="wv-choice" :class="appearance.progress_style !== 'gradient' ? 'is-on' : ''" @click="setProgressStyle('solid')">单色</button>
        <input type="color" :value="appearance.progress_color || '#3f6f57'" title="进度颜色" @change="setProgressColor" />
        <button type="button" class="wv-choice" :class="appearance.progress_style === 'gradient' ? 'is-on' : ''" @click="setProgressStyle('gradient')">彩色</button>
      </div>
      <label class="mt-4 flex items-center gap-3 text-base font-semibold">
        <input type="checkbox" :checked="appearance.low_power" @change="setLowPower" />
        低性能模式，不播视频背景
      </label>
      </section>
      <section class="wv-card">
      <h3>桌面背景</h3>
      <div class="mt-3 flex flex-wrap gap-2">
        <button type="button" class="wv-btn wv-btn-quiet" :disabled="busy === 'image'" @click="imageInput.click()">上传全局背景图</button>
        <button type="button" class="wv-btn-ghost" @click="clear('image', null)">清除</button>
        <button type="button" class="wv-btn wv-btn-quiet" :disabled="busy === 'video'" @click="videoInput.click()">上传 MP4 背景</button>
        <button type="button" class="wv-btn-ghost" @click="clear('video', null)">清除视频</button>
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
        <button type="button" class="wv-btn wv-btn-quiet" :disabled="busy === 'image'" @click="groupInput.click()">上传「{{ groupName || '当前分组' }}」背景</button>
        <button type="button" class="wv-btn-ghost" @click="clear('image', groupId)">清除分组背景</button>
        <p v-if="groupFile" class="mt-2 text-xs text-ink/70">分组背景 {{ groupLabel }}</p>
        <img v-if="groupFile" :src="backgroundUrl(groupFile)" alt="" class="mt-2 h-20 w-full rounded object-cover" />
      </div>
      </section>
      <section class="wv-card">
      <h3>欢迎封面</h3>
      <p class="wv-quiet">
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
      <div class="mt-3 flex flex-wrap gap-2">
        <button type="button" class="wv-btn wv-btn-quiet" :disabled="busy === 'splash'" @click="splashInput.click()">替换封面</button>
        <button type="button" class="wv-btn-ghost" @click="resetSplash">恢复默认</button>
      </div>
      <p class="mt-4 text-sm font-semibold">播放时长</p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button
          v-for="seconds in SPLASH_SECONDS"
          :key="seconds"
          type="button"
          class="wv-choice"
          :class="(appearance.splash_duration || 2) === seconds ? 'is-on' : ''"
          @click="setSplashDuration(seconds)"
        >
          {{ seconds }} 秒
        </button>
      </div>
      <label class="mt-4 block text-sm font-semibold">
        底部标语
        <input v-model="captionDraft" class="wv-field mt-2" maxlength="40" @change="saveCaption" />
      </label>
      <label class="mt-3 flex items-center gap-2 text-sm text-ink/80">
        <input type="checkbox" :checked="appearance.splash_loop !== false" @change="setSplashLoop" />
        视频循环到时长结束
      </label>
      <p v-if="errorMessage" class="mt-3 text-xs text-ember">{{ errorMessage }}</p>
      <button type="button" class="wv-btn-ghost mt-4" @click="emit('open-guide')">再次显示使用说明</button>
      </section>
      </template>
      <section v-if="page === 'general'" class="wv-card wv-status">
        <h3>系统状态</h3>
        <p class="wv-quiet">构建时间如果停在旧的时刻，窗口还在用旧的前端包。</p>
        <dl>
          <div><dt>前端构建时间</dt><dd>{{ builtLabel }}</dd></div>
          <div><dt>后端版本</dt><dd>{{ systemStatus.version || '…' }}</dd></div>
          <div><dt>数据库版本</dt><dd>{{ systemStatus.revision || '…' }}</dd></div>
        </dl>
        <p v-if="systemNote" class="mt-3 text-sm">{{ systemNote }}</p>
      </section>
      <input ref="imageInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif" @change="onImage" />
      <input ref="videoInput" class="wv-file-input" type="file" accept="video/mp4,.mp4" @change="onVideo" />
      <input ref="groupInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif" @change="onGroupImage" />
      <input ref="splashInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,video/webm,video/mp4,application/json,.png,.jpg,.jpeg,.webp,.gif,.webm,.mp4,.json,.lottie" @change="onSplash" />
      <input ref="themeInput" class="wv-file-input" type="file" accept=".wvtheme,.wvpack,.json,application/json,application/zip" @change="onThemeFile" />
      </div>
    </div>
  </div>
</template>
