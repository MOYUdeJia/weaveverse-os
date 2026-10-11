<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import draggable from 'vuedraggable'

import {
  createVaultEntry,
  createVaultSection,
  deleteVaultEntry,
  deleteVaultSection,
  getPrivacy,
  listVaultEntries,
  listVaultSections,
  lockVault,
  pinVaultEntryTop,
  renameVaultSection,
  reorderVaultEntries,
  reorderVaultSections,
  setVaultPassword,
  unlockVault,
  updateVaultEntry,
} from '../api/client'
import { showMenu } from '../contextMenu'
import { openExternalLink } from '../openExternal'
import { showToast } from '../toast'
import NavIcon from './NavIcon.vue'

defineProps({
  title: { type: String, default: '密码管理器' },
  icon: { type: String, default: '🔒' },
})

const privacy = ref({ vault_set: false, vault_unlocked: false })
const sections = ref([])
const entries = ref([])
const query = ref('')
const tab = ref('all')
const shown = ref({})
const form = ref(null)
const passwordDraft = ref('')
const busy = ref(false)

const filtered = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return entries.value.filter((entry) => {
    if (tab.value !== 'all' && entry.section_id !== tab.value) {
      return false
    }
    if (!needle) {
      return true
    }
    return String(entry.name || '').toLowerCase().includes(needle)
  })
})

const cards = computed(() => {
  const grouped = tab.value === 'all' ? sections.value : sections.value.filter((section) => section.id === tab.value)
  return grouped.map((section) => ({
    ...section,
    items: filtered.value
      .filter((entry) => entry.section_id === section.id)
      .slice()
      .sort((a, b) => Number(b.pinned) - Number(a.pinned) || a.sort_order - b.sort_order || a.id - b.id),
  }))
})

async function refreshPrivacy() {
  privacy.value = await getPrivacy()
}

async function loadVault() {
  sections.value = await listVaultSections()
  entries.value = await listVaultEntries()
  if (!sections.value.length) {
    await createVaultSection('常用')
    sections.value = await listVaultSections()
  }
}

async function enterPage() {
  await refreshPrivacy()
  if (privacy.value.vault_unlocked) {
    await lockVault()
    await refreshPrivacy()
  }
}

async function submitPassword() {
  busy.value = true
  try {
    if (!privacy.value.vault_set) {
      await setVaultPassword(passwordDraft.value)
    } else {
      await unlockVault(passwordDraft.value)
    }
    passwordDraft.value = ''
    await refreshPrivacy()
    await loadVault()
  } catch (error) {
    showToast(error.message || '密码不对')
  } finally {
    busy.value = false
  }
}

function openUrl(entry) {
  const raw = String(entry.url || '').trim()
  if (!raw) {
    return
  }
  const href = /^[a-z][a-z0-9+.-]*:/i.test(raw) ? raw : `https://${raw}`
  openExternalLink(href)
}

async function copyText(text, label) {
  if (!text) {
    showToast(`没有${label}`)
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    showToast(`已复制${label}`)
  } catch {
    showToast('复制失败')
  }
}

function toggleShow(entry) {
  if (entry.locked) {
    showToast('这条已锁定')
    return
  }
  shown.value = { ...shown.value, [entry.id]: !shown.value[entry.id] }
}

async function persistSections() {
  await reorderVaultSections(sections.value.map((section) => section.id))
}

async function persistEntries(section) {
  const ids = cards.value.find((card) => card.id === section.id)?.items.map((item) => item.id) || []
  await reorderVaultEntries(section.id, ids)
  entries.value = await listVaultEntries()
}

async function addSection() {
  const name = window.prompt('分区名称', '新分区')
  if (!name || !name.trim()) {
    return
  }
  await createVaultSection(name.trim())
  sections.value = await listVaultSections()
}

async function renameSection(section) {
  const name = window.prompt('分区名称', section.name)
  if (!name || !name.trim()) {
    return
  }
  await renameVaultSection(section.id, name.trim())
  sections.value = await listVaultSections()
}

async function removeSection(section) {
  if (!window.confirm(`删除分区「${section.name}」以及里面的条目？`)) {
    return
  }
  await deleteVaultSection(section.id)
  if (tab.value === section.id) {
    tab.value = 'all'
  }
  await loadVault()
}

function startCreate() {
  const sectionId = tab.value === 'all' ? sections.value[0]?.id : tab.value
  if (!sectionId) {
    showToast('先建一个分区')
    return
  }
  form.value = {
    id: null,
    section_id: sectionId,
    name: '',
    url: '',
    username: '',
    password: '',
    note: '',
  }
}

