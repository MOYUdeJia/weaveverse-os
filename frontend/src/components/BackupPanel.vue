<script setup>
import { onMounted, ref } from 'vue'

import {
  deleteBackupFile,
  exportBackup,
  getBackupInfo,
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
const label = ref('')
const sessionPassword = ref('')
const restorePassword = ref('')
const restoreName = ref('')
const file = ref(null)
const extras = ref([])
const busy = ref(false)

async function load() {
  const info = await getBackupInfo()
  last.value = info.last_backup_at || ''
  items.value = info.items || []
  backupSet.value = Boolean(info.backup_set)
  backupUnlocked.value = Boolean(info.backup_unlocked)
}

async function unlockSession() {
  try {
    await unlockBackup(sessionPassword.value)
    sessionPassword.value = ''
    await load()
    showToast('本会话已记住备份密码')
  } catch (error) {
    showToast(error.message || '密码不对')
  }
}

async function download() {
  if (!backupSet.value) {
    showToast('请先设置备份密码')
    emit('need-privacy')
    return
  }
  if (!backupUnlocked.value) {
    showToast('重启后需要先输入备份密码')
    return
  }
  busy.value = true
  try {
    const result = await exportBackup(label.value.trim())
    label.value = ''
    extras.value = result.extras || []
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

async function restoreNamed() {
  if (!restoreName.value) {
    showToast('先选一个备份')
    return
  }
  if (!restorePassword.value) {
    showToast('恢复需要输入备份密码')
    return
  }
  if (!window.confirm('当前数据会被覆盖。恢复前会把现有数据复制到 data/safety。继续吗？')) {
    return
  }
  busy.value = true
  try {
    await restoreNamedBackup(restoreName.value, restorePassword.value)
    restorePassword.value = ''
    showToast('已恢复，请重启应用')
  } catch (error) {
    showToast(error.message || '密码不对')
  } finally {
    busy.value = false
  }
}

async function restoreFile() {
  if (!file.value) {
    showToast('先选择 .wvbak 文件')
    return
  }
  if (!restorePassword.value) {
    showToast('恢复需要输入备份密码')
    return
  }
  if (!window.confirm('当前数据会被覆盖。恢复前会把现有数据复制到 data/safety。继续吗？')) {
    return
  }
  busy.value = true
  try {
    await restoreBackup(file.value, restorePassword.value)
    restorePassword.value = ''
    showToast('已恢复，请重启应用')
  } catch (error) {
    showToast(error.message || '密码不对')
  } finally {
    busy.value = false
  }
}

async function dropExtra(filename) {
  await deleteBackupFile(filename)
  extras.value = extras.value.filter((item) => item.filename !== filename)
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
    <p class="text-xs text-ink/50">上次备份：{{ last || '还没有' }}</p>
    <p class="text-xs text-ink/60">备份会加密存到 data/backups。不含语音模型和钥匙串里的 Key。密码本身不会被保存。</p>
    <p v-if="!backupSet" class="text-xs text-ember">还没有备份密码。</p>
    <button v-if="!backupSet" type="button" class="h-8 w-fit rounded bg-moss px-3 text-xs text-white" @click="emit('need-privacy')">去设置备份密码</button>
    <template v-else-if="!backupUnlocked">
      <p class="text-xs text-ink/50">应用重启后要再输一次备份密码，之后这次运行里备份不用再输。</p>
      <PasswordField v-model="sessionPassword" placeholder="输入备份密码" />
      <button type="button" class="h-8 w-fit rounded border border-black/15 px-3 text-xs" @click="unlockSession">记住到本次运行</button>
    </template>
    <input v-model="label" type="text" class="wv-surface h-10 rounded border border-black/10 px-3 outline-none" placeholder="可选命名，例如 十月版本" />
    <button type="button" class="h-9 w-fit rounded bg-moss px-3 text-xs text-white" :disabled="busy" @click="download">立即备份</button>
    <div v-if="extras.length" class="rounded border border-ember/30 p-2 text-xs">
      <p>已超过最近 5 个。可以删掉更早的：</p>
      <div v-for="item in extras" :key="item.filename" class="mt-1 flex items-center justify-between gap-2">
        <span>{{ item.label || '（无命名）' }} · {{ item.time }}</span>
        <button type="button" class="text-ember" @click="dropExtra(item.filename)">删除</button>
      </div>
    </div>
    <p class="mt-2 text-xs font-semibold text-ink">历史备份</p>
    <p v-if="!items.length" class="text-xs text-ink/40">还没有备份文件</p>
    <label v-for="item in items" :key="item.filename" class="flex items-center gap-2 text-xs">
      <input v-model="restoreName" type="radio" :value="item.filename" />
      <span>{{ item.label || '（无命名）' }} · {{ item.time }} · {{ sizeLabel(item.size) }}</span>
    </label>
    <PasswordField v-model="restorePassword" placeholder="恢复时输入密码" />
    <button type="button" class="h-9 w-fit rounded border border-black/15 px-3 text-xs" :disabled="busy" @click="restoreNamed">恢复所选备份</button>
    <p class="mt-2 text-xs text-ink/40">也可以从别处选一个旧的 .wvbak</p>
    <input type="file" accept=".wvbak" @change="file = $event.target.files?.[0] || null" />
    <button type="button" class="h-9 w-fit rounded border border-black/15 px-3 text-xs" :disabled="busy" @click="restoreFile">从文件恢复</button>
  </div>
</template>
