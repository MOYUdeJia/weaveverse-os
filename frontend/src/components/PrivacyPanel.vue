<script setup>
import { onMounted, ref } from 'vue'

import {
  getPrivacy,
  listUnusedAttachments,
  purgeUnusedAttachments,
  resetSecurity,
  setVaultPassword,
  unlockVault,
} from '../api/client'
import PasswordField from './PasswordField.vue'
import { showToast } from '../toast'

const emit = defineEmits(['change'])

const status = ref({ security_set: false, vault_set: false })
const unused = ref([])
const scanned = ref(false)
const loaded = ref(false)
const form = ref(blankForm())

function blankForm() {
  return { open: false, current: '', verified: false, next: '', again: '', hint: '' }
}

const ready = () => Boolean(status.value.security_set || status.value.vault_set)

async function load() {
  status.value = await getPrivacy()
  loaded.value = true
  emit('change', status.value)
}

function mismatch() {
  if (form.value.next.length < 8) {
    showToast('密码至少 8 位，建议 12 位')
    return true
  }
  if (form.value.next !== form.value.again) {
    showToast('两次输入不一致')
    return true
  }
  if (form.value.verified && form.value.next === form.value.current) {
    showToast('不能与当前相同')
    return true
  }
  return false
}

async function verify() {
  try {
    await unlockVault(form.value.current)
    form.value.verified = true
  } catch (error) {
    showToast(String(error.message || '密码不对').replace(/^[^:]+:\s*/, ''))
  }
}

async function save() {
  const already = ready()
  if (already && !form.value.verified) {
    showToast('先验证原密码')
    return
  }
  if (mismatch()) {
    return
  }
  try {
    status.value = await setVaultPassword(form.value.next, already ? form.value.current : '', form.value.hint)
    form.value = blankForm()
    if (already) {
      window.dispatchEvent(new Event('wv-privacy-locked'))
    }
    showToast(already ? '修改成功，请重新输入新密码' : '已设置')
    emit('change', status.value)
  } catch (error) {
    showToast(String(error.message || '没有保存').replace(/^[^:]+:\s*/, ''))
  }
}

async function resetSecret() {
  const warning = '确定重置安全密码？密码库里的条目会全部删除，不能恢复。笔记、图片和其他数据还在。旧备份仍要用当时的密码打开。'
  if (!window.confirm(warning)) {
    return
  }
  try {
    status.value = await resetSecurity()
    form.value = blankForm()
    window.dispatchEvent(new Event('wv-privacy-locked'))
    showToast('已重置，请设置新的安全密码')
    emit('change', status.value)
  } catch (error) {
    showToast(String(error.message || '没有重置').replace(/^[^:]+:\s*/, ''))
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
      <h3 class="text-sm font-semibold text-ink">安全密码</h3>
      <p class="mt-1 text-xs text-ink/50">打开密码库和加密备份用同一套。至少 8 位，建议 12 位。关掉应用后重新锁定。改完密码也要再输一次。</p>
      <p v-if="loaded" class="mt-1 text-xs text-moss">{{ ready() ? '已设置' : '未设置' }}</p>
      <div v-if="loaded && !ready()" class="mt-2 grid gap-2">
        <PasswordField v-model="form.next" autocomplete="new-password" placeholder="新安全密码，至少 8 位，建议 12 位" />
        <PasswordField v-model="form.again" autocomplete="new-password" placeholder="再输入一次" />
        <input v-model="form.hint" type="text" maxlength="80" class="h-8 rounded border border-black/10 px-2 text-xs outline-none" placeholder="提示（可选，不是密码）" />
        <button type="button" class="wv-btn wv-btn-primary" @click="save">设置安全密码</button>
      </div>
      <div v-else-if="loaded" class="mt-2">
        <button type="button" class="h-8 rounded border border-black/15 px-3 text-xs" @click="form.open = !form.open">修改安全密码</button>
        <div v-if="form.open" class="mt-2 grid gap-2">
          <PasswordField v-model="form.current" placeholder="原密码" />
          <button type="button" class="h-8 w-fit rounded border border-black/15 px-3 text-xs" :disabled="form.verified" @click="verify">验证</button>
          <template v-if="form.verified">
            <PasswordField v-model="form.next" autocomplete="new-password" placeholder="新密码" />
            <PasswordField v-model="form.again" autocomplete="new-password" placeholder="确认新密码" />
            <button type="button" class="wv-btn wv-btn-primary" @click="save">保存新密码</button>
          </template>
        </div>
        <p class="mt-3 text-xs text-ink/50">忘记密码只能重置。重置会清掉安全密码和密码库条目，其他数据还在。</p>
        <button type="button" class="mt-2 h-8 rounded border border-ember/40 px-3 text-xs text-ember" @click="resetSecret">重置安全密码</button>
      </div>
      <p class="mt-3 text-xs text-ink/45">备份页使用这套安全密码。改完密码后要重新输入一次。</p>
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
