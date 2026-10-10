<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  attachmentUrl,
  createAlbum,
  deleteAlbum,
  deletePhotos,
  listAlbums,
  listPhotos,
  movePhotos,
  renamePhoto,
  saveAttachmentLocal,
  unlockAlbum,
  updateAlbum,
  uploadPhoto,
} from '../api/client'
import NavIcon from './NavIcon.vue'
import { showToast } from '../toast'

defineProps({
  title: {
    type: String,
    default: '图片库',
  },
  icon: {
    type: String,
    default: '🖼',
  },
  noticeMessage: {
    type: String,
    default: '',
  },
})

const albums = ref([])
const photos = ref([])
const tab = ref('all')
const layout = ref('grid')
const loading = ref(true)
const uploading = ref(false)
const errorMessage = ref('')
const selected = ref([])
const selecting = ref(false)
const previewIndex = ref(-1)
const password = ref('')
const locked = ref(false)
const albumForm = ref(false)
const albumName = ref('')
const albumPrivate = ref(false)
const albumPassword = ref('')
const renameDraft = ref('')
const moveTarget = ref('none')
const aspects = ref({})
const frame = ref(null)
const frameWidth = ref(720)
const fileInput = ref(null)
let holdTimer = null
let frameObserver = null

const activeAlbum = computed(() => albums.value.find((album) => album.id === tab.value) || null)
const preview = computed(() => photos.value[previewIndex.value] || null)

function labelOf(photo) {
  return photo?.display_name || photo?.note || photo?.filename || ''
}

function saveName(photo) {
  const ext = String(photo.filename || '').match(/\.[a-z0-9]+$/i)?.[0] || ''
  const raw = labelOf(photo)
  if (ext && !raw.toLowerCase().endsWith(ext.toLowerCase())) {
    return `${raw}${ext}`
  }
  return raw
}

const flowRows = computed(() => {
  const width = Math.max(240, frameWidth.value)
  const gap = 8
  const target = 180
  const rows = []
  let row = []
  let sum = 0
  function push(force) {
    if (!row.length) {
      return
    }
    const gaps = gap * Math.max(0, row.length - 1)
    let height = (width - gaps) / Math.max(sum, 0.01)
    if (force) {
      height = Math.min(height, target)
    }
    rows.push(
      row.map((item) => ({
        photo: item.photo,
        width: Math.max(72, height * item.aspect),
        height,
      })),
    )
    row = []
    sum = 0
  }
  photos.value.forEach((photo) => {
    const aspect = aspects.value[photo.id] || 1
    row.push({ photo, aspect })
    sum += aspect
    const height = (width - gap * (row.length - 1)) / sum
    if (height <= target) {
      push(false)
    }
  })
  push(true)
  return rows
})

async function loadAlbums() {
  albums.value = await listAlbums()
}

async function loadPhotos() {
  loading.value = true
  errorMessage.value = ''
  const album = activeAlbum.value
  if (album?.is_private && !password.value) {
    photos.value = []
    locked.value = true
    loading.value = false
    return
  }
  locked.value = false
  try {
    photos.value = await listPhotos(tab.value === 'all' ? null : tab.value, password.value)
  } catch (error) {
    photos.value = []
    if (album?.is_private) {
      locked.value = true
      password.value = ''
      showToast(error.message || '需要密码')
    } else {
      errorMessage.value = error.message || '无法加载图片库'
    }
  } finally {
    loading.value = false
  }
}

async function refresh() {
  try {
    await loadAlbums()
    await loadPhotos()
  } catch (error) {
    errorMessage.value = error.message || '无法加载图片库'
    loading.value = false
  }
}

function chooseTab(next) {
  if (next === tab.value) {
    return
  }
  password.value = ''
  selected.value = []
  previewIndex.value = -1
  tab.value = next
}

watch(tab, () => {
  loadPhotos()
})

watch(preview, (photo) => {
  renameDraft.value = photo ? labelOf(photo) : ''
})

