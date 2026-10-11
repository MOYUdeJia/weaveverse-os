<script setup>
import { onMounted, ref } from 'vue'

import { exportBackup, getBackupInfo, restoreBackup } from '../api/client'
import { showToast } from '../toast'

const last = ref('')
const password = ref('')
const restorePassword = ref('')
const file = ref(null)
const busy = ref(false)

async function load() {
  const info = await getBackupInfo()
  last.value = info.last_backup_at || ''
}

async function download() {
  if (password.value.length < 8) {
    showToast('密码至少 8 位')
    return
  }
  busy.value = true
  try {
    const blob = await exportBackup(password.value)
    password.value = ''
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'weaveverse.wvbak'
    link.click()
    URL.revokeObjectURL(link.href)
    showToast('备份已开始下载')
    await load()
  } catch (error) {
    showToast(error.message || '备份没有做成')
  } finally {
    busy.value = false
  }
}

async function restore() {
  if (!file.value) {
    showToast('先选择 .wvbak 文件')
    return
  }
  if (restorePassword.value.length < 8) {
    showToast('密码至少 8 位')
    return
  }
  if (!window.confirm('当前数据会被覆盖。建议先做一次备份。恢复前会把现有数据复制到 data/safety。继续吗？')) {
    return
  }
  busy.value = true
  try {
    await restoreBackup(file.value, restorePassword.value)
    restorePassword.value = ''
    showToast('已恢复。请关闭窗口后重新打开。')
  } catch (error) {
    showToast(error.message || '密码不对')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  load().catch(() => {})
})
</script>

<template>
  <div class="grid gap-3 text-sm">
    <p class="text-xs text-ink/50">上次备份：{{ last ? last.slice(0, 19).replace('T', ' ') : '还没有' }}</p>
    <p class="text-xs text-ink/60">备份包含数据库、附件、书籍、音乐、图标、背景和外观。不含语音模型和钥匙串里的 Key。主密码不会被保存。</p>
    <input v-model="password" type="password" autocomplete="new-password" class="wv-surface h-10 rounded border border-black/10 px-3 outline-none" placeholder="备份密码，至少 8 位" />
    <button type="button" class="h-9 w-fit rounded bg-moss px-3 text-xs text-white" :disabled="busy" @click="download">备份</button>
    <input type="file" accept=".wvbak" @change="file = $event.target.files?.[0] || null" />
    <input v-model="restorePassword" type="password" autocomplete="current-password" class="wv-surface h-10 rounded border border-black/10 px-3 outline-none" placeholder="恢复密码" />
    <button type="button" class="h-9 w-fit rounded border border-black/15 px-3 text-xs" :disabled="busy" @click="restore">恢复</button>
  </div>
</template>
