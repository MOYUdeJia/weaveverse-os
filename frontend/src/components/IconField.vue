<script setup>
import Cropper from 'cropperjs'
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import 'cropperjs/dist/cropper.css'

import { deleteIcon, uploadIcon } from '../api/client'
import NavIcon from './NavIcon.vue'

const ICONS = [
  '📚', '📝', '✅', '🖼️', '🔗', '📅', '📊', '🎯',
  '💡', '🔐', '🌱', '🎮', '🎵', '🏠', '⭐', '📌',
  '📁', '✨', '🌙', '🧭', '📖', '🗒️', '🎨', '💬',
]
const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])

const fileInput = ref(null)
const cropImage = ref(null)
const cropping = ref(false)
const previewUrl = ref('')
const zoomLevel = ref(0)
const imageUrl = ref('')
const uploaded = ref('')
const initial = ref(props.modelValue)
const keepUpload = ref(false)
let cropper = null
let minRatio = 1
let maxRatio = 1

function choose(icon) {
  emit('update:modelValue', icon)
}

function saved() {
  keepUpload.value = true
}

defineExpose({ saved })

watch(
  () => props.modelValue,
  (value) => {
    if (!uploaded.value || uploaded.value === value || uploaded.value === initial.value) {
      return
    }
    const stale = uploaded.value
    uploaded.value = ''
    deleteIcon(stale).catch((error) => console.error('Failed to delete unused icon:', error))
  },
)

function coverRatio() {
  const box = cropper.getCropBoxData()
  const image = cropper.getImageData()
  return Math.max(box.width / image.naturalWidth, box.height / image.naturalHeight)
}

function currentRatio() {
  const image = cropper.getImageData()
  return image.width / image.naturalWidth
}

function zoomAtCenter(ratio) {
  const box = cropper.getCropBoxData()
  cropper.zoomTo(ratio, {
    x: box.left + box.width / 2,
    y: box.top + box.height / 2,
  })
}

function syncZoomLevel() {
  if (!cropper || maxRatio <= minRatio) {
    zoomLevel.value = 0
    return
  }
  const ratio = Math.min(maxRatio, Math.max(minRatio, currentRatio()))
  zoomLevel.value = (ratio - minRatio) / (maxRatio - minRatio)
}

function updatePreview() {
  if (!cropper) {
    return
  }
  const canvas = cropper.getCroppedCanvas({
    width: 64,
    height: 64,
    imageSmoothingEnabled: true,
    imageSmoothingQuality: 'high',
  })
  previewUrl.value = canvas ? canvas.toDataURL('image/png') : ''
  syncZoomLevel()
}

function startCropper() {
  cropper?.destroy()
  cropper = new Cropper(cropImage.value, {
    viewMode: 3,
    dragMode: 'move',
    aspectRatio: 1,
    autoCropArea: 1,
    background: false,
    guides: false,
    center: false,
    highlight: false,
    modal: false,
    cropBoxMovable: false,
    cropBoxResizable: false,
    toggleDragModeOnDblclick: false,
    zoomOnWheel: false,
    ready() {
      minRatio = coverRatio()
      maxRatio = Math.max(minRatio, 1)
      zoomAtCenter(minRatio)
      updatePreview()
    },
    crop() {
      updatePreview()
    },
  })
}

function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    return
  }
  if (!file.type.startsWith('image/')) {
    alert('请选择图片')
    return
  }
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
  }
  imageUrl.value = URL.createObjectURL(file)
  cropping.value = true
  nextTick(() => {
    if (cropImage.value?.complete) {
      startCropper()
    }
  })
}

function onWheel(event) {
  if (!cropper) {
    return
  }
  const step = event.deltaY < 0 ? 1.08 : 1 / 1.08
  const next = Math.min(maxRatio, Math.max(minRatio, currentRatio() * step))
  zoomAtCenter(next)
}

function onZoomInput(event) {
  if (!cropper) {
    return
  }
  const t = Number(event.target.value)
  zoomAtCenter(minRatio + (maxRatio - minRatio) * t)
}

