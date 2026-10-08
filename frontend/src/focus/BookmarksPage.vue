<script setup>
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'

import { useQueuedSave } from '../blocks/queuedSave.js'
import { openExternalLink } from '../openExternal.js'

const props = defineProps({
  block: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save'])

const sections = ref([])
const editingKey = ref('')

function readContent() {
  return {
    sections: sections.value.map((section) => ({
      name: section.name.trim() || '收藏',
      items: section.items.map((item) => ({
        title: item.title.trim(),
        url: normalizeUrl(item.url),
        tags: textToTags(item.tagText),
      })),
    })),
  }
}

const { queue, flush } = useQueuedSave(emit, readContent)

function tagsToText(tags) {
  return (tags || []).map((tag) => `#${tag}`).join(' ')
}

function textToTags(text) {
  const seen = []
  String(text || '')
    .split(/[\s,，]+/)
    .map((part) => part.trim().replace(/^#+/, ''))
    .filter(Boolean)
    .forEach((tag) => {
      if (!seen.includes(tag)) {
        seen.push(tag.slice(0, 40))
      }
    })
  return seen.slice(0, 12)
}

function normalizeUrl(url) {
  const trimmed = String(url || '').trim()
  if (!trimmed) {
    return ''
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(trimmed)) {
    return trimmed
  }
  return `https://${trimmed}`
}

function makeKey() {
  return Math.random().toString(36).slice(2, 10)
}

function applyBlock(block) {
  const source = Array.isArray(block.content?.sections) ? block.content.sections : []
  const next = source.length ? source : [{ name: '收藏', items: [] }]
  sections.value = next.map((section) => ({
    key: makeKey(),
    name: section.name || '收藏',
    items: (section.items || []).map((item) => ({
      key: makeKey(),
      title: item.title || '',
      url: item.url || '',
      tags: item.tags || [],
      tagText: tagsToText(item.tags),
    })),
  }))
  editingKey.value = ''
}

watch(
  () => props.block.id,
  (_id, previous) => {
    if (previous != null) {
      flush()
    }
    applyBlock(props.block)
  },
  { immediate: true },
)

function touch() {
  queue(props.block.id)
}

function commit() {
  touch()
  flush()
}

function addSection() {
  sections.value.push({ key: makeKey(), name: '新分区', items: [] })
  commit()
}

function removeSection(index) {
  if (sections.value.length <= 1) {
    return
  }
  sections.value.splice(index, 1)
  commit()
}

function addItem(sectionIndex) {
  const item = { key: makeKey(), title: '', url: '', tags: [], tagText: '' }
  sections.value[sectionIndex].items.push(item)
  editingKey.value = item.key
  touch()
}

function removeItem(sectionIndex, itemIndex) {
  sections.value[sectionIndex].items.splice(itemIndex, 1)
  editingKey.value = ''
  commit()
}

function finishEdit() {
  sections.value.forEach((section) => {
    section.items.forEach((item) => {
      item.tags = textToTags(item.tagText)
    })
  })
  editingKey.value = ''
  commit()
}

function openItem(item) {
  const url = normalizeUrl(item.url)
  if (!url) {
    return
  }
  openExternalLink(url)
}
</script>

<template>
  <div class="mx-auto w-full max-w-3xl px-6 py-5">
    <div class="mb-3 flex items-center justify-between gap-3">
      <p class="text-xs text-ink/40">点标题打开网址 · 自动保存</p>
      <button type="button" class="h-8 rounded-md bg-ink px-3 text-xs font-semibold text-white hover:bg-moss" @click="addSection">
        + 分区
      </button>
    </div>

    <draggable v-model="sections" item-key="key" handle=".section-handle" :animation="160" @end="commit">
      <template #item="{ element: section, index: sectionIndex }">
        <section class="mb-4">
          <div class="mb-1 flex items-center gap-2">
            <button type="button" class="section-handle cursor-grab px-1 text-ink/35 active:cursor-grabbing" title="拖动分区">⋮⋮</button>
            <input
              v-model="section.name"
              class="h-8 min-w-0 flex-1 bg-transparent text-sm font-semibold text-ink outline-none"
              placeholder="分区名称"
              @change="commit"
            />
            <button type="button" class="text-xs text-moss hover:underline" @click="addItem(sectionIndex)">+ 链接</button>
            <button
              type="button"
              class="text-xs text-ink/40 hover:text-ember disabled:opacity-30"
              :disabled="sections.length <= 1"
              @click="removeSection(sectionIndex)"
            >
              删除分区
            </button>
          </div>

          <p v-if="section.items.length === 0" class="py-2 text-xs text-ink/40">这个分区还没有网址</p>

          <draggable
            v-model="section.items"
            item-key="key"
            handle=".item-handle"
            :animation="160"
            class="divide-y divide-black/[0.05] rounded-md border border-black/10 bg-white/70"
            @end="commit"
          >
            <template #item="{ element: item, index: itemIndex }">
              <div class="px-2.5 py-1.5">
                <div v-if="editingKey !== item.key" class="flex items-center gap-2">
                  <button type="button" class="item-handle cursor-grab text-ink/30 active:cursor-grabbing" title="拖动">⋮</button>
                  <button
                    type="button"
                    class="min-w-0 flex-1 truncate text-left text-sm font-medium text-aurora hover:underline disabled:text-ink/35 disabled:no-underline"
                    :disabled="!item.url.trim()"
                    @click="openItem(item)"
                  >
                    {{ item.title || '未命名' }}
                  </button>
                  <span class="hidden max-w-[34%] truncate text-xs text-ink/40 sm:inline">{{ item.url }}</span>
                  <span v-for="tag in item.tags" :key="tag" class="shrink-0 text-[11px] text-moss">#{{ tag }}</span>
                  <button type="button" class="shrink-0 text-xs text-ink/45 hover:text-ink" @click="editingKey = item.key">改</button>
                  <button type="button" class="shrink-0 text-xs text-ink/45 hover:text-ember" @click="removeItem(sectionIndex, itemIndex)">
                    删
                  </button>
                </div>
                <div v-else class="grid gap-1.5 sm:grid-cols-[auto_1fr_1.3fr_0.8fr_auto]">
                  <button type="button" class="item-handle cursor-grab text-ink/30" title="拖动">⋮</button>
                  <input v-model="item.title" class="h-8 rounded border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss" placeholder="标题" @change="touch" />
                  <input v-model="item.url" class="h-8 rounded border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss" placeholder="网址" @change="touch" />
                  <input
                    v-model="item.tagText"
                    class="h-8 rounded border border-black/10 bg-white px-2 text-sm outline-none focus:border-moss"
                    placeholder="#标签"
                    @change="item.tags = textToTags(item.tagText); touch()"
                  />
                  <button type="button" class="h-8 rounded bg-moss px-3 text-xs font-semibold text-white" @click="finishEdit">完成</button>
                </div>
              </div>
            </template>
          </draggable>
        </section>
      </template>
    </draggable>
  </div>
</template>
