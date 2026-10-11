<script setup>
import { onMounted, ref } from 'vue'

import {
  getPrivacy,
  listUnusedAttachments,
  purgeUnusedAttachments,
  setBackupPassword,
  setVaultPassword,
} from '../api/client'
import { showToast } from '../toast'

const emit = defineEmits(['change'])

const status = ref({ vault_set: false, backup_set: false })
const vaultPassword = ref('')
const vaultCurrent = ref('')
const backupPassword = ref('')
const backupCurrent = ref('')
const unused = ref([])
const scanned = ref(false)

async function load() {
  status.value = await getPrivacy()
  emit('change', status.value)
}

async function saveVault() {
  try {
    status.value = await setVaultPassword(vaultPassword.value, vaultCurrent.value)
    vaultPassword.value = ''
    vaultCurrent.value = ''
    showToast(status.value.vault_set ? '主密码已保存' : '主密码已设置')
    emit('change', status.value)
  } catch (error) {
    showToast(error.message || '主密码没有保存')
  }
}

async function saveBackup() {
  try {
    status.value = await setBackupPassword(backupPassword.value, backupCurrent.value)
    backupPassword.value = ''
    backupCurrent.value = ''
    showToast('备份密码已保存')
    emit('change', status.value)
  } catch (error) {
    showToast(error.message || '备份密码没有保存')
  }
}

async function scanUnused() {
  const result = await listUnusedAttachments()
  unused.value = result.items || []
  scanned.value = true
}

async function purgeUnused() {
  if (!unused.value.length) {
    return
  }
  if (!window.confirm(`彻底删除 ${unused.value.length} 个未引用附件？`)) {
    return
  }
  const result = await purgeUnusedAttachments(unused.value.map((item) => item.filename))
  unused.value = result.items || []
  showToast(`已清理 ${result.removed?.length || 0} 个文件`)
}

function sizeLabel(size) {
  if (size < 1024) {
    return `${size} B`
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
  <div class="grid gap-6 text-sm">
    <section>
      <h3 class="text-sm font-semibold text-ink">密码管理器主密码</h3>
      <p class="mt-1 text-xs text-ink/50">至少 12 位。忘记无法恢复。只在本次运行里记住，关掉应用要重输。</p>
      <p class="mt-1 text-xs text-moss">{{ status.vault_set ? '已设置' : '还没设置' }}</p>
      <input v-if="status.vault_set" v-model="vaultCurrent" type="password" autocomplete="current-password" class="mt-2 h-9 w-full rounded border border-black/10 px-2 outline-none" placeholder="当前主密码" />
      <input v-model="vaultPassword" type="password" autocomplete="new-password" class="mt-2 h-9 w-full rounded border border-black/10 px-2 outline-none" placeholder="新主密码，至少 12 位" />
      <button type="button" class="mt-2 h-8 rounded bg-moss px-3 text-xs text-white" @click="saveVault">{{ status.vault_set ? '修改主密码' : '设置主密码' }}</button>
    </section>
    <section>
      <h3 class="text-sm font-semibold text-ink">备份密码</h3>
      <p class="mt-1 text-xs text-ink/50">和主密码分开。备份时不用再输，恢复时要输。改密码不影响已经做好的备份文件。</p>
      <p class="mt-1 text-xs text-moss">{{ status.backup_set ? '已设置' : '还没设置' }}</p>
      <input v-if="status.backup_set" v-model="backupCurrent" type="password" autocomplete="current-password" class="mt-2 h-9 w-full rounded border border-black/10 px-2 outline-none" placeholder="当前备份密码" />
      <input v-model="backupPassword" type="password" autocomplete="new-password" class="mt-2 h-9 w-full rounded border border-black/10 px-2 outline-none" placeholder="新备份密码，至少 12 位" />
      <button type="button" class="mt-2 h-8 rounded bg-moss px-3 text-xs text-white" @click="saveBackup">{{ status.backup_set ? '修改备份密码' : '设置备份密码' }}</button>
    </section>
    <section>
      <h3 class="text-sm font-semibold text-ink">清理未使用附件</h3>
      <p class="mt-1 text-xs text-ink/50">扫描 attachments 里没有被文档、图库或其他地方提到的文件。</p>
      <button type="button" class="mt-2 h-8 rounded border border-black/15 px-3 text-xs" @click="scanUnused">扫描</button>
      <p v-if="scanned" class="mt-2 text-xs text-ink/50">找到 {{ unused.length }} 个</p>
      <ul v-if="unused.length" class="mt-2 max-h-40 overflow-y-auto text-xs text-ink/70">
        <li v-for="item in unused" :key="item.filename">{{ item.filename }} · {{ sizeLabel(item.size) }}</li>
      </ul>
      <button v-if="unused.length" type="button" class="mt-2 h-8 rounded bg-ember px-3 text-xs text-white" @click="purgeUnused">一键清理</button>
    </section>
  </div>
</template>
