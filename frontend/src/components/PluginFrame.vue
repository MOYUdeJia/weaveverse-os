<script setup>
// Sandboxed plugin page. The iframe is a unique origin and cannot read the host.
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { pluginEntryUrl } from '../api/client'
import { showToast } from '../toast'

const props = defineProps({
  plugin: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close'])
const frame = ref(null)

function onMessage(event) {
  if (event.source !== frame.value?.contentWindow) return
  const data = event.data
  if (!data || data.source !== 'wv-plugin') return
  if (data.type === 'toast') {
    showToast(String(data.text || '').slice(0, 200))
  }
}

function greet() {
  frame.value?.contentWindow?.postMessage(
    { source: 'wv-host', type: 'hello', id: props.plugin.id, name: props.plugin.name },
    '*',
  )
}

onMounted(() => {
  window.addEventListener('message', onMessage)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
})
</script>

<template>
  <section class="frame">
    <header>
      <h2>{{ plugin.name }}</h2>
      <button type="button" @click="emit('close')">关闭插件</button>
    </header>
    <iframe
      ref="frame"
      :src="pluginEntryUrl(plugin)"
      :title="plugin.name"
      sandbox="allow-scripts"
      referrerpolicy="no-referrer"
      @load="greet"
    />
  </section>
</template>

<style scoped>
.frame {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  height: 100vh;
  background: #f6f1e8;
  color: #1c1915;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 28px;
}

h2 {
  margin: 0;
  overflow: hidden;
  font-size: 22px;
  line-height: 1.1;
  letter-spacing: -0.03em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

button {
  min-height: 36px;
  padding: 0 12px;
  border: 0;
  background: #e7e0d4;
  color: inherit;
  font: inherit;
  font-size: 14px;
}

button:focus-visible,
iframe:focus-visible {
  outline: 2px solid #c43228;
  outline-offset: 2px;
}

iframe {
  flex: 1;
  width: 100%;
  min-height: 0;
  border: 0;
  background: #f4efe6;
}
</style>
