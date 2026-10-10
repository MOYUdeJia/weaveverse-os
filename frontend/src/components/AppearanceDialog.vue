<script setup>
import { computed, ref, watch } from 'vue'

import { backgroundUrl, clearBackground, updateAppearance, uploadBackground } from '../api/client'
import AiSettings from './AiSettings.vue'

const THEMES = [
  { id: 'warm', label: '暖白', swatch: '#f4efe7' },
  { id: 'mint', label: '薄荷', swatch: '#e5f4ee' },
  { id: 'sky', label: '天蓝', swatch: '#e7f1fb' },
  { id: 'sakura', label: '樱粉', swatch: '#fbeaf0' },
  { id: 'ash', label: '灰调', swatch: '#eceeef' },
]

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

const emit = defineEmits(['close', 'change', 'open-guide'])

const page = ref('look')
const busy = ref('')
const busyName = ref('')
const errorMessage = ref('')
const statusMessage = ref('')
const imageInput = ref(null)
const videoInput = ref(null)
const groupInput = ref(null)

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

watch(
  () => props.open,
  () => {
    errorMessage.value = ''
    statusMessage.value = ''
    busyName.value = ''
  },
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

async function setLowPower(event) {
  emit('change', await updateAppearance({ low_power: event.target.checked }))
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

function onGroupImage(event) {
  if (props.groupId == null) {
    return
  }
  takeFile(event, 'image', props.groupId)
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
  <div v-if="open" class="fixed inset-0 z-[70] grid place-items-center bg-black/40 px-4" @click.self="emit('close')">
    <div class="wv-surface max-h-[86vh] w-full max-w-lg overflow-y-auto rounded-md p-5 shadow-2xl">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-ink">设置</h2>
        <button type="button" class="text-ink/50" @click="emit('close')">×</button>
      </div>
      <div class="mb-4 flex gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'look' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'look'">外观</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="page === 'ai' ? 'bg-moss text-white' : 'wv-chip'" @click="page = 'ai'">AI</button>
      </div>
      <AiSettings v-if="page === 'ai'" />
      <template v-else>
      <p class="text-xs text-ink/45">主题</p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button
          v-for="theme in THEMES"
          :key="theme.id"
          type="button"
          class="h-9 rounded px-3 text-xs"
          :class="appearance.theme === theme.id ? 'bg-ink text-white' : 'bg-white text-ink'"
          @click="setTheme(theme.id)"
        >
          <span class="mr-1 inline-block h-3 w-3 rounded-full border border-black/10" :style="{ background: theme.swatch }" />
          {{ theme.label }}
        </button>
      </div>
      <p class="mt-4 text-xs text-ink/45">分组栏</p>
      <div class="mt-2 flex gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.bar === 'push' ? 'bg-ink text-white' : 'bg-white'" @click="setBar('push')">推栏</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.bar === 'overlay' ? 'bg-ink text-white' : 'bg-white'" @click="setBar('overlay')">名字浮出</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.bar === 'stack' ? 'bg-ink text-white' : 'bg-white'" @click="setBar('stack')">图标在上</button>
      </div>
      <p class="mt-4 text-xs text-ink/45">播放器位置</p>
      <div class="mt-2 flex gap-2">
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player === 'top' ? 'bg-ink text-white' : 'bg-white'" @click="setPlayer('top')">上方</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player === 'bottom' || !appearance.player ? 'bg-ink text-white' : 'bg-white'" @click="setPlayer('bottom')">下方</button>
        <button type="button" class="h-8 rounded px-3 text-xs" :class="appearance.player === 'corner' ? 'bg-ink text-white' : 'bg-white'" @click="setPlayer('corner')">右下</button>
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
      <p v-if="errorMessage" class="mt-3 text-xs text-ember">{{ errorMessage }}</p>
      <button type="button" class="mt-5 text-sm text-moss" @click="emit('open-guide')">再看一次使用说明</button>
      </template>
      <input ref="imageInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif" @change="onImage" />
      <input ref="videoInput" class="wv-file-input" type="file" accept="video/mp4,.mp4" @change="onVideo" />
      <input ref="groupInput" class="wv-file-input" type="file" accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif" @change="onGroupImage" />
    </div>
  </div>
</template>
