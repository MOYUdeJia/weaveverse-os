<script setup>
import { ref, watch } from 'vue'

import { attachmentUrl, deleteAttachment, uploadImage } from '../api/client'
import BlockShell from './BlockShell.vue'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'delete'])

const images = ref([])
const fileInput = ref(null)
const isUploading = ref(false)

watch(
  () => props.block,
  () => {
    images.value = (props.block.content?.images || []).map((item) => ({ ...item }))
  },
  { immediate: true, deep: true },
)

function persist(nextImages) {
  images.value = nextImages
  emit('save', { images: nextImages })
}

async function onFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    return
  }

  isUploading.value = true
  try {
    const result = await uploadImage(props.block.id, file)
    persist([...images.value, { filename: result.filename, caption: file.name }])
  } catch (error) {
    console.error('Image upload failed:', error)
    alert(error.message || '上传失败')
  } finally {
    isUploading.value = false
  }
}

async function removeImage(index) {
  const target = images.value[index]
  if (!window.confirm('确定删除这张图片吗？')) {
    return
  }
  try {
    if (target?.filename) {
      await deleteAttachment(target.filename)
    }
  } catch (error) {
    console.error('Failed to delete attachment:', error)
  }
  persist(images.value.filter((_, itemIndex) => itemIndex !== index))
}

function confirmDelete() {
  if (window.confirm('确定删除这个画廊区块吗？')) {
    emit('delete')
  }
}
</script>

<template>
  <BlockShell title="画廊" :block-id="block.id" @delete="confirmDelete">
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <figure v-for="(image, index) in images" :key="image.filename" class="group relative overflow-hidden rounded-md bg-dawn">
        <img :src="attachmentUrl(image.filename)" :alt="image.caption" class="h-32 w-full object-cover" />
        <figcaption class="truncate px-2 py-1 text-xs text-ink/60">{{ image.caption }}</figcaption>
        <button
          type="button"
          class="absolute right-2 top-2 hidden h-7 w-7 place-items-center rounded-md bg-black/60 text-white group-hover:grid"
          @click="removeImage(index)"
        >
          ×
        </button>
      </figure>
    </div>

    <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/gif,image/webp" class="hidden" @change="onFileChange" />
    <button
      type="button"
      class="mt-2 h-8 rounded-md border border-dashed border-moss/40 px-3 text-sm font-medium text-moss hover:bg-moss/10"
      :disabled="isUploading"
      @click="fileInput?.click()"
    >
      {{ isUploading ? '上传中...' : '+ 上传图片' }}
    </button>
  </BlockShell>
</template>
