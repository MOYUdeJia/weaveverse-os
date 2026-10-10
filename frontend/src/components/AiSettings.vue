<script setup>
import { computed, onMounted, ref } from 'vue'

import { getAiSettings, saveAiSettings, testAiConnection } from '../api/client'
import { showToast } from '../toast'

const providers = ref([])
const profiles = ref({})
const provider = ref('deepseek')
const baseUrl = ref('')
const model = ref('')
const apiKey = ref('')
const hasKey = ref(false)
const busy = ref(false)

const current = computed(() => providers.value.find((item) => item.id === provider.value) || null)
const keyLabel = computed(() => (apiKey.value.trim() ? '未保存' : hasKey.value ? '已保存' : '未保存'))

function showProvider(id) {
  const spec = providers.value.find((item) => item.id === id)
  const profile = profiles.value[id] || {}
  provider.value = id
  baseUrl.value = profile.base_url || spec?.base_url || ''
  model.value = profile.model || spec?.models?.[0] || ''
  hasKey.value = Boolean(profile.has_key)
  apiKey.value = ''
}

async function load() {
  const payload = await getAiSettings()
  providers.value = payload.providers || []
  profiles.value = payload.profiles || {}
  showProvider(payload.provider || 'deepseek')
}

async function save() {
  busy.value = true
  try {
    const saved = await saveAiSettings({
      provider: provider.value,
      base_url: baseUrl.value,
      model: model.value,
      api_key: apiKey.value,
    })
    profiles.value = saved.profiles || profiles.value
    showProvider(saved.provider || provider.value)
    showToast(saved.has_key ? '已保存' : '地址和模型已保存，Key 还没有')
  } catch (error) {
    showToast(error.message || '保存失败')
  } finally {
    busy.value = false
  }
}

async function test() {
  busy.value = true
  try {
    const saved = await saveAiSettings({
      provider: provider.value,
      base_url: baseUrl.value,
      model: model.value,
      api_key: apiKey.value,
    })
    profiles.value = saved.profiles || profiles.value
    showProvider(saved.provider || provider.value)
    await testAiConnection()
    showToast('连接成功')
  } catch (error) {
    showToast(error.message || '网络错误，请重试')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  load().catch((error) => showToast(error.message || '无法加载 AI 设置'))
})
</script>

<template>
  <div class="grid gap-3">
    <p class="text-xs text-ink/55">每个提供商分开保存。换一个，会看到它自己的地址、模型和 Key 状态。</p>
    <div class="flex flex-wrap gap-2">
      <button
        v-for="item in providers"
        :key="item.id"
        type="button"
        class="h-9 rounded px-3 text-xs"
        :class="provider === item.id ? 'bg-moss text-white' : 'wv-chip'"
        @click="showProvider(item.id)"
      >
        {{ item.label }}
        <span class="ml-1 opacity-70">{{ profiles[item.id]?.has_key ? '已保存' : '未保存' }}</span>
      </button>
    </div>
    <label class="text-xs text-ink/55">Base URL</label>
    <input v-model="baseUrl" class="wv-surface h-10 rounded border border-black/10 px-2 text-sm outline-none" />
    <label class="text-xs text-ink/55">模型</label>
    <select v-model="model" class="wv-surface h-10 rounded border border-black/10 px-2 text-sm">
      <option v-for="name in current?.models || []" :key="name" :value="name">{{ name }}</option>
    </select>
    <div class="flex items-center justify-between">
      <label class="text-xs text-ink/55">API Key</label>
      <span class="text-xs" :class="keyLabel === '已保存' && !apiKey ? 'text-moss' : 'text-ember'">{{ keyLabel }}</span>
    </div>
    <input
      v-model="apiKey"
      type="password"
      autocomplete="off"
      class="wv-surface h-10 rounded border border-black/10 px-2 text-sm outline-none"
      :placeholder="hasKey ? '留空表示继续用已保存的 Key' : '粘贴 Key，保存后才会写入'"
    />
    <div class="flex gap-2">
      <button type="button" class="h-9 rounded bg-moss px-3 text-xs text-white" :disabled="busy" @click="save">保存</button>
      <button type="button" class="wv-chip h-9 rounded px-3 text-xs" :disabled="busy || keyLabel !== '已保存' && !apiKey" @click="test">测试连接</button>
    </div>
  </div>
</template>