function closeCrop() {
  cropper?.destroy()
  cropper = null
  cropping.value = false
  previewUrl.value = ''
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
    imageUrl.value = ''
  }
}

async function confirmCrop() {
  if (!cropper) {
    return
  }
  const canvas = cropper.getCroppedCanvas({
    width: 64,
    height: 64,
    imageSmoothingEnabled: true,
    imageSmoothingQuality: 'high',
  })
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
  if (!blob) {
    alert('裁剪失败')
    return
  }
  try {
    const result = await uploadIcon(blob)
    const previous = uploaded.value
    uploaded.value = result.icon
    emit('update:modelValue', result.icon)
    closeCrop()
    if (previous && previous !== result.icon && previous !== initial.value) {
      await deleteIcon(previous)
    }
  } catch (error) {
    console.error('Failed to upload icon:', error)
    alert(error.message || '上传图标失败')
  }
}

onBeforeUnmount(() => {
  cropper?.destroy()
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
  }
  if (!keepUpload.value && uploaded.value && uploaded.value !== initial.value) {
    deleteIcon(uploaded.value).catch((error) => console.error('Failed to delete unused icon:', error))
  }
})
</script>

<template>
  <div>
    <div class="mt-2 flex items-center gap-3">
      <NavIcon :icon="modelValue" box="h-11 w-11 bg-dawn text-xl" />
      <input
        id="nav-icon"
        :value="modelValue"
        class="h-11 min-w-0 flex-1 rounded-md border border-black/15 bg-white px-3 text-base outline-none focus:border-moss"
        maxlength="20"
        autocomplete="off"
        @input="emit('update:modelValue', $event.target.value)"
      />
    </div>
    <div class="mt-3 grid grid-cols-8 gap-2">
      <button
        v-for="icon in ICONS"
        :key="icon"
        type="button"
        class="grid h-9 place-items-center rounded-md bg-white text-lg hover:bg-moss/15"
        :class="modelValue === icon ? 'ring-2 ring-moss' : ''"
        @click="choose(icon)"
      >
        {{ icon }}
      </button>
    </div>
    <button type="button" class="mt-3 h-9 rounded-md px-3 text-sm font-medium text-moss hover:bg-moss/10" @click="fileInput?.click()">
      上传图片
    </button>
    <input ref="fileInput" class="hidden" type="file" accept="image/*" @change="onFile" />

    <div v-if="cropping" class="fixed inset-0 z-50 grid place-items-center bg-black/50 px-4">
      <div class="w-full max-w-md rounded-md bg-[#fcfaf5] p-5 shadow-2xl">
        <h3 class="text-lg font-semibold text-ink">裁剪图标</h3>
        <p class="mt-1 text-xs text-ink/50">图片始终盖住方框。拖动时边缘不能进框，缩放以方框中心为准。</p>
        <div class="mt-4 flex items-start justify-center gap-4">
          <div class="h-48 w-48 overflow-hidden rounded-md bg-white" @wheel.prevent="onWheel">
            <img ref="cropImage" :src="imageUrl" alt="" class="block max-w-none" @load="startCropper" />
          </div>
          <div class="text-center">
            <p class="text-xs text-ink/50">预览</p>
            <img v-if="previewUrl" :src="previewUrl" alt="" class="mt-2 h-16 w-16 rounded-md bg-white object-cover" />
          </div>
        </div>
        <input class="mt-4 w-full" type="range" min="0" max="1" step="0.01" :value="zoomLevel" @input="onZoomInput" />
        <div class="mt-4 flex justify-end gap-3">
          <button type="button" class="h-10 rounded-md px-4 text-sm text-ink/70 hover:bg-black/5" @click="closeCrop">取消</button>
          <button type="button" class="h-10 rounded-md bg-moss px-4 text-sm font-semibold text-white" @click="confirmCrop">使用</button>
        </div>
      </div>
    </div>
  </div>
</template>
