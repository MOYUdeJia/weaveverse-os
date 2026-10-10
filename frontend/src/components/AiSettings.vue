<script setup>
import { onMounted, ref, watch } from 'vue'

import { getAiSettings, saveAiSettings, testAiConnection } from '../api/client'
import { showToast } from '../toast'

const providers = ref([])
const provider = ref('deepseek')
const baseUrl = ref('')
const model = ref('')
const apiKey = ref('')
const hasKey = ref(false)
const urlTouched = ref(false)
const busy = ref(false)

const current = () => providers.value.find((item) => item.id === provider.value)

async function load() {
  const payload = await getAiSettings()
  providers.value = payload.providers || []
  provider.value = payload.provider || 'deepseek'
  baseUrl.value = payload.base_url || current()?.base_url || ''
  model.value = payload.model || current()?.models?.[0] || ''
  hasKey.value = Boolean(payload.has_key)
  apiKey.value = ''
  urlTouched.value = false
}

watch(provider, () => {
  const spec = current()
  if (!spec) {
    return
  }
  if (!urlTouched.value) {
    baseUrl.value = spec.base_url
  }
  if (!spec.models.includes(model.value)) {
    model.value = spec.models[0] || ''
  }
})

async function save() {
  busy.value = true
  try {
    const saved = await saveAiSettings({
      provider: provider.value,
      base_url: baseUrl.value,
      model: model.value,
      api_key: apiKey.value,
    })
    hasKey.value = Boolean(saved.has_key)
    apiKey.value = ''
    showToast('AI 设置已保存')
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
    hasKey.value = Boolean(saved.has_key)
    apiKey.value = ''
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
    <label class="text-xs text-ink/55">提供商</label>
    <select v-model="provider" class="wv-surface h-10 rounded border border-black/10 px-2 text-sm">
      <option v-for="item in providers" :key="item.id" :value="item.id">{{ item.label }}</option>
    </select>
    <label class="text-xs text-ink/55">Base URL</label>
    <input v-model="baseUrl" class="wv-surface h-10 rounded border border-black/10 px-2 text-sm outline-none" @input="urlTouched = true" />
    <label class="text-xs text-ink/55">API Key</label>
    <input
      v-model="apiKey"
      type="password"
      autocomplete="off"
      class="wv-surface h-10 rounded border border-black/10 px-2 text-sm outline-none"
      :placeholder="hasKey ? '已保存，留空则不修改' : '在这里粘贴 Key'"
    />
    <label class="text-xs text-ink/55">模型</label>
    <select v-model="model" class="wv-surface h-10 rounded border border-black/10 px-2 text-sm">
      <option v-for="name in current()?.models || []" :key="name" :value="name">{{ name }}</option>
    </select>
    <div class="flex gap-2">
      <button type="button" class="h-9 rounded bg-moss px-3 text-xs text-white" :disabled="busy" @click="save">保存</button>
      <button type="button" class="wv-chip h-9 rounded px-3 text-xs" :disabled="busy" @click="test">测试连接</button>
    </div>
  </div>
</template>
