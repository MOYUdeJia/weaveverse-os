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
  pinVaultEntryTop,
  renameVaultSection,
  reorderVaultEntries,
  reorderVaultSections,
  resetSecurity,
  setVaultPassword,
  unlockVault,
  updateVaultEntry,
} from '../api/client'
import { showMenu } from '../contextMenu'
import { openExternalLink } from '../openExternal'
import { showToast } from '../toast'
import NavIcon from './NavIcon.vue'
import PasswordField from './PasswordField.vue'

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
const hintDraft = ref('')
const confirmDraft = ref('')
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
    await loadVault()
  }
}

async function submitPassword() {
  if (!privacy.value.vault_set) {
    if (passwordDraft.value.length < 8) {
      showToast('密码至少 8 位，建议 12 位')
      return
    }
    if (passwordDraft.value !== confirmDraft.value) {
      showToast('两次输入不一致')
      return
    }
  }
  busy.value = true
  try {
    if (!privacy.value.vault_set) {
      await setVaultPassword(passwordDraft.value, '', hintDraft.value)
    } else {
      await unlockVault(passwordDraft.value)
    }
    passwordDraft.value = ''
    confirmDraft.value = ''
    hintDraft.value = ''
    await refreshPrivacy()
    await loadVault()
  } catch (error) {
    showToast(String(error.message || '密码不对').replace(/^[^:]+:\s*/, ''))
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
    { label: '移到最前', onClick: async () => { await pinVaultEntryTop(entry.id); await loadVault() } },
    { label: entry.pinned ? '取消置顶' : '置顶', onClick: async () => { await updateVaultEntry(entry.id, { pinned: !entry.pinned }); await loadVault() } },
    { label: entry.locked ? '解锁' : '锁定', onClick: async () => { await updateVaultEntry(entry.id, { locked: !entry.locked }); shown.value = { ...shown.value, [entry.id]: false }; await loadVault() } },
    { label: shown.value[entry.id] ? '隐藏密码' : '显示密码', disabled: entry.locked, onClick: () => toggleShow(entry) },
    { label: '移动', onClick: () => moveEntry(entry) },
    { label: '编辑', onClick: () => startEdit(entry) },
    { label: '删除', onClick: () => removeEntry(entry) },
  ])
}

function onPrivacyLocked() {
  privacy.value = { ...privacy.value, vault_unlocked: false }
  entries.value = []
  sections.value = []
}

async function resetSecret() {
  const warning = '确定重置安全密码？密码库里的条目会全部删除，不能恢复。笔记、图片和其他数据还在。旧备份仍要用当时的密码打开。'
  if (!window.confirm(warning)) {
    return
  }
  try {
    privacy.value = await resetSecurity()
    onPrivacyLocked()
    showToast('已重置，请设置新的安全密码')
  } catch (error) {
    showToast(String(error.message || '没有重置').replace(/^[^:]+:\s*/, ''))
  }
}

onMounted(() => {
  window.addEventListener('wv-privacy-locked', onPrivacyLocked)
  enterPage().catch((error) => showToast(error.message || '打不开密码库'))
})