function startEdit(entry) {
  form.value = {
    id: entry.id,
    section_id: entry.section_id,
    name: entry.name,
    url: entry.url,
    username: entry.username,
    password: entry.password,
    note: entry.note,
  }
}

async function saveForm() {
  if (!form.value?.name.trim()) {
    showToast('请填写命名')
    return
  }
  const payload = {
    section_id: form.value.section_id,
    name: form.value.name.trim(),
    url: form.value.url.trim(),
    username: form.value.username.trim(),
    password: form.value.password,
    note: form.value.note.trim(),
  }
  if (form.value.id) {
    await updateVaultEntry(form.value.id, payload)
  } else {
    await createVaultEntry(payload)
  }
  form.value = null
  await loadVault()
}

async function removeEntry(entry) {
  if (!window.confirm(`删除「${entry.name}」？`)) {
    return
  }
  await deleteVaultEntry(entry.id)
  await loadVault()
}

async function moveEntry(entry) {
  const names = sections.value.map((section) => `${section.id}: ${section.name}`).join('\n')
  const picked = window.prompt(`移到哪个分区？填写分区 id\n${names}`, String(entry.section_id))
  const sectionId = Number(picked)
  if (!sectionId || sectionId === entry.section_id) {
    return
  }
  await updateVaultEntry(entry.id, { section_id: sectionId })
  await loadVault()
}

function onMenu(event, entry) {
  showMenu(event, [
    { label: '一键置顶', onClick: async () => { await pinVaultEntryTop(entry.id); await loadVault() } },
    { label: entry.pinned ? '取消真置顶' : '真置顶', onClick: async () => { await updateVaultEntry(entry.id, { pinned: !entry.pinned }); await loadVault() } },
    { label: entry.locked ? '解锁' : '锁定', onClick: async () => { await updateVaultEntry(entry.id, { locked: !entry.locked }); shown.value = { ...shown.value, [entry.id]: false }; await loadVault() } },
    { label: shown.value[entry.id] ? '隐藏密码' : '显示密码', disabled: entry.locked, onClick: () => toggleShow(entry) },
    { label: '移动', onClick: () => moveEntry(entry) },
    { label: '编辑', onClick: () => startEdit(entry) },
    { label: '删除', onClick: () => removeEntry(entry) },
  ])
}

onMounted(() => {
  enterPage().catch((error) => showToast(error.message || '打不开密码库'))
})

