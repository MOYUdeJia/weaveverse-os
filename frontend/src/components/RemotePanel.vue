<script setup>
import { onMounted, ref } from 'vue'

import { getRemoteStatus } from '../api/client'
import { showToast } from '../toast'

const status = ref(null)

const label = {
  connected: '已连接',
  logged_out: '未登录',
  missing: '未安装',
}

async function load() {
  status.value = await getRemoteStatus()
}

async function copy() {
  if (!status.value?.url) {
    return
  }
  await navigator.clipboard.writeText(status.value.url)
  showToast('地址已复制')
}

onMounted(() => {
  load().catch((error) => showToast(error.message || '读不到 Tailscale 状态'))
})
</script>

<template>
  <div class="grid gap-3 text-sm">
    <p>状态：{{ label[status?.state] || '正在检查' }}</p>
    <p v-if="status?.ip">本机地址：{{ status.ip }}</p>
    <p v-if="status?.url">手机打开：{{ status.url }}</p>
    <button v-if="status?.url" type="button" class="wv-btn wv-btn-primary" @click="copy">复制地址</button>
    <div v-if="status?.qr" class="w-40 bg-white p-2" v-html="status.qr" />
    <ol class="list-decimal space-y-1 pl-5 text-xs leading-5 text-ink/70">
      <li>打开 tailscale.com 注册账号。</li>
      <li>在这台电脑安装 Tailscale 并登录。</li>
      <li>手机也安装 Tailscale，登录同一个账号。</li>
      <li>用手机浏览器打开上面的地址。</li>
    </ol>
    <p class="text-xs text-ink/45">这里只读取状态，不会改 Tailscale。传输由 Tailscale 加密，应用本身不开 HTTPS。</p>
  </div>
</template>
