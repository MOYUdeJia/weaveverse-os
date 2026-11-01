<script setup>
// Installed plugins, zip import, a reserved market tab, and the developer guide.
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { ref, watch } from 'vue'

import { deletePlugin, getPluginGuide, getPlugins, importPlugin, pluginExportUrl } from '../api/client'
import { showToast } from '../toast'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'open'])

const tab = ref('installed')
const items = ref([])
const busy = ref(false)
const pendingDelete = ref('')
const docsOpen = ref(false)
const guideHtml = ref('')
const guideError = ref('')

async function load() {
  try {
    const data = await getPlugins()
    items.value = data.items || []
  } catch (error) {
    showToast(error.message || '插件没有读出来')
  }
}

async function onImport(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  busy.value = true
  try {
    await importPlugin(file)
    await load()
    showToast('插件已经放进来')
  } catch (error) {
    showToast(error.message || '这个压缩包没有装上')
  } finally {
    busy.value = false
  }
}

async function remove(id) {
  if (pendingDelete.value !== id) {
    pendingDelete.value = id
    return
  }
  pendingDelete.value = ''
  try {
    await deletePlugin(id)
    await load()
  } catch (error) {
    showToast(error.message || '没有删掉')
  }
}

async function openDocs() {
  docsOpen.value = true
  if (guideHtml.value || guideError.value) return
  try {
    const data = await getPluginGuide()
    guideHtml.value = DOMPurify.sanitize(marked.parse(data.markdown || '', { async: false }))
  } catch (error) {
    guideError.value = error.message || '文档没有读出来'
  }
}

function onKey(event) {
  if (event.key !== 'Escape' || !props.open) return
  if (docsOpen.value) {
    docsOpen.value = false
    return
  }
  emit('close')
}

watch(
  () => props.open,
  (value) => {
    if (!value) return
    tab.value = 'installed'
    pendingDelete.value = ''
    load()
    window.addEventListener('keydown', onKey)
  },
)

watch(
  () => props.open,
  (value) => {
    if (!value) window.removeEventListener('keydown', onKey)
  },
)
</script>

<template>
  <div v-if="open" class="mask" @click="emit('close')">
    <section class="sheet" role="dialog" aria-modal="true" aria-labelledby="plugin-title" @click.stop>
      <header class="top">
        <h2 id="plugin-title">插件</h2>
        <button type="button" class="ghost" @click="emit('close')">关闭</button>
      </header>
      <div class="tabs">
        <button type="button" :class="{ 'is-on': tab === 'installed' }" @click="tab = 'installed'">已安装</button>
        <button type="button" :class="{ 'is-on': tab === 'market' }" @click="tab = 'market'">市场</button>
        <button type="button" @click="openDocs">开发者文档</button>
      </div>

      <div v-if="tab === 'market'" class="market">
        <p>敬请期待</p>
      </div>

      <template v-else>
        <label class="import" :class="{ 'is-busy': busy }">
          导入 zip
          <input type="file" accept=".zip,application/zip" :disabled="busy" @change="onImport" />
        </label>
        <p v-if="!items.length" class="empty">还没有插件。</p>
        <ul v-else>
          <li v-for="item in items" :key="item.id">
            <span class="mark" aria-hidden="true">{{ item.icon }}</span>
            <span class="copy">
              <span class="name">{{ item.name }}</span>
              <span class="meta">{{ item.version }}</span>
            </span>
            <button type="button" class="open" @click="emit('open', item)">打开</button>
            <a :href="pluginExportUrl(item.id)">导出</a>
            <button type="button" class="danger" @click="remove(item.id)">
              {{ pendingDelete === item.id ? '确认删除' : '删除' }}
            </button>
          </li>
        </ul>
      </template>
    </section>
    <section v-if="docsOpen" class="docs" role="dialog" aria-modal="true" aria-labelledby="plugin-guide-title" @click.stop>
      <header class="top">
        <h2 id="plugin-guide-title">开发者文档</h2>
        <button type="button" class="ghost" @click="docsOpen = false">关闭</button>
      </header>
      <p v-if="guideError">{{ guideError }}</p>
      <p v-else-if="!guideHtml">正在读取文档。</p>
      <article v-else class="prose" v-html="guideHtml" />
    </section>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  background: rgba(22, 24, 20, 0.46);
}