onBeforeUnmount(() => {
  window.removeEventListener('wv-privacy-locked', onPrivacyLocked)
  passwordDraft.value = ''
  confirmDraft.value = ''
  hintDraft.value = ''
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
        <p class="text-sm text-ink/70">{{ privacy.vault_set ? '输入安全密码解锁' : '第一次使用，设置安全密码' }}</p>
        <p class="text-xs text-ink/45">至少 8 位，建议 12 位。本会话解锁一次即可。改密码或关掉应用后要重输。</p>
        <p v-if="privacy.vault_set && privacy.security_hint" class="text-xs text-moss">提示：{{ privacy.security_hint }}</p>
        <PasswordField v-model="passwordDraft" :autocomplete="privacy.vault_set ? 'current-password' : 'new-password'" :placeholder="privacy.vault_set ? '安全密码' : '至少 8 位，建议 12 位'" />
        <PasswordField v-if="!privacy.vault_set" v-model="confirmDraft" autocomplete="new-password" placeholder="再输入一次" />
        <input v-if="!privacy.vault_set" v-model="hintDraft" type="text" maxlength="80" class="h-10 rounded border border-black/10 px-3 text-sm outline-none" placeholder="提示（可选，不是密码）" />
        <button type="submit" class="h-10 rounded bg-ink text-sm text-white" :disabled="busy">{{ privacy.vault_set ? '解锁' : '设置并进入' }}</button>
        <button v-if="privacy.vault_set" type="button" class="h-8 text-left text-xs text-ember" @click="resetSecret">忘记密码，重置</button>
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
          <PasswordField v-model="form.password" autocomplete="new-password" placeholder="密码" />
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
                <button type="button" class="text-xs text-ink/45" @click="renameSection(section)">重命名</button>
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
                  <div class="wv-vault-item group" @contextmenu="onMenu($event, entry)">
                    <div class="wv-vault-line">
                      <button type="button" class="item-handle cursor-grab text-ink/30" title="拖动">⋮</button>
                      <div class="wv-vault-namebox">
                        <span class="wv-vault-marks" aria-hidden="true">
                          <span v-if="entry.pinned" title="置顶">📌</span>
                          <span v-if="entry.locked" title="锁定">🔒</span>
                        </span>
                        <button
                          v-if="entry.url"
                          type="button"
                          class="wv-vault-name is-link"
                          :title="entry.name"
                          @click="openUrl(entry)"
                        >
                          {{ entry.name }}
                        </button>
                        <span v-else class="wv-vault-name" :title="entry.name">{{ entry.name }}</span>
                      </div>
                      <span class="wv-vault-user" :title="entry.username || '没有账号'">{{ entry.username || '—' }}</span>
                      <span class="wv-vault-secret" :title="shown[entry.id] && !entry.locked ? entry.password : '密码'">{{ entry.locked || !shown[entry.id] ? '••••••' : entry.password || '（空）' }}</span>
                      <div class="wv-vault-actions">
                      <button type="button" class="wv-vault-copy" title="复制账号" @click="copyText(entry.username, '账号')">
                        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M5 15V5h10" /></svg>
                      </button>
                      <button type="button" class="wv-vault-copy" title="复制密码" @click="copyText(entry.password, '密码')">
                        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="8" y="3" width="8" height="4" rx="1" /><rect x="5" y="6" width="14" height="15" rx="2" /><path d="M9 12h6" /><path d="M9 16h4" /></svg>
                      </button>
                      <button type="button" class="wv-vault-eye" title="显示密码" :disabled="entry.locked" @click="toggleShow(entry)">
                        <svg v-if="shown[entry.id] && !entry.locked" viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 3l18 18" /><path d="M10.6 10.6a2 2 0 002.8 2.8" /><path d="M9.9 5.2A10.4 10.4 0 0112 5c5 0 8.5 3.5 10 7-.6 1.3-1.5 2.6-2.7 3.7" /><path d="M6.1 6.2C4.3 7.5 2.9 9.2 2 12c1.1 2.6 3.6 5.2 7.4 6.2" /></svg>
                        <svg v-else viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></svg>
                      </button>
                      <button type="button" class="wv-vault-edit" title="编辑" @click="startEdit(entry)">
                        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20h4l10-10-4-4L4 16v4z" /><path d="M13 7l4 4" /></svg>
                      </button>
                      <button type="button" class="wv-vault-edit is-danger" title="删除" @click="removeEntry(entry)">
                        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 7h14" /><path d="M9 7V5h6v2" /><path d="M8 7l1 12h6l1-12" /></svg>
                      </button>
                      </div>
                    </div>
                    <p v-if="entry.note" class="wv-vault-note" :title="entry.note">{{ entry.note }}</p>
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