onBeforeUnmount(() => {
  lockVault().catch(() => {})
  passwordDraft.value = ''
})
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-8 py-8">
    <div class="mx-auto flex w-full max-w-5xl flex-col">
      <div class="flex items-center gap-4">
        <NavIcon :icon="icon" box="h-14 w-14 bg-dawn text-2xl shadow-sm" />
        <div>
          <p class="text-sm font-semibold uppercase tracking-[0.28em] text-aurora">Vault</p>
          <h2 class="mt-1 text-4xl font-semibold text-ink">{{ title }}</h2>
        </div>
      </div>

      <form v-if="!privacy.vault_unlocked" class="mt-8 flex max-w-sm flex-col gap-2" @submit.prevent="submitPassword">
        <p class="text-sm text-ink/70">{{ privacy.vault_set ? '输入主密码解锁' : '第一次使用，设置主密码（至少 12 位）' }}</p>
        <p class="text-xs text-ink/45">忘记无法恢复。主密码只在本会话有效，关掉应用要重输。</p>
        <input v-model="passwordDraft" type="password" autocomplete="current-password" class="wv-surface h-10 rounded border border-black/10 px-3 text-sm outline-none" :placeholder="privacy.vault_set ? '主密码' : '至少 12 位'" />
        <button type="submit" class="h-10 rounded bg-ink text-sm text-white" :disabled="busy">{{ privacy.vault_set ? '解锁' : '设置并进入' }}</button>
      </form>

      <template v-else>
        <div class="mt-6 flex flex-wrap items-center gap-2">
          <button type="button" class="h-8 rounded-full px-3 text-xs" :class="tab === 'all' ? 'bg-moss text-white' : 'wv-chip'" @click="tab = 'all'">全部</button>
          <draggable v-model="sections" item-key="id" class="flex flex-wrap gap-2" :animation="160" @end="persistSections">
            <template #item="{ element }">
              <button type="button" class="h-8 cursor-grab rounded-full px-3 text-xs active:cursor-grabbing" :class="tab === element.id ? 'bg-moss text-white' : 'wv-chip'" @click="tab = element.id">
                {{ element.name }}
              </button>
            </template>
          </draggable>
          <button type="button" class="h-8 rounded-full border border-dashed border-moss px-3 text-xs text-moss" @click="addSection">+ 分区</button>
          <input v-model="query" type="text" class="ml-auto h-8 w-40 rounded border border-black/10 bg-white px-2 text-xs outline-none" placeholder="搜索命名" />
          <button type="button" class="h-8 rounded bg-moss px-3 text-xs text-white" @click="startCreate">新建条目</button>
        </div>

        <div v-if="form" class="wv-surface mt-4 grid gap-2 rounded-md p-4 text-sm">
          <input v-model="form.name" class="h-9 rounded border border-black/10 px-2 outline-none" placeholder="命名" />
          <input v-model="form.url" class="h-9 rounded border border-black/10 px-2 outline-none" placeholder="网址（可选）" />
          <input v-model="form.username" class="h-9 rounded border border-black/10 px-2 outline-none" placeholder="账号" />
          <input v-model="form.password" type="password" autocomplete="new-password" class="h-9 rounded border border-black/10 px-2 outline-none" placeholder="密码" />
          <textarea v-model="form.note" class="min-h-[4rem] rounded border border-black/10 px-2 py-1 outline-none" placeholder="备注 / 简介" />
          <select v-model.number="form.section_id" class="h-9 rounded border border-black/10 px-2 outline-none">
            <option v-for="section in sections" :key="section.id" :value="section.id">{{ section.name }}</option>
          </select>
          <div class="flex gap-2">
            <button type="button" class="h-8 rounded bg-moss px-3 text-xs text-white" @click="saveForm">保存</button>
            <button type="button" class="h-8 rounded px-3 text-xs text-ink/50" @click="form = null">取消</button>
          </div>
        </div>

        <draggable v-model="sections" item-key="id" handle=".section-handle" class="mt-4" :animation="160" @end="persistSections">
          <template #item="{ element: section }">
            <section v-show="tab === 'all' || tab === section.id" class="wv-surface mb-4 rounded-md p-3">
              <div class="mb-2 flex items-center gap-2">
                <button type="button" class="section-handle cursor-grab text-ink/35" title="拖动分区">⋮⋮</button>
                <h3 class="flex-1 text-sm font-semibold">{{ section.name }}</h3>
                <button type="button" class="text-xs text-ink/45" @click="renameSection(section)">改名</button>
                <button type="button" class="text-xs text-ember" @click="removeSection(section)">删除分区</button>
              </div>
              <draggable
                :model-value="cards.find((card) => card.id === section.id)?.items || []"
                item-key="id"
                handle=".item-handle"
                class="divide-y divide-black/[0.05]"
                :animation="160"
                @update:model-value="(items) => { entries = entries.filter((entry) => entry.section_id !== section.id).concat(items); persistEntries(section) }"
              >
                <template #item="{ element: entry }">
                  <div class="py-2" @contextmenu="onMenu($event, entry)">
                    <div class="flex flex-wrap items-center gap-2 text-sm">
                      <button type="button" class="item-handle cursor-grab text-ink/30">⋮</button>
                      <span v-if="entry.pinned" class="text-[10px] text-moss">置顶</span>
                      <span v-if="entry.locked" class="text-[10px] text-ink/40">锁</span>
                      <button
                        v-if="entry.url"
                        type="button"
                        class="min-w-0 truncate font-medium text-aurora underline"
                        @click="openUrl(entry)"
                      >
                        {{ entry.name }}
                      </button>
                      <span v-else class="min-w-0 truncate font-medium text-ink">{{ entry.name }}</span>
                      <span class="truncate text-xs text-ink/50">{{ entry.username }}</span>
                      <button type="button" class="text-xs text-ink/45" @click="copyText(entry.username, '账号')">复制账号</button>
                      <span class="font-mono text-xs">{{ entry.locked || !shown[entry.id] ? '••••••' : entry.password || '（空）' }}</span>
                      <button type="button" class="text-xs text-ink/45" :disabled="entry.locked" @click="toggleShow(entry)">{{ shown[entry.id] ? '隐藏' : '显示' }}</button>
                      <button type="button" class="text-xs text-ink/45" :disabled="entry.locked" @click="copyText(entry.password, '密码')">复制密码</button>
                      <button type="button" class="text-xs text-ink/45" @click="startEdit(entry)">编辑</button>
                      <button type="button" class="text-xs text-ember" @click="removeEntry(entry)">删除</button>
                    </div>
                    <p v-if="entry.note" class="ml-6 mt-0.5 text-xs text-ink/45">{{ entry.note }}</p>
                  </div>
                </template>
              </draggable>
              <p v-if="!(cards.find((card) => card.id === section.id)?.items || []).length" class="py-3 text-xs text-ink/40">这个分区还没有条目</p>
            </section>
          </template>
        </draggable>
      </template>
    </div>
  </div>
</template>
