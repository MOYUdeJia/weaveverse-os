<script setup>
import { onMounted, ref } from 'vue'

import {
  deleteBackupFile,
  exportBackup,
  getBackupInfo,
  resetSecurity,
  restoreBackup,
  restoreNamedBackup,
  unlockBackup,
} from '../api/client'
import PasswordField from './PasswordField.vue'
import { showToast } from '../toast'

const emit = defineEmits(['need-privacy'])

const last = ref('')
const items = ref([])
const backupSet = ref(false)
const backupUnlocked = ref(false)
const hint = ref('')
const label = ref('')
const sessionPassword = ref('')
const oldPassword = ref('')
const needOld = ref(false)
const restoreName = ref('')
const file = ref(null)
const busy = ref(false)
const loaded = ref(false)

async function load() {
  const info = await getBackupInfo()
  last.value = info.last_backup_at || ''
  items.value = info.items || []
  backupSet.value = Boolean(info.security_set ?? info.backup_set)
  backupUnlocked.value = Boolean(info.backup_unlocked)
  hint.value = info.security_hint || ''
  loaded.value = true
}

async function resetSecret() {
  const warning = '确定重置安全密码？密码库里的条目会全部删除，不能恢复。笔记、图片和其他数据还在。旧备份仍要用当时的密码打开。'
  if (!window.confirm(warning)) {
    return
  }
  try {
    await resetSecurity()
    window.dispatchEvent(new Event('wv-privacy-locked'))
    showToast('已重置，请设置新的安全密码')
    emit('need-privacy')
    await load()
  } catch (error) {
    showToast(String(error.message || '没有重置').replace(/^[^:]+:\s*/, ''))
  }
}

async function unlockSession() {
  try {
    await unlockBackup(sessionPassword.value)
    sessionPassword.value = ''
    await load()
  } catch (error) {
    showToast(error.message || '密码不对')
  }
}

async function download() {
  if (!backupSet.value) {
    showToast('请先设置安全密码')
    emit('need-privacy')
    return
  }
  if (!backupUnlocked.value) {
    showToast('请先输入安全密码')
    return
  }
  busy.value = true
  try {
    const result = await exportBackup(label.value.trim())
    label.value = ''
    showToast(`已备份到 ${result.path}`)
    await load()
  } catch (error) {
    const message = error.message || '备份没有做成'
    showToast(message.replace(/^[^:]+:\s*/, ''))
    if (message.includes('设置')) {
      emit('need-privacy')
    }
  } finally {
    busy.value = false
  }
}

function passwordError(error) {
  const message = error.message || '恢复没有完成'
  if (message.includes('密码不对') || message.includes('解不开')) {
    needOld.value = true
    showToast('这份备份要用当时的安全密码')
    return
  }
  showToast(message)
}

async function restoreNamed() {
  if (!restoreName.value) {
    showToast('先选一个备份')
    return
  }
  if (!window.confirm('当前数据会被覆盖。恢复前会留下最近 3 份后悔副本。继续吗？')) {
    return
  }
  busy.value = true
  try {
    await restoreNamedBackup(restoreName.value, needOld.value ? oldPassword.value : '')
    oldPassword.value = ''
    needOld.value = false
    showToast('已恢复，请重启')
  } catch (error) {
    passwordError(error)
  } finally {
    busy.value = false
  }
}

async function restoreFile() {
  if (!file.value) {
    showToast('先选择 .wvbak 文件')
    return
  }
  if (!window.confirm('当前数据会被覆盖。恢复前会留下最近 3 份后悔副本。继续吗？')) {
    return
  }
  busy.value = true
  try {
    await restoreBackup(file.value, needOld.value ? oldPassword.value : '')
    oldPassword.value = ''
    needOld.value = false
    showToast('已恢复，请重启')
  } catch (error) {
    passwordError(error)
  } finally {
    busy.value = false
  }
}

async function removeItem(filename) {
  if (!window.confirm('确定删除这份备份吗？')) {
    return
  }
  await deleteBackupFile(filename)
  if (restoreName.value === filename) {
    restoreName.value = ''
  }
  await load()
}

function sizeLabel(size) {
  if (!size) {
    return ''
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

onMounted(() => {
  load().catch(() => {})
})
</script>

<template>
  <div class="grid gap-3 text-sm">
    <p class="text-xs text-ink/70">使用备份/恢复需要输入安全密码，本次登陆有效</p>
    <p class="text-xs text-ink/50">上次备份：{{ last || '还没有' }}</p>
    <template v-if="loaded && !backupSet">
      <p class="text-xs text-ember">请先设置安全密码</p>
      <button type="button" class="wv-btn wv-btn-primary" @click="emit('need-privacy')">去设置安全密码</button>
    </template>
    <template v-else-if="loaded && !backupUnlocked">
      <p class="text-xs text-ink/50">输入安全密码后，这次运行里备份和恢复不用再输。</p>
      <p v-if="hint" class="text-xs text-moss">提示：{{ hint }}</p>
      <PasswordField v-model="sessionPassword" placeholder="安全密码" />
      <button type="button" class="h-8 w-fit rounded border border-black/15 px-3 text-xs" @click="unlockSession">解锁</button>
      <button type="button" class="h-8 w-fit text-xs text-ember" @click="resetSecret">忘记密码，重置</button>
    </template>
    <template v-else-if="loaded">
      <input v-model="label" type="text" class="wv-surface h-10 rounded border border-black/10 px-3 outline-none" placeholder="可选命名" />
      <button type="button" class="wv-btn wv-btn-primary" :disabled="busy" @click="download">立即备份</button>
      <p class="mt-2 text-xs font-semibold text-ink">历史备份</p>
      <p v-if="!items.length" class="text-xs text-ink/40">还没有备份文件</p>
      <div v-for="item in items" :key="item.filename" class="flex items-center gap-2 text-xs">
        <label class="flex min-w-0 flex-1 items-center gap-2">
          <input v-model="restoreName" type="radio" :value="item.filename" />
          <span class="truncate">{{ item.label || '（无命名）' }} · {{ item.time }} · {{ sizeLabel(item.size) }}</span>
        </label>
        <button type="button" class="text-ember" title="删除" @click="removeItem(item.filename)">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 7h14" /><path d="M9 7V5h6v2" /><path d="M8 7l1 12h6l1-12" /></svg>
        </button>
      </div>
      <PasswordField v-if="needOld" v-model="oldPassword" placeholder="当时的安全密码" />
      <button type="button" class="h-9 w-fit rounded border border-black/15 px-3 text-xs" :disabled="busy" @click="restoreNamed">恢复</button>
      <p class="mt-2 text-xs text-ink/40">也可以从别处选一个 .wvbak</p>
      <input type="file" accept=".wvbak" @change="file = $event.target.files?.[0] || null" />
      <button type="button" class="h-9 w-fit rounded border border-black/15 px-3 text-xs" :disabled="busy" @click="restoreFile">从文件恢复</button>
    </template>
  </div>
</template>