.docs {
  position: absolute;
  top: 24px;
  right: 16px;
  left: 16px;
  width: min(720px, calc(100% - 32px));
  max-height: min(84vh, 800px);
  margin: 0 auto;
  overflow: auto;
  padding: 28px;
  border-radius: 20px;
  background: #f7f3ea;
  color: #1c1915;
  animation: plugin-panel-in 320ms cubic-bezier(0.2, 0, 0, 1);
}

.prose :deep(h1),
.prose :deep(h2) {
  margin: 1.2em 0 0.4em;
  font-size: 28px;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.prose :deep(h1) {
  margin-top: 0;
  font-size: 36px;
}

.prose :deep(p),
.prose :deep(li) {
  font-size: 16px;
  line-height: 1.55;
}

.prose :deep(pre) {
  overflow: auto;
  padding: 12px;
  background: #1c1915;
  color: #f6f1e8;
}

.prose :deep(code) {
  font-family: ui-monospace, monospace;
  font-size: 14px;
}

.prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.prose :deep(td),
.prose :deep(th) {
  padding: 8px 10px;
  background: #efe8dc;
  text-align: left;
}

.sheet {
  width: min(640px, 100%);
  max-height: min(80vh, 720px);
  overflow: auto;
  padding: 28px;
  border-radius: 20px;
  background: #f3eee4;
  color: #1c1915;
  animation: plugin-panel-in 320ms cubic-bezier(0.2, 0, 0, 1);
}

.top,
.tabs,
li {
  display: flex;
  align-items: center;
}

.top {
  justify-content: space-between;
}

h2,
p,
.name,
.meta {
  margin: 0;
}

h2 {
  font-size: 32px;
  line-height: 1;
  letter-spacing: -0.03em;
}

.ghost,
.tabs button,
.import,
.open,
.danger,
a {
  border: 0;
  border-radius: 10px;
  background: #e7e0d4;
  color: inherit;
  font: inherit;
  font-size: 14px;
  text-decoration: none;
  transition:
    transform 130ms cubic-bezier(0.2, 0, 0, 1),
    background-color 160ms ease,
    color 160ms ease;
}

.ghost,
.tabs button,
.import,
.open,
.danger,
a {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  padding: 0 12px;
}

.tabs {
  gap: 8px;
  margin-top: 18px;
}

.tabs button.is-on,
.open {
  background: #1c1915;
  color: #f6f1e8;
}

.import {
  margin-top: 22px;
  cursor: pointer;
}

.import input {
  display: none;
}

.import.is-busy {
  opacity: 0.5;
}

.empty,
.market p {
  margin-top: 28px;
  font-size: 22px;
  line-height: 1.3;
}

.market {
  min-height: 220px;
}

ul {
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}

li {
  gap: 12px;
  min-height: 72px;
  margin-top: 8px;
  border-radius: 14px;
  background: #eee7da;
  transition:
    transform 180ms cubic-bezier(0.2, 0, 0, 1),
    background-color 180ms ease;
}

li:nth-child(odd) {
  background: #e9e2d4;
}

li:hover {
  transform: translateX(3px);
  background: #e3d9c9;
}

.mark {
  display: grid;
  width: 36px;
  height: 36px;
  margin-left: 8px;
  place-items: center;
  border-radius: 11px;
  background: #c43228;
  color: #fff6ea;
  font-weight: 700;
}

.copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.name {
  overflow: hidden;
  font-size: 18px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  font-variant-numeric: tabular-nums;
}

.danger {
  margin-right: 8px;
  background: transparent;
}

button:focus-visible,
a:focus-visible {
  outline: 2px solid #c43228;
  outline-offset: 2px;
}

button:active,
a:active {
  transform: scale(0.97);
}

@keyframes plugin-panel-in {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 640px) {
  li {
    flex-wrap: wrap;
    padding: 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sheet,
  .docs {
    animation: none;
  }

  li,
  button,
  a {
    transition: none;
  }

  li:hover {
    transform: none;
  }
}
</style>