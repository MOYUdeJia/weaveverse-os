<script setup>
import { onMounted, ref } from 'vue'

import {
  getPrivacy,
  listUnusedAttachments,
  purgeUnusedAttachments,
  setBackupPassword,
  setVaultPassword,
  unlockBackup,
  unlockVault,
} from '../api/client'
import PasswordField from './PasswordField.vue'
import { showToast } from '../toast'

const emit = defineEmits(['change'])

const status = ref({ vault_set: false, backup_set: false })
const unused = ref([])
const scanned = ref(false)
const vault = ref(blankForm())
const backup = ref(blankForm())

function blankForm() {
  return { open: false, current: '', verified: false, next: '', again: '' }
}

async function load() {
  status.value = await getPrivacy()
  emit('change', status.value)
}

function mismatch(form) {
  if (form.next.length < 12) {
    showToast('密码至少 12 位')
    return true
  }
  if (form.next !== form.again) {
    showToast('两次输入不一致')
    return true
  }
  if (form.verified && form.next === form.current) {
    showToast('新密码不能与当前密码相同')
    return true
  }
  return false
}

async function verify(kind) {
  const form = kind === 'vault' ? vault.value : backup.value
  try {
    if (kind === 'vault') {
      await unlockVault(form.current)
    } else {
      await unlockBackup(form.current)
    }
    form.verified = true
  } catch (error) {
    showToast(error.message || '密码不对')
  }
}

async function save(kind) {
  const form = kind === 'vault' ? vault.value : backup.value
  const already = kind === 'vault' ? status.value.vault_set : status.value.backup_set
  if (already && !form.verified) {
    showToast('先验证原密码')
    return
  }
  if (mismatch(form)) {
    return
  }
  try {
    const next = kind === 'vault'
      ? await setVaultPassword(form.next, already ? form.current : '')
      : await setBackupPassword(form.next, already ? form.current : '')
    status.value = next
    if (kind === 'vault') {
      vault.value = blankForm()
    } else {
      backup.value = blankForm()
    }
    showToast(already ? '修改成功' : '已设置')
    emit('change', status.value)
  } catch (error) {
    showToast(error.message || '没有保存')
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
      <div v-if="!status.vault_set" class="mt-2 grid gap-2">
        <PasswordField v-model="vault.next" autocomplete="new-password" placeholder="新主密码，至少 12 位" />
        <PasswordField v-model="vault.again" autocomplete="new-password" placeholder="再输入一次" />
        <button type="button" class="h-8 w-fit rounded bg-moss px-3 text-xs text-white" @click="save('vault')">设置主密码</button>
      </div>
      <div v-else class="mt-2">
        <button type="button" class="h-8 rounded border border-black/15 px-3 text-xs" @click="vault.open = !vault.open">修改密码</button>
        <div v-if="vault.open" class="mt-2 grid gap-2">
          <PasswordField v-model="vault.current" placeholder="原密码" />
          <button type="button" class="h-8 w-fit rounded border border-black/15 px-3 text-xs" :disabled="vault.verified" @click="verify('vault')">验证</button>
          <template v-if="vault.verified">
            <PasswordField v-model="vault.next" autocomplete="new-password" placeholder="新密码" />
            <PasswordField v-model="vault.again" autocomplete="new-password" placeholder="确认新密码" />
            <button type="button" class="h-8 w-fit rounded bg-moss px-3 text-xs text-white" @click="save('vault')">提交</button>
          </template>
        </div>
      </div>
    </section>
    <section>
      <h3 class="text-sm font-semibold text-ink">备份密码</h3>
      <p class="mt-1 text-xs text-ink/50">和主密码分开。备份时不用再输，恢复时要输。改密码不影响已经做好的备份文件。</p>
      <p class="mt-1 text-xs text-moss">{{ status.backup_set ? '已设置' : '还没设置' }}</p>
      <div v-if="!status.backup_set" class="mt-2 grid gap-2">
        <PasswordField v-model="backup.next" autocomplete="new-password" placeholder="新备份密码，至少 12 位" />
        <PasswordField v-model="backup.again" autocomplete="new-password" placeholder="再输入一次" />
        <button type="button" class="h-8 w-fit rounded bg-moss px-3 text-xs text-white" @click="save('backup')">设置备份密码</button>
      </div>
      <div v-else class="mt-2">
        <button type="button" class="h-8 rounded border border-black/15 px-3 text-xs" @click="backup.open = !backup.open">修改密码</button>
        <div v-if="backup.open" class="mt-2 grid gap-2">
          <PasswordField v-model="backup.current" placeholder="原密码" />
          <button type="button" class="h-8 w-fit rounded border border-black/15 px-3 text-xs" :disabled="backup.verified" @click="verify('backup')">验证</button>
          <template v-if="backup.verified">
            <PasswordField v-model="backup.next" autocomplete="new-password" placeholder="新密码" />
            <PasswordField v-model="backup.again" autocomplete="new-password" placeholder="确认新密码" />
            <button type="button" class="h-8 w-fit rounded bg-moss px-3 text-xs text-white" @click="save('backup')">提交</button>
          </template>
        </div>
      </div>
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