function rememberAspect(photo, event) {
  const img = event.target
  if (!img?.naturalWidth || !img?.naturalHeight) {
    return
  }
  aspects.value = { ...aspects.value, [photo.id]: img.naturalWidth / img.naturalHeight }
}

function isSelected(photo) {
  return selected.value.includes(photo.id)
}

function toggleSelected(photo) {
  selected.value = isSelected(photo)
    ? selected.value.filter((id) => id !== photo.id)
    : [...selected.value, photo.id]
}

function openPhoto(photo, event) {
  if (selecting.value || event?.ctrlKey || event?.metaKey) {
    selecting.value = true
    toggleSelected(photo)
    return
  }
  previewIndex.value = photos.value.findIndex((item) => item.id === photo.id)
}

function pressStart(photo) {
  clearTimeout(holdTimer)
  holdTimer = setTimeout(() => {
    selecting.value = true
    if (!isSelected(photo)) {
      toggleSelected(photo)
    }
  }, 450)
}

function pressEnd() {
  clearTimeout(holdTimer)
}

async function onFileChange(event) {
  const files = [...(event.target.files || [])]
  event.target.value = ''
  if (!files.length) {
    return
  }
  uploading.value = true
  errorMessage.value = ''
  const albumId = tab.value === 'all' ? null : tab.value
  try {
    for (const file of files) {
      await uploadPhoto(file, albumId, password.value)
    }
    await loadPhotos()
  } catch (error) {
    errorMessage.value = error.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function submitPassword() {
  if (!activeAlbum.value) {
    return
  }
  try {
    await unlockAlbum(activeAlbum.value.id, password.value)
    locked.value = false
    await loadPhotos()
  } catch (error) {
    password.value = ''
    showToast(error.message || '密码不对')
  }
}

async function makeAlbum() {
  const name = albumName.value.trim()
  if (!name) {
    return
  }
  if (albumPrivate.value && albumPassword.value.trim().length < 4) {
    showToast('隐私相册密码至少 4 位')
    return
  }
  try {
    const created = await createAlbum(name, albumPrivate.value, albumPassword.value.trim())
    albumForm.value = false
    albumName.value = ''
    albumPrivate.value = false
    albumPassword.value = ''
    await loadAlbums()
    chooseTab(created.id)
  } catch (error) {
    showToast(error.message || '相册没建成')
  }
}

async function renameAlbum() {
  if (!activeAlbum.value) {
    return
  }
  const name = window.prompt('相册名称', activeAlbum.value.name)
  if (!name || !name.trim() || name.trim() === activeAlbum.value.name) {
    return
  }
  await updateAlbum(activeAlbum.value.id, { name: name.trim() })
  await loadAlbums()
}

async function markPrivate() {
  if (!activeAlbum.value) {
    return
  }
  const next = window.prompt(activeAlbum.value.is_private ? '重设隐私密码' : '设置隐私密码（至少 4 位）')
  if (!next || next.trim().length < 4) {
    showToast('密码至少 4 位')
    return
  }
  await updateAlbum(activeAlbum.value.id, { is_private: true, password: next.trim() })
  password.value = ''
  await loadAlbums()
  await loadPhotos()
}

async function clearPrivate() {
  if (!activeAlbum.value) {
    return
  }
  await updateAlbum(activeAlbum.value.id, { is_private: false })
  password.value = ''
  await loadAlbums()
  await loadPhotos()
}

async function removeAlbum() {
  if (!activeAlbum.value) {
    return
  }
  if (!window.confirm(`删除相册「${activeAlbum.value.name}」？图片会回到未分类，文件还在。`)) {
    return
  }
  await deleteAlbum(activeAlbum.value.id)
  tab.value = 'all'
  password.value = ''
  await refresh()
}

async function saveCurrent() {
  const photo = preview.value
  if (!photo) {
    return
  }
  try {
    await saveAttachmentLocal(photo.filename, saveName(photo))
  } catch (error) {
    showToast(error.message || '保存失败')
  }
}

async function applyRename() {
  const photo = preview.value
  const name = renameDraft.value.trim()
  if (!photo || !name) {
    return
  }
  const updated = await renamePhoto(photo.id, name)
  photos.value = photos.value.map((item) => (item.id === updated.id ? updated : item))
  showToast('已改名')
}

async function removeSelected() {
  if (!selected.value.length) {
    return
  }
  if (!window.confirm(`从图片库移除 ${selected.value.length} 张？原文件会留着。`)) {
    return
  }
  await deletePhotos(selected.value)
  selected.value = []
  previewIndex.value = -1
  await loadPhotos()
}

async function moveSelected() {
  if (!selected.value.length || moveTarget.value === 'none') {
    return
  }
  const albumId = moveTarget.value === 'loose' ? null : Number(moveTarget.value)
  const album = albums.value.find((item) => item.id === albumId)
  let secret = ''
  if (album?.is_private) {
    secret = window.prompt(`「${album.name}」的密码`) || ''
    if (secret.length < 4) {
      showToast('需要密码')
      return
    }
  }
  try {
    await movePhotos(selected.value, albumId, secret)
    selected.value = []
    moveTarget.value = 'none'
    await loadPhotos()
  } catch (error) {
    showToast(error.message || '移动失败')
  }
}

function onKey(event) {
  if (previewIndex.value < 0) {
    return
  }
  if (event.key === 'Escape') {
    previewIndex.value = -1
  } else if (event.key === 'ArrowRight') {
    previewIndex.value = Math.min(photos.value.length - 1, previewIndex.value + 1)
  } else if (event.key === 'ArrowLeft') {
    previewIndex.value = Math.max(0, previewIndex.value - 1)
  }
}

watch(frame, (node) => {
  frameObserver?.disconnect()
  if (!node) {
    return
  }
  frameObserver = new ResizeObserver(() => {
    frameWidth.value = node.clientWidth || 720
  })
  frameObserver.observe(node)
  frameWidth.value = node.clientWidth || 720
})

onMounted(() => {
  window.addEventListener('keydown', onKey)
  refresh()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  frameObserver?.disconnect()
  clearTimeout(holdTimer)
})
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-8 py-8">
    <div class="mx-auto flex w-full max-w-6xl flex-col">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="flex items-center gap-4">
          <NavIcon :icon="icon" box="h-14 w-14 bg-dawn text-2xl shadow-sm" />
          <div>
            <p class="text-sm font-semibold uppercase tracking-[0.28em] text-aurora">Photos</p>
            <h2 class="mt-1 text-4xl font-semibold text-ink">{{ title }}</h2>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button type="button" class="h-10 rounded-md px-3 text-sm" :class="layout === 'grid' ? 'bg-moss text-white' : 'bg-white text-ink/70'" @click="layout = 'grid'">网格</button>
          <button type="button" class="h-10 rounded-md px-3 text-sm" :class="layout === 'flow' ? 'bg-moss text-white' : 'bg-white text-ink/70'" @click="layout = 'flow'">自适应</button>
          <button type="button" class="h-10 rounded-md px-3 text-sm" :class="layout === 'list' ? 'bg-moss text-white' : 'bg-white text-ink/70'" @click="layout = 'list'">列表</button>
          <button type="button" class="h-10 rounded-md px-3 text-sm" :class="selecting ? 'bg-ink text-white' : 'bg-white text-ink/70'" @click="selecting = !selecting">{{ selecting ? '完成' : '选择' }}</button>
          <button type="button" class="h-11 rounded-md bg-moss px-5 text-sm font-semibold text-white disabled:bg-ink/30" :disabled="uploading || locked" @click="fileInput.click()">
            {{ uploading ? '上传中...' : '上传' }}
          </button>
          <input ref="fileInput" class="hidden" type="file" accept="image/png,image/jpeg,image/gif,image/webp" multiple @change="onFileChange" />
        </div>
      </div>

      <div class="mt-5 flex gap-2 overflow-x-auto pb-1">
        <button type="button" class="h-8 shrink-0 rounded-full px-3 text-xs" :class="tab === 'all' ? 'bg-ink text-white' : 'bg-white text-ink/70'" @click="chooseTab('all')">全部</button>
        <button
          v-for="album in albums"
          :key="album.id"
          type="button"
          class="h-8 shrink-0 rounded-full px-3 text-xs"
          :class="tab === album.id ? 'bg-ink text-white' : 'bg-white text-ink/70'"
          @click="chooseTab(album.id)"
        >
          {{ album.is_private ? '🔒 ' : '' }}{{ album.name }}
        </button>
        <button type="button" class="h-8 shrink-0 rounded-full bg-white px-3 text-xs text-moss" @click="albumForm = !albumForm">新建相册</button>
      </div>

      <form v-if="albumForm" class="mt-3 flex flex-wrap items-center gap-2" @submit.prevent="makeAlbum">
        <input v-model="albumName" class="h-9 rounded border border-black/10 px-2 text-sm outline-none" maxlength="40" placeholder="相册名称" />
        <label class="flex items-center gap-1 text-xs text-ink/70">
          <input v-model="albumPrivate" type="checkbox" />
          隐私
        </label>
        <input v-if="albumPrivate" v-model="albumPassword" type="password" class="h-9 rounded border border-black/10 px-2 text-sm outline-none" placeholder="密码至少 4 位" />
        <button type="submit" class="h-9 rounded bg-ink px-3 text-xs text-white">创建</button>
      </form>

      <div v-if="activeAlbum" class="mt-3 flex flex-wrap gap-2 text-xs">
        <button type="button" class="rounded bg-white px-2 py-1" @click="renameAlbum">改相册名</button>
        <button type="button" class="rounded bg-white px-2 py-1" @click="markPrivate">{{ activeAlbum.is_private ? '重设密码' : '设为隐私' }}</button>
        <button v-if="activeAlbum.is_private" type="button" class="rounded bg-white px-2 py-1" @click="clearPrivate">取消隐私</button>
        <button type="button" class="rounded px-2 py-1 text-ember" @click="removeAlbum">删除相册</button>
      </div>

      <div v-if="selected.length" class="mt-3 flex flex-wrap items-center gap-2 rounded-md bg-white px-3 py-2 text-sm">
        <span>已选 {{ selected.length }} 张</span>
        <button type="button" class="rounded bg-ember px-3 py-1 text-xs text-white" @click="removeSelected">删除</button>
        <select v-model="moveTarget" class="h-8 rounded border border-black/10 bg-white px-2 text-xs">
          <option value="none">移动到…</option>
          <option value="loose">未分类</option>
          <option v-for="album in albums" :key="album.id" :value="String(album.id)">{{ album.name }}</option>
        </select>
        <button type="button" class="rounded bg-ink px-3 py-1 text-xs text-white" @click="moveSelected">移动</button>
      </div>

      <p v-if="noticeMessage" class="mt-4 rounded-md border border-moss/25 bg-moss/10 px-4 py-3 text-sm text-moss">{{ noticeMessage }}</p>
      <p v-if="errorMessage" class="mt-4 text-sm text-ember">{{ errorMessage }}</p>

      <form v-if="locked" class="mt-8 flex max-w-sm flex-col gap-2" @submit.prevent="submitPassword">
        <p class="text-sm text-ink/70">这个相册已锁定</p>
        <input v-model="password" type="password" class="h-10 rounded border border-black/10 px-3 text-sm outline-none" placeholder="输入密码" />
        <button type="submit" class="h-10 rounded bg-ink text-sm text-white">打开</button>
      </form>

      <p v-else-if="loading" class="mt-8 text-sm text-ink/60">正在加载图片库...</p>
      <p v-else-if="!photos.length" class="mt-10 text-lg text-ink/70">暂无图片</p>

      <div v-else ref="frame" class="mt-6">
        <div v-if="layout === 'grid'" class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
          <button
            v-for="photo in photos"
            :key="photo.id"
            type="button"
            class="relative overflow-hidden rounded-md bg-white text-left shadow-sm"
            :class="isSelected(photo) ? 'ring-2 ring-moss' : ''"
            @pointerdown="pressStart(photo)"
            @pointerup="pressEnd"
            @pointerleave="pressEnd"
            @click="openPhoto(photo, $event)"
          >
            <img :src="attachmentUrl(photo.filename)" :alt="labelOf(photo)" class="h-40 w-full object-cover" @load="rememberAspect(photo, $event)" />
            <span v-if="selecting" class="absolute right-2 top-2 grid h-5 w-5 place-items-center rounded-full bg-white text-[11px]">{{ isSelected(photo) ? '✓' : '' }}</span>
            <p class="truncate px-3 py-2 text-xs text-ink/55">{{ labelOf(photo) }}</p>
          </button>
        </div>

        <div v-else-if="layout === 'flow'" class="flex flex-col gap-2">
          <div v-for="(row, rowIndex) in flowRows" :key="rowIndex" class="flex gap-2">
            <button
              v-for="tile in row"
              :key="tile.photo.id"
              type="button"
              class="relative overflow-hidden rounded-md bg-black/5"
              :class="isSelected(tile.photo) ? 'ring-2 ring-moss' : ''"
              :style="{ width: `${tile.width}px`, height: `${tile.height}px` }"
              @pointerdown="pressStart(tile.photo)"
              @pointerup="pressEnd"
              @pointerleave="pressEnd"
              @click="openPhoto(tile.photo, $event)"
            >
              <img :src="attachmentUrl(tile.photo.filename)" alt="" class="h-full w-full object-cover" @load="rememberAspect(tile.photo, $event)" />
            </button>
          </div>
        </div>

        <div v-else class="divide-y divide-black/5 overflow-hidden rounded-md bg-white shadow-sm">
          <button
            v-for="photo in photos"
            :key="photo.id"
            type="button"
            class="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-black/5"
            :class="isSelected(photo) ? 'bg-moss/10' : ''"
            @click="openPhoto(photo, $event)"
          >
            <img :src="attachmentUrl(photo.filename)" alt="" class="h-12 w-12 shrink-0 rounded object-cover" @load="rememberAspect(photo, $event)" />
            <span class="min-w-0 flex-1 truncate text-sm">{{ labelOf(photo) }}</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="preview" class="fixed inset-0 z-50 flex flex-col bg-black/90" @click.self="previewIndex = -1">
      <img :src="attachmentUrl(preview.filename)" :alt="labelOf(preview)" class="min-h-0 w-full flex-1 object-contain" />
      <div class="flex flex-wrap items-center gap-2 bg-black/70 px-4 py-3 text-white">
        <input v-model="renameDraft" class="h-9 min-w-0 flex-1 rounded bg-white/10 px-2 text-sm outline-none" @keydown.enter.prevent="applyRename" />
        <button type="button" class="h-9 rounded bg-white/15 px-3 text-xs" @click="applyRename">改名</button>
        <button type="button" class="h-9 rounded bg-white px-3 text-xs text-ink" @click="saveCurrent">保存到本地</button>
        <button type="button" class="h-9 rounded px-3 text-xs" @click="previewIndex = Math.max(0, previewIndex - 1)">上一张</button>
        <button type="button" class="h-9 rounded px-3 text-xs" @click="previewIndex = Math.min(photos.length - 1, previewIndex + 1)">下一张</button>
        <button type="button" class="h-9 rounded px-3 text-xs" @click="previewIndex = -1">关闭</button>
      </div>
    </div>
  </div>
</template>
